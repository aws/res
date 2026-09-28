#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import botocore.exceptions
import jwt
import res.exceptions as exceptions
from res import constants
from res.clients.aws.aws_provider import AwsClientProvider
from res.clients.dcv_session_manager import dcv_session_manager_client
from res.resources import (
    ad_automation,
    cluster_settings,
    launch_templates,
    schedules,
    session_permissions,
)
from res.resources import sessions as user_sessions
from res.resources import software_stacks
from res.resources.sessions import ScriptEventType, ScriptOSType
from res.utils import (
    cluster_settings_utils,
    ec2_utils,
    gpu_utils,
    logging_utils,
    script_utils,
)
from res.utils import tags as res_tags
from res.utils.bootstrap_userdata_builder import BootstrapUserDataBuilder

SESSION_ID_KEY = "idea_session_id"

# DeleteFleets caps instant-fleet deletions per request; bulk terminations batch by this size.
_DELETE_FLEETS_BATCH_SIZE = 25

_FLEET_TYPE_INSTANT = "instant"
_FLEET_CAPACITY_TYPE_ON_DEMAND = "on-demand"
_FLEET_ALLOCATION_STRATEGY_LOWEST_PRICE = "lowest-price"
_FLEET_TAG_RESOURCE_TYPE = "fleet"
_FLEET_TARGET_CAPACITY_SINGLE_INSTANCE = 1

logger = logging_utils.get_logger("vdi-management")


# Stop VDI logic
def stop_sessions(sessions: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Stop sessions
    :param sessions: list of sessions to be stopped
    :returns successful and unsuccessful list of stopped sessions
    """
    validate_sessions_to_delete(sessions, True)

    servers_to_stop = []
    servers_to_hibernate = []
    success_response_list = []
    fail_response_list = []
    for session in sessions:
        if session.get("failure_reason"):
            logger.error(f'{session[SESSION_ID_KEY]}: {session["failure_reason"]}')
            fail_response_list.append(session)
            continue

        # Atomically move READY -> STOPPING. If a concurrent/overlapping stop
        # already transitioned this session out of READY, the conditional write
        # fails (returns None) and we skip issuing StopInstances — preventing a
        # redundant stop from overwriting a completed STOPPED back to STOPPING
        # (the stuck-STOPPING race).
        updated = user_sessions.transition_session_state_if(
            owner=session["owner"],
            session_id=session[SESSION_ID_KEY],
            new_state="STOPPING",
            expected_current_state="READY",
            session=session,
        )
        if updated is None:
            logger.info(
                f"{session[SESSION_ID_KEY]}: state changed concurrently; "
                f"not issuing a redundant stop."
            )
            success_response_list.append(session)
            continue

        if session.get("hibernation_enabled"):
            servers_to_hibernate.append(session.get("server"))
        else:
            servers_to_stop.append(session.get("server"))
        success_response_list.append(updated)

    logger.info(f"Stopping session(s)")
    stop_servers(servers_to_stop)
    hibernate_servers(servers_to_hibernate)
    return success_response_list, fail_response_list


def reboot_sessions(sessions: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Reboot EC2 instances for validated sessions and update state to RESUMING.
    Assumes sessions have already been validated (exists, correct state, connections checked).
    :param sessions: list of validated session dicts (from DDB)
    :returns (successful_list, unsuccessful_list)
    """
    instance_ids = [
        session.get("server", {}).get("instance_id") for session in sessions
    ]

    ec2_client = AwsClientProvider().ec2()
    ec2_client.reboot_instances(InstanceIds=instance_ids)

    success_response_list = []
    fail_response_list = []
    for session in sessions:
        try:
            updated = user_sessions.update_session_state(
                session["owner"], session[SESSION_ID_KEY], "RESUMING"
            )
            success_response_list.append(updated)
        except Exception as e:
            logger.error(
                f"Failed to update session state for {session[SESSION_ID_KEY]}: {e}"
            )
            session["failure_reason"] = f"State update failed: {e}"
            session["failure_code"] = exceptions.FAILURE_CODE_INTERNAL_SERVICE
            fail_response_list.append(session)

    return success_response_list, fail_response_list


def validate_sessions_to_delete(
    sessions: List[Dict[str, Any]],
    check_ready_state: bool = False,
) -> None:
    sessions_to_check = []
    for i, session in enumerate(sessions):
        try:
            existing_session = user_sessions.get_session(
                owner=session["owner"],
                session_id=session[SESSION_ID_KEY],
            )
            session = {
                **existing_session,
                "is_idle": session.get("is_idle", False),
                "force": session.get("force", False),
            }
            sessions[i] = session

        except exceptions.UserSessionNotFound:
            session["failure_reason"] = (
                f"Invalid RES Session ID: {session[SESSION_ID_KEY]}:{session['name']} for user: {session['owner']}.  Nothing to delete"
            )
            session["failure_code"] = exceptions.FAILURE_CODE_NOT_FOUND
            continue

        if check_ready_state and session.get("state", "") != "READY":
            session["failure_reason"] = (
                f"RES Session ID: {session[SESSION_ID_KEY]}:{session['name']} for user: {session['owner']} is in {session['state']} state. Can't stop. Wait for it to be READY."
            )
            session["failure_code"] = exceptions.FAILURE_CODE_BAD_REQUEST
            continue
        if session.get("state", "") in {"STOPPED", "STOPPED_IDLE"}:
            continue

        if not session.get(user_sessions.SESSION_DB_DCV_SESSION_ID_KEY):
            session["server"]["is_idle"] = (
                session.get("is_idle") if session.get("is_idle") else False
            )
            continue

        if not session.get("force"):
            sessions_to_check.append(session)

    sessions_with_count = get_active_counts_for_sessions(sessions_to_check)

    for session in sessions_with_count:
        if session.get("connection_count", 0) > 0:
            logger.info(
                f"Session {session.get('idea_session_id')}:{session.get('name')} has {session.get('connection_count')} active connection(s)"
            )
            session["failure_reason"] = (
                f"There exists {session.get('connection_count')} active connection(s)for session_id: {session.get('idea_session_id')}:{session.get('name')}. Please terminate."
            )
            session["failure_code"] = exceptions.FAILURE_CODE_CONFLICT


def get_active_counts_for_sessions(
    sessions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Populate ``connection_count`` on each session via the DCV Session Management Lambda.

    Sessions that fail to describe (e.g. host unreachable) keep ``connection_count = 0``.
    """
    if not sessions:
        return []

    response = dcv_session_manager_client.describe_sessions(
        [{"session_id": s[SESSION_ID_KEY], "owner": s["owner"]} for s in sessions]
    )
    counts = {
        entry["session_id"]: entry.get("num_of_connections", 0)
        for entry in response.get("successful_list", [])
    }
    for entry in response.get("unsuccessful_list", []):
        logger.warning(
            "Failed to describe session %s: %s. Treating as 0 connections.",
            entry.get("session_id"),
            entry.get("failure_reason"),
        )

    for session in sessions:
        session["connection_count"] = counts.get(session[SESSION_ID_KEY], 0)

    return sessions


def stop_servers(servers: List[Dict] = None) -> None:
    if not servers:
        logger.info("No servers provided to stop")
        return
    _stop_or_hibernate_servers(servers)


def hibernate_servers(servers: List[Dict] = None) -> None:
    if not servers:
        logger.info("No servers provided to hibernate...")
        return
    _stop_or_hibernate_servers(servers, True)


def _stop_or_hibernate_servers(servers, hibernate=False) -> None:
    _stop_hosts(servers=servers, hibernate=hibernate)


def _stop_hosts(servers: List[Dict], hibernate=False) -> dict:
    if not servers:
        logger.info("No servers provided to _stop_hosts...")
        return {}

    instance_ids = [server["instance_id"] for server in servers]

    if hibernate:
        logger.info(f"Hibernating {instance_ids}")
    else:
        logger.info(f"Stopping {instance_ids}")

    ec2_client = AwsClientProvider().ec2()
    response = ec2_client.stop_instances(InstanceIds=instance_ids, Hibernate=hibernate)
    return response


# Terminate VDI logic
def terminate_sessions(sessions: List[Dict[str, Any]]):
    """
    Terminates sessions
    :param sessions: list of sessions to be terminated
    :returns successful and unsuccessful list of terminated sessions
    """
    validate_sessions_to_delete(sessions)

    servers_to_delete = []
    success_response_list = []
    fail_response_list = []
    for session in sessions:
        if session.get("failure_reason"):
            logger.error(f'{session[SESSION_ID_KEY]}: {session["failure_reason"]}')
            fail_response_list.append(session)
            continue

        session["state"] = "DELETING"
        session = user_sessions.update_session(session)

        delete_schedule_for_session(session=session)
        session_permissions.delete_session_permission_by_id(
            session_id=session[SESSION_ID_KEY]
        )
        user_sessions.delete_session(session=session)
        session["state"] = "DELETED"
        servers_to_delete.append(session.get("server"))

        success_response_list.append(session)

    terminate_servers(servers_to_delete)

    ad_automation.remove_ad_authorization(
        [server["instance_id"] for server in servers_to_delete]
    )

    return success_response_list, fail_response_list


def terminate_servers(servers: List[Dict[str, Any]]) -> None:
    if not servers:
        logger.info("No servers provided to terminate")
        return

    _terminate_hosts(servers)


def _terminate_hosts(servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ec2_client = AwsClientProvider().ec2()

    fleet_ids = [server["fleet_id"] for server in servers if server.get("fleet_id")]
    # Sessions migrated from a pre-CreateFleet environment have no fleet_id.
    instance_ids_without_fleet = [
        server["instance_id"]
        for server in servers
        if not server.get("fleet_id") and server.get("instance_id")
    ]

    responses: List[Dict[str, Any]] = []

    for batch_start in range(0, len(fleet_ids), _DELETE_FLEETS_BATCH_SIZE):
        batch = fleet_ids[batch_start : batch_start + _DELETE_FLEETS_BATCH_SIZE]
        logger.info(f"Deleting fleets {batch}")
        batch_response = ec2_client.delete_fleets(
            FleetIds=batch, TerminateInstances=True
        )
        unsuccessful = batch_response.get("UnsuccessfulFleetDeletions") or []
        if unsuccessful:
            logger.warning(f"Failed to delete fleets: {unsuccessful}")
        responses.append(batch_response)

    if instance_ids_without_fleet:
        logger.info(f"Terminating instances {instance_ids_without_fleet}")
        responses.append(
            ec2_client.terminate_instances(InstanceIds=instance_ids_without_fleet)
        )

    return responses


def delete_schedule_for_session(session: Dict[str, Any]) -> None:
    session_id = session.get(user_sessions.SESSION_DB_RANGE_KEY)
    owner = session.get(user_sessions.SESSION_DB_HASH_KEY)
    curr_session = user_sessions.get_session(owner=owner, session_id=session_id)

    for day in schedules.DayOfWeek:
        key = f"{day.value}{user_sessions.SESSION_DB_SCHEDULE_SUFFIX}"
        schedule = curr_session.get(key)
        if schedule and schedule.get("schedule_id"):
            schedules.delete_schedule(schedule=schedule)


# Start VDI logic
def start_sessions(sessions: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Start sessions by calling EC2 start_instances and updating session state.
    Only updates state for instances that actually transitioned from stopped.
    :param sessions: list of validated sessions to be started (DDB dicts)
    :returns (successful list, unsuccessful list)
    """
    servers_to_start = [session.get("server") for session in sessions]
    response = _start_hosts(servers_to_start)

    started_ids = set()
    for instance in response.get("StartingInstances", []):
        if instance.get("CurrentState", {}).get("Name") in ("pending", "running"):
            started_ids.add(instance["InstanceId"])

    success_response_list = []
    fail_response_list = []
    for session in sessions:
        instance_id = session.get("server", {}).get("instance_id")
        if instance_id in started_ids:
            updated = user_sessions.update_session_state(
                owner=session["owner"],
                session_id=session[SESSION_ID_KEY],
                state="RESUMING",
            )
            success_response_list.append(updated)
        else:
            session["failure_reason"] = f"EC2 instance {instance_id} failed to start"
            session["failure_code"] = exceptions.FAILURE_CODE_INTERNAL_SERVICE
            fail_response_list.append(session)

    return success_response_list, fail_response_list


def _start_hosts(servers: List[Dict]) -> dict:
    if not servers:
        logger.info("No servers provided to start")
        return {}

    instance_ids = [server["instance_id"] for server in servers]
    logger.info(f"Starting {instance_ids}")

    ec2_client = AwsClientProvider().ec2()
    response = ec2_client.start_instances(InstanceIds=instance_ids)
    return response


# --- Session Creation ---


def validate_attempt_subnets(virtual_desktop: Dict[str, Any]):
    """
    Determine which subnets to attempt for EC2 placement.
    Validates user-provided subnet_id against configured allowed subnets.
    Returns (virtual_desktop, is_valid).
    """
    configured_vdi_subnets = cluster_settings.get_setting(
        "vdc.dcv_session.network.private_subnets"
    )
    cluster_private_subnets = cluster_settings.get_setting(
        "cluster.network.private_subnets"
    )

    server = virtual_desktop.get("server") or {}
    subnet_id = server.get("subnet_id")

    if subnet_id:
        # Validate user-provided subnet_id against allowed subnets
        allowed_subnets = set(configured_vdi_subnets or []) | set(
            cluster_private_subnets or []
        )
        if subnet_id not in allowed_subnets:
            allowed_list = ", ".join(sorted(allowed_subnets))
            virtual_desktop["failure_reason"] = (
                f"The provided subnet ({subnet_id}) is not authorized for this environment. "
                f"Valid subnets: {allowed_list}"
            )
            return virtual_desktop, False
        attempt_subnets = [subnet_id]
    elif configured_vdi_subnets:
        attempt_subnets = configured_vdi_subnets
    else:
        attempt_subnets = cluster_private_subnets

    if not attempt_subnets:
        virtual_desktop["failure_reason"] = "No subnets available for deployment"
        return virtual_desktop, False

    virtual_desktop["attempt_subnets"] = attempt_subnets
    return virtual_desktop, True


def create_virtual_desktop(virtual_desktop: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a Virtual Desktop: attach default schedule, provision EC2 host, write to DDB.
    Returns virtual desktop dict with state=PROVISIONING, or with failure_reason set on error.
    """
    virtual_desktop, is_valid = validate_attempt_subnets(virtual_desktop)
    if not is_valid:
        return virtual_desktop

    try:
        if not virtual_desktop.get("schedule"):
            virtual_desktop["schedule"] = schedules.get_default_schedules() or {}

        for day, day_schedule in virtual_desktop.get("schedule", {}).items():
            virtual_desktop["schedule"][day] = {
                **day_schedule,
                "idea_session_id": virtual_desktop.get("idea_session_id"),
                "idea_session_owner": virtual_desktop.get("owner"),
            }

        host_provisioning_response = _build_user_data_and_provision(virtual_desktop)
        instances = host_provisioning_response.get("Instances", [])
        server = virtual_desktop.get("server") or {}
        server["instance_id"] = instances[0].get("InstanceId", None)
        server["instance_type"] = instances[0].get("InstanceType", None)
        server["subnet_id"] = instances[0].get("SubnetId", None)
        server["fleet_id"] = host_provisioning_response.get("FleetId")
        server["ami_id"] = host_provisioning_response.get("ami_id")
        virtual_desktop["server"] = server

    except exceptions.InvalidParams as e:
        logger.error(f"Client error provisioning virtual desktop: {e}")
        virtual_desktop["failure_reason"] = str(e)
        virtual_desktop["failure_code"] = exceptions.FAILURE_CODE_BAD_REQUEST
        return virtual_desktop
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        logger.error(f"AWS error provisioning virtual desktop: {error_code} - {e}")
        virtual_desktop["failure_reason"] = (
            f"AWS provisioning error: {error_code} - {e}"
        )
        if error_code in exceptions.EC2_NON_RETRYABLE_CLIENT_ERROR_CODES:
            virtual_desktop["failure_code"] = exceptions.FAILURE_CODE_BAD_REQUEST
        else:
            virtual_desktop["failure_code"] = exceptions.FAILURE_CODE_INTERNAL_SERVICE
        return virtual_desktop
    except Exception as e:
        logger.error(f"Unexpected error provisioning virtual desktop: {e}")
        virtual_desktop["failure_reason"] = f"Internal error: {e}"
        virtual_desktop["failure_code"] = exceptions.FAILURE_CODE_INTERNAL_SERVICE
        return virtual_desktop

    for day, day_schedule in virtual_desktop.pop("schedule", {}).items():
        if (
            day_schedule.get("schedule_type")
            and day_schedule.get("schedule_type")
            != schedules.VirtualDesktopScheduleType.NO_SCHEDULE.value
        ):
            try:
                day_schedule = schedules.create_schedule_for_day_of_week(
                    day_of_week=schedules.DayOfWeek(day),
                    schedule=day_schedule,
                    idea_session_id=virtual_desktop.get("idea_session_id"),
                    idea_session_owner=virtual_desktop.get("owner"),
                )
            except Exception as e:
                logger.error(f"Failed to create schedule record for {day}: {e}")
        virtual_desktop[f"{day}_schedule"] = day_schedule

    virtual_desktop["state"] = "PROVISIONING"
    return user_sessions.create_session(virtual_desktop)


def _build_user_data_and_provision(virtual_desktop: Dict[str, Any]) -> dict:
    """Build tags, resolve subnets, and provision EC2 instance."""
    cluster_name = cluster_settings.get_setting("cluster.cluster_name")
    project = virtual_desktop.get("project") or {}

    tags = {
        "Name": f'{cluster_name}-{virtual_desktop.get("name")}-{virtual_desktop.get("owner")}',
        constants.RES_TAG_NODE_TYPE: constants.NODE_TYPE_DCV_HOST,
        constants.RES_TAG_ENVIRONMENT_NAME: cluster_name,
        constants.RES_TAG_MODULE_ID: constants.MODULE_ID_VDC,
        constants.RES_TAG_MODULE_NAME: constants.MODULE_NAME_VDC,
        constants.RES_TAG_MODULE_VERSION: os.environ.get("version", ""),
        constants.RES_TAG_BACKUP_PLAN: f"{cluster_name}-{constants.MODULE_ID_VDC}",
        constants.RES_TAG_PROJECT: project.get("name", ""),
        constants.RES_TAG_DCV_SESSION_ID: "TBD",
    }

    project_tags = project.get("tags")
    if project_tags:
        for key, value in project_tags.items():
            tags[key] = value

    custom_tags = cluster_settings.get_setting("global-settings.custom_tags")
    custom_tags_dict = res_tags.convert_custom_tags_to_key_value_pairs(custom_tags)
    vd_tags = res_tags.convert_tags_list_of_dict_to_tags_dict(
        virtual_desktop.get("tags") or []
    )
    tags = {**custom_tags_dict, **tags, **vd_tags}

    aws_tags = [{"Key": key, "Value": value} for key, value in tags.items()]
    metadata_http_tokens = cluster_settings.get_setting(
        "vdc.dcv_session.metadata_http_tokens"
    )
    kms_key_id = (
        cluster_settings.get_setting("cluster.ebs.kms_key_id") or "alias/aws/ebs"
    )

    attempt_subnets = list(virtual_desktop.get("attempt_subnets") or [])
    subnet_autoretry = cluster_settings.get_setting(
        "vdc.dcv_session.network.subnet_autoretry"
    )
    randomize_subnets = cluster_settings.get_setting(
        "vdc.dcv_session.network.randomize_subnets"
    )

    if randomize_subnets:
        random.shuffle(attempt_subnets)

    stack_id = virtual_desktop.get("software_stack_id", "")
    base_os = virtual_desktop.get("base_os", "")
    software_stack = (
        software_stacks.get_software_stack(base_os=base_os, stack_id=stack_id)
        if stack_id and base_os
        else {}
    )
    tenancy = software_stack.get("tenancy") or "default"
    placement = {"Tenancy": tenancy}
    if tenancy == "host":
        affinity = software_stack.get("affinity")
        if affinity:
            placement["Affinity"] = affinity
        host_id = software_stack.get("host_id")
        if host_id:
            placement["HostId"] = host_id
        else:
            host_resource_group_arn = software_stack.get("host_resource_group_arn")
            if host_resource_group_arn:
                placement["HostResourceGroupArn"] = host_resource_group_arn

    host_provisioning_response = _provision_ec2_instance(
        virtual_desktop,
        attempt_subnets,
        aws_tags,
        metadata_http_tokens,
        kms_key_id,
        placement,
        software_stack,
    )
    host_provisioning_response["ami_id"] = software_stack.get("ami_id")
    return host_provisioning_response


def _provision_ec2_instance(
    virtual_desktop: Dict[str, Any],
    attempt_subnets: List[str],
    aws_tags: list,
    metadata_http_tokens: str,
    kms_key_id: str,
    placement: dict,
    software_stack: Dict[str, Any],
) -> dict:
    """Launch a VDI host via CreateFleet in `instant` mode.

    Returns {"Instances": [{"InstanceId", "InstanceType", "SubnetId"}], "FleetId"}.
    """
    idea_session_id = virtual_desktop.get("idea_session_id", "")
    cluster_name = cluster_settings.get_setting("cluster.cluster_name")
    smart_retry_enabled = cluster_settings.get_setting(
        "vdc.dcv_session.smart_retry.enabled"
    )

    overrides = _build_fleet_overrides(
        virtual_desktop, software_stack, attempt_subnets, smart_retry_enabled
    )
    user_data = _build_userdata(virtual_desktop, software_stack)
    fleet_tags = [
        {"Key": constants.RES_TAG_ENVIRONMENT_NAME, "Value": cluster_name},
        {"Key": constants.RES_TAG_MODULE_ID, "Value": constants.MODULE_ID_VDC},
        {"Key": "idea_session_id", "Value": idea_session_id},
    ]

    launch_template_id: Optional[str] = None
    try:
        launch_template_id, launch_template_version = (
            launch_templates.create_for_session(
                virtual_desktop=virtual_desktop,
                software_stack=software_stack,
                aws_tags=aws_tags,
                metadata_http_tokens=metadata_http_tokens,
                kms_key_id=kms_key_id,
                placement=placement,
                user_data=user_data,
            )
        )
        return _create_fleet(
            idea_session_id=idea_session_id,
            launch_template_id=launch_template_id,
            launch_template_version=launch_template_version,
            overrides=overrides,
            fleet_tags=fleet_tags,
        )
    finally:
        launch_templates.delete_for_session(launch_template_id)


def _create_fleet(
    idea_session_id: str,
    launch_template_id: str,
    launch_template_version: int,
    overrides: List[Dict[str, Any]],
    fleet_tags: List[Dict[str, str]],
) -> dict:
    """Launch an EC2 instance via CreateFleet.

    :returns: {"Instances": [{"InstanceId", "InstanceType", "SubnetId"}], "FleetId"}
    :raises InvalidParams: when the fleet launched no instances.
    """
    ec2_client = AwsClientProvider().ec2()
    logger.info(f"session {idea_session_id} CreateFleet")

    response = ec2_client.create_fleet(
        Type=_FLEET_TYPE_INSTANT,
        LaunchTemplateConfigs=[
            {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": launch_template_id,
                    "Version": str(launch_template_version),
                },
                "Overrides": overrides,
            }
        ],
        TargetCapacitySpecification={
            "TotalTargetCapacity": _FLEET_TARGET_CAPACITY_SINGLE_INSTANCE,
            "OnDemandTargetCapacity": _FLEET_TARGET_CAPACITY_SINGLE_INSTANCE,
            "DefaultTargetCapacityType": _FLEET_CAPACITY_TYPE_ON_DEMAND,
        },
        OnDemandOptions={"AllocationStrategy": _FLEET_ALLOCATION_STRATEGY_LOWEST_PRICE},
        TagSpecifications=[
            {"ResourceType": _FLEET_TAG_RESOURCE_TYPE, "Tags": fleet_tags}
        ],
    )

    picked = (response.get("Instances") or [{}])[0]
    picked_instance_ids = picked.get("InstanceIds") or []
    if not picked_instance_ids:
        error_messages = [
            entry.get("ErrorMessage", "") for entry in (response.get("Errors") or [])
        ]
        raise exceptions.InvalidParams(
            f"CreateFleet launched no instances. Errors: {error_messages}"
        )

    picked_instance_id = picked_instance_ids[0]
    picked_instance_type = picked.get("InstanceType")
    picked_subnet_id = (
        picked.get("LaunchTemplateAndOverrides", {})
        .get("Overrides", {})
        .get("SubnetId")
    )
    logger.info(
        f"session {idea_session_id} CreateFleet picked "
        f"instance_type={picked_instance_type} "
        f"subnet_id={picked_subnet_id} "
        f"instance_id={picked_instance_id}. "
        f"Skipped candidate errors: {response.get('Errors')}"
    )
    return {
        "Instances": [
            {
                "InstanceId": picked_instance_id,
                "InstanceType": picked_instance_type,
                "SubnetId": picked_subnet_id,
            }
        ],
        "FleetId": response.get("FleetId"),
    }


def _build_fleet_overrides(
    virtual_desktop: Dict[str, Any],
    software_stack: Dict[str, Any],
    attempt_subnets: List[str],
    smart_retry_enabled: bool,
) -> List[Dict[str, Any]]:
    """Build the CreateFleet Overrides list, log the candidates, and raise if empty.

    When smart retry is enabled, cross-product allowed_instance_types with
    attempt_subnets, filtering out instance types that don't meet the
    software stack's min RAM requirement;
    When smart retry is disabled, produce one override per attempt subnet
    for the User-supplied instance_type.
    """
    server = virtual_desktop.get("server") or {}
    if smart_retry_enabled:
        valid_instance_types = ec2_utils.get_valid_instance_types_by_allowed_list(
            hibernation_support=bool(virtual_desktop.get("hibernation_enabled")),
            allowed_instance_types=software_stack.get("allowed_instance_types") or [],
        )
        instance_types = sorted(
            name
            for name in valid_instance_types
            if software_stacks.validate_min_ram(name, software_stack)
        )
    else:
        instance_types = [server.get("instance_type")]

    overrides = [
        {"InstanceType": instance_type, "SubnetId": subnet_id}
        for instance_type in instance_types
        if instance_type
        for subnet_id in attempt_subnets
    ]

    idea_session_id = virtual_desktop.get("idea_session_id", "")
    if not overrides:
        raise exceptions.InvalidParams(
            f"No valid instance types available for this software stack "
            f"(hibernation_enabled={bool(virtual_desktop.get('hibernation_enabled'))}). "
            f"Check the software stack's allowed_instance_types and the deny list."
        )

    candidate_pairs = [(o["InstanceType"], o["SubnetId"]) for o in overrides]
    logger.info(
        f"session {idea_session_id} CreateFleet candidates "
        f"(smart_retry_enabled={smart_retry_enabled}): {candidate_pairs}"
    )
    return overrides


def _build_userdata(
    virtual_desktop: Dict[str, Any], software_stack: Dict[str, Any]
) -> str:
    """Build EC2 userdata script for the DCV host."""
    project = virtual_desktop.get("project") or {}
    server = virtual_desktop.get("server") or {}
    base_os = virtual_desktop.get("base_os", "")
    owner = virtual_desktop.get("owner", "")
    idea_session_id = virtual_desktop.get("idea_session_id", "")
    project_id = project.get("project_id", "")
    project_name = project.get("name", "")

    # install.sh expects "NONE" for the no-GPU case.
    gpu_family = software_stack.get("gpu") or "NO_GPU"
    if gpu_family == "NO_GPU":
        gpu_family = "NONE"

    rerun_on_reboot = script_utils._retrieve_rerun_on_reboot(
        project, ScriptOSType.LINUX
    )
    on_vdi_start_script_commands = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.LINUX, ScriptEventType.ON_VDI_START
    )
    on_vdi_configured_script_commands = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.LINUX, ScriptEventType.ON_VDI_CONFIGURED
    )
    on_vdi_start_script_store = script_utils._store_commands_as_linux_script(
        on_vdi_start_script_commands, ScriptEventType.ON_VDI_START.value
    )
    on_vdi_configured_script_store = script_utils._store_commands_as_linux_script(
        on_vdi_configured_script_commands, ScriptEventType.ON_VDI_CONFIGURED.value
    )

    lock_file = "/root/bootstrap/semaphore/custom_script.lock"
    instance_ready_lock_file = "/root/bootstrap/semaphore/instance_ready.lock"
    custom_script_check = [f"if [[ ! -f {lock_file} ]]; then"]
    if rerun_on_reboot:
        custom_script_check = [
            f"if [[ ! -f {lock_file} || -f {instance_ready_lock_file} ]]; then"
        ]

    cluster_name = cluster_settings.get_setting("cluster.cluster_name")

    custom_script_commands = custom_script_check + [
        *on_vdi_start_script_store,
        *on_vdi_configured_script_store,
        f"/bin/bash scripts/virtual-desktop-host/linux/export_launch_script_env.sh -p {project_id} -o {owner} -n {project_name} -e {cluster_name} -c {ScriptEventType.ON_VDI_CONFIGURED.value}.sh -s {ScriptEventType.ON_VDI_START.value}.sh -r {rerun_on_reboot}",
        "source /etc/launch_script_environment",
        f"/bin/bash scripts/virtual-desktop-host/linux/{ScriptEventType.ON_VDI_START.value}.sh",
        f"echo $(date +%s) > {lock_file}",
        "fi",
    ]

    custom_broker_api_url = cluster_settings.get_setting(
        "vdc.custom_credential_broker_api_gateway_url"
    )
    region = cluster_settings.get_setting("cluster.aws.region")

    try:
        secret_value = cluster_settings.get_secret(
            "vdc.custom_credential_broker_secret_name"
        )
        current_time = int(time.time())
        payload = {
            "region": region,
            "project_name": project_name,
            "session_owner": owner,
            "session_id": idea_session_id,
            "iat": current_time,
            "exp": current_time + 31536000,
            "role_arn": cluster_settings.get_setting("vdc.dcv_host_role_arn"),
            "role_session_name": f"{owner}-{idea_session_id}",
        }
        jwt_token = jwt.encode(payload, secret_value, algorithm="HS256")
    except Exception as e:
        logger.error(f"Failed to retrieve credential broker secret: {e}")
        raise

    session_type = virtual_desktop.get("session_type", "")
    enable_lustre = "true" if _has_fsx_lustre_file_systems() else "false"

    install_commands = custom_script_commands + [
        f'/bin/bash scripts/virtual-desktop-host/linux/install.sh -m {constants.MODULE_ID_VIRTUAL_DESKTOP_APP} -g {gpu_family} -u {custom_broker_api_url} -t {jwt_token} -p false -e {cluster_name} -n {project_name} -o {owner} -d {session_type} -i {idea_session_id} -a {region} -h {virtual_desktop.get("hibernation_enabled") or False} -l {enable_lustre}'
    ]

    if base_os == "windows":
        install_commands = _build_windows_install_commands(
            virtual_desktop, project, jwt_token, custom_broker_api_url
        )

    https_proxy = cluster_settings.get_setting("cluster.network.https_proxy")
    no_proxy = cluster_settings.get_setting("cluster.network.no_proxy")
    proxy_config = {}
    if https_proxy:
        proxy_config = {
            "http_proxy": https_proxy,
            "https_proxy": https_proxy,
            "no_proxy": no_proxy,
        }

    user_data_builder = BootstrapUserDataBuilder(
        base_os=base_os,
        aws_region=cluster_settings.get_setting("cluster.aws.region"),
        bootstrap_package_uri=cluster_settings.get_setting(
            "cluster.installation_scripts_uri"
        ),
        install_commands=install_commands,
        proxy_config=proxy_config,
    )
    return user_data_builder.build()


def _build_windows_install_commands(
    virtual_desktop: Dict[str, Any], project: dict, jwt_token: str, broker_api_url: str
) -> List[str]:
    """Build Windows-specific install commands for VDI bootstrap."""
    cluster_name = cluster_settings.get_setting("cluster.cluster_name")
    project_id = project.get("project_id", "")
    project_name = project.get("name", "")
    owner = virtual_desktop.get("owner", "")
    idea_session_id = virtual_desktop.get("idea_session_id", "")

    on_vdi_start_script_commands = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_START
    )
    on_vdi_configured_script_commands = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_CONFIGURED
    )
    on_vdi_start_script_store = script_utils._store_commands_as_windows_script(
        on_vdi_start_script_commands, ScriptEventType.ON_VDI_START.value
    )
    on_vdi_configured_script_store = script_utils._store_commands_as_windows_script(
        on_vdi_configured_script_commands, ScriptEventType.ON_VDI_CONFIGURED.value
    )

    change_directory_command = ['cd "scripts\\virtual-desktop-host\\windows"']
    export_env_variables_commands = [
        "Import-Module .\\ExportLaunchScriptEnv.ps1",
        f'Export-EnvironmentVariables -ProjectId "{project_id}" -OwnerId "{owner}" -EnvName "{cluster_name}" -ProjectName "{project_name}" -OnVDIStartCommands "{ScriptEventType.ON_VDI_START.value}.ps1" -OnVDIConfigureCommands "{ScriptEventType.ON_VDI_CONFIGURED.value}.ps1"',
    ]
    on_vdi_start_run = ["& .\\$env:ON_VDI_START_COMMANDS"]

    return (
        change_directory_command
        + export_env_variables_commands
        + on_vdi_start_script_store
        + on_vdi_configured_script_store
        + on_vdi_start_run
        + [
            "Import-Module .\\Install.ps1",
            f'Install-WindowsEC2Instance -ConfigureForRESVDI -AWSRegion "{cluster_settings.get_setting("cluster.aws.region")}" -ENVName "{cluster_name}" -ModuleID "{constants.MODULE_ID_VIRTUAL_DESKTOP_APP}" -ProjectName {project_name} -SessionOwner "{owner}" -SessionId "{idea_session_id}" -BootstrapToken "{jwt_token}" -CustomBrokerApi "{broker_api_url}" -OnVDIConfiguredCommands "{ScriptEventType.ON_VDI_CONFIGURED.value}.ps1"',
        ]
    )


def _has_fsx_lustre_file_systems() -> bool:
    """Check if any FSx Lustre file systems are onboarded."""
    entries = cluster_settings_utils.get_config_entries(
        query=r"shared-storage\..+\.fsx_lustre\..+"
    )
    return len(entries) > 0
