#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import jwt
import os
import random
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import botocore.exceptions
from res import exceptions as res_exceptions  # type: ignore
from api import exceptions as api_exceptions
from res.utils.ec2_utils import dedicated_hosts_supported, get_gpu_manufacturer, get_instance_ram, get_systems_manager_parameter, get_valid_instance_types_by_allowed_list
from datamodel.models.backend.batch_stop_session_failure import BatchStopSessionFailure
from datamodel.models.backend.batch_delete_session_failure import BatchDeleteSessionFailure
from datamodel.models.backend.batch_start_session_failure import BatchStartSessionFailure
from datamodel.models.backend.batch_reboot_session_failure import BatchRebootSessionFailure
from datamodel.models.backend.batch_operation_error_code import BatchOperationErrorCode
from datamodel.models.project import Project
from datamodel.models.res_memory import ResMemory
from datamodel.models.virtual_desktop_base_os import VirtualDesktopBaseOs
from datamodel.models.virtual_desktop_gpu import VirtualDesktopGpu
from datamodel.models.virtual_desktop_server import VirtualDesktopServer
from datamodel.models.virtual_desktop_session import VirtualDesktopSession
from datamodel.models.virtual_desktop_session_type import VirtualDesktopSessionType
from datamodel.models.virtual_desktop_session_state import VirtualDesktopSessionState
from datamodel.models.virtual_desktop_software_stack import VirtualDesktopSoftwareStack
from datamodel.models.virtual_desktop_tenancy import VirtualDesktopTenancy
from datamodel.serializers.virtual_desktop_session_serializer import virtualdesktopsession_serializer
from datamodel.models.virtual_desktop_week_schedule import VirtualDesktopWeekSchedule
from res import constants
from res.clients.aws.aws_provider import AwsClientProvider
from res.clients.aws.base import AWSClientProviderOptions
from res.resources.vdi_management import get_active_counts_for_sessions
from res.exceptions import SoftwareStackNotFound
from res.resources.sessions import ScriptOSType, ScriptEventType
from res.resources import (
    accounts,
    cluster_settings,
    projects as res_projects,
    role_assignments,
    schedules as res_schedules,
    sessions as res_sessions,
    software_stacks,
)
from res.utils import logging_utils, ec2_utils, script_utils, iam_utils, cluster_settings_utils
from res.resources import budget_utils
from res.utils import tags as res_tags
from res.utils import gpu_utils
from res.utils.bootstrap_userdata_builder import BootstrapUserDataBuilder
from res.constants import SESSION_NAME_REGEX, SESSION_NAME_ERROR_MESSAGE
from res.utils import string_utils

_region = os.environ.get('aws_region', 'us-east-1')
_aws_client_provider = AwsClientProvider(AWSClientProviderOptions(region=_region))
ec2_client = _aws_client_provider.ec2()
_module_version = os.environ.get("version", "")

logger = logging_utils.get_logger(__name__)

def validate_update_session_request(
    session: VirtualDesktopSession, old_session_dict: Dict[str, Any]
) -> None:

    old_state = old_session_dict.get(res_sessions.SESSION_DB_STATE_KEY)
    if (
        session.server.instance_type
        != old_session_dict[res_sessions.SESSION_DB_SERVER_KEY]["instance_type"]
        and old_state != VirtualDesktopSessionState.STOPPED
    ):
        raise api_exceptions.BadRequestException(
            "Session must be stopped before changing instance type."
        )

    hibernation_enabled = old_session_dict[res_sessions.SESSION_DB_HIBERNATION_KEY]
    if (
        hibernation_enabled
        and session.server.instance_type
        != old_session_dict[res_sessions.SESSION_DB_SERVER_KEY]["instance_type"]
    ):
        raise api_exceptions.BadRequestException(
            f"Not allowed to change Instance type for session: {old_session_dict[res_sessions.SESSION_DB_RANGE_KEY]} because hibernation is enabled"
        )

    base_os = old_session_dict[res_sessions.SESSION_DB_STACK_KEY][
        res_sessions.SESSION_DB_BASE_OS_KEY
    ]
    software_stack_id = old_session_dict[res_sessions.SESSION_DB_STACK_KEY][
        software_stacks.SOFTWARE_STACK_DB_RANGE_KEY
    ]
    try:
        software_stack_dict = software_stacks.get_software_stack(
            base_os, software_stack_id
        )
    except res_exceptions.SoftwareStackNotFound:
        raise api_exceptions.BadRequestException(
            f"Software stack {software_stack_id} with base_os {base_os} does not exist"
        )

    valid_instance_types_dict = ec2_utils.get_valid_instance_types_by_allowed_list(
        hibernation_support=hibernation_enabled,
        allowed_instance_types=software_stack_dict[
            software_stacks.SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY
        ],
    )
    if session.server.instance_type not in valid_instance_types_dict.keys():
        raise api_exceptions.BadRequestException(
            f"Invalid session instance type {session.server.instance_type}.  Not allowed for current configuration."
        )

def _validate_create_session_request(session: VirtualDesktopSession, user: str) -> Tuple[VirtualDesktopSession, bool]:
    if not session.owner: 
        session.owner = user   
    if accounts.is_active_admin(user):
        return validate_create_session_request(session)            
    
    # Session name sanitization
    if session.name and not string_utils.validate_input(session.name, SESSION_NAME_REGEX):
        session.failure_reason = SESSION_NAME_ERROR_MESSAGE
        return session, False

    message, is_valid = _validate_owner_for_create(session, user)
    if not is_valid:
        session.failure_reason = (session.failure_reason or "") + str(message)
        logger.error(session.failure_reason)
        return session, False

    session, is_valid = _validate_user_identity_for_create(session, user)
    if not is_valid:
        return session, False

    session_count_for_user = res_sessions.get_current_project_session_count_for_user(session.owner, session.project.project_id)
    allowed_sessions_per_user = res_projects.get_allowed_sessions_per_user(session.project.project_id)

    if session_count_for_user >= allowed_sessions_per_user:
        session.failure_reason = f'User {session.owner} has exceeded the allowed number of sessions: {session_count_for_user}. Please contact the Project Administrators if you need to create more sessions.'
        return session, False

    return validate_create_session_request(session)


def _validate_user_identity_for_create(session: VirtualDesktopSession, user: str) -> Tuple[VirtualDesktopSession, bool]:
    """Validate user identity constraints (Cognito UID, OS restrictions)."""
    user_info = accounts.get_user(user)

    if not user_info.get("uid") and user_info.get("identity_source") == constants.COGNITO_USER_IDP_TYPE:
        session.failure_reason = 'The system was unable to create an ID for you. Please try logging out of the account and logging back in for an ID to be created'
        logger.error(session.failure_reason)
        return session, False

    SUPPORTED_LINUX_OS = [os for os in VirtualDesktopBaseOs if os != VirtualDesktopBaseOs.WINDOWS]
    if user_info.get("identity_source") != constants.SSO_USER_IDP_TYPE and session.base_os not in SUPPORTED_LINUX_OS:
        session.failure_reason = 'Cognito users are not allowed to create non-Linux sessions.'
        logger.error(session.failure_reason)
        return session, False

    return session, True


def _validate_owner_for_create(session: VirtualDesktopSession, user: str) -> Tuple[str, bool]:
    
    logger.info(f'Session creation requested by {user} in project ID: {session.project.project_id} to be owned by {session.owner}')

    resource_key = f'{session.project.project_id}:project'
    user_permissions = role_assignments.get_user_permissions(user, resource_key)
    
    logger.info(f'User {user} permissions for project {session.project.project_id}: {user_permissions}')
    
    if session.owner == user:
        if "vdis.create_sessions" not in user_permissions:
            return "You're not authorized to create sessions for yourself in this project.", False
    else:
        if "vdis.create_terminate_others_sessions" not in user_permissions:
            return "You're not authorized to create sessions for others in this project.", False

    return "", True


def validate_create_session_request(session: VirtualDesktopSession) -> Tuple[VirtualDesktopSession, bool]:
    
    # These validations are needed as these fields are marked as optional in the VirtualDesktopSession smithy model  
    if session.hibernation_enabled is None:
        session.failure_reason = "missing session.hibernation_enabled"
        return session, False

    if not session.software_stack_id or not session.base_os:
        session.failure_reason = f'missing session.software_stack_id and/or session.base_os'
        return session, False
    
    if not session.project or not session.project.project_id:
         session.failure_reason = 'missing - session.project.project_id'
         return session, False
    
    if not session.server or not session.server.root_volume_size:
        session.failure_reason = 'missing session.server.root_volume_size'
        return session, False
    
    if not session.server or not session.server.instance_type:
        session.failure_reason = 'missing session.server.instance_type'
        return session, False

    if session.server.instance_profile_arn:
        session.failure_reason = f'Invalid session.server.instance_profile_arn {session.server.instance_profile_arn}. External instance_profile_arn not allowed.'
        return session, False

    is_user_part_of_project = False
    
    user_projects = res_projects.get_user_projects(username=session.owner)
    
    for project in user_projects:
        if project and project.get("project_id") == session.project.project_id:
            is_user_part_of_project = True
            session.project = Project.from_dict(project)
            break

    if not is_user_part_of_project:
        session.failure_reason = f'User {session.owner} does not belong in the selected project.'
        return session, False

    try:
        software_stack_dict = software_stacks.get_software_stack(stack_id=session.software_stack_id, base_os=session.base_os, get_project_details=True)
        software_stack = VirtualDesktopSoftwareStack.from_ddb_dict(software_stack_dict)
    except SoftwareStackNotFound:
        session.failure_reason = f'Invalid session.software_stack.stack_id: {session.software_stack_id} and/or session.software_stack.base_os: {session.base_os}'
        return session, False

    if software_stack.enabled is False:
        session.failure_reason = f'Software stack {session.software_stack_id} is not available'
        return session, False

    is_software_stack_part_of_project = False
    for project in software_stack.projects:
        if project and project.project_id == session.project.project_id:
            is_software_stack_part_of_project = True
            break

    if not is_software_stack_part_of_project:
        session.failure_reason = f'session.software_stack_id: {session.software_stack_id} is not part of session.project.project_id: {session.project.project_id}'
        return session, False

    try:
        enforce_project_budgets = cluster_settings.get_setting("vdc.controller.enforce_project_budgets")
    except Exception as e:
        logger.warning(f"Failed to retrieve enforce_project_budgets setting, defaulting to False: {e}")
        enforce_project_budgets = False

    if enforce_project_budgets:
        session, is_valid = _validate_project_budget(session)
        if not is_valid:
            return session, False
    else:
        logger.info("VDI Project budgets are disabled (vdc.controller.enforce_project_budgets). Not checking budgets.")

    session.software_stack = software_stack

    valid_instance_types_dict = get_valid_instance_types_by_allowed_list( 
        hibernation_support=session.hibernation_enabled,
        allowed_instance_types=session.software_stack.allowed_instance_types,
    )
    if session.server.instance_type not in valid_instance_types_dict.keys():
        session.failure_reason = f'Invalid session.server.instance_type: {session.server.instance_type}. Not allowed for current configuration'
        return session, False

    session, is_valid = validate_attempt_subnets(session)
    
    if not is_valid:
        return session, False

    if session.hibernation_enabled:
        if session.base_os == VirtualDesktopBaseOs.UBUNTU2404.value:
            session.failure_reason = f'OS {session.base_os} does not support Instance Hibernation.'
            return session, False
        elif session.base_os == VirtualDesktopBaseOs.WINDOWS.value:
            ram_mib, _ = get_instance_ram(session.server.instance_type)
            ram_gib = ram_mib / 1024
            if ram_gib > constants.DEFAULT_HIBERNATION_RAM_LIMIT_WINDOWS:
                session.failure_reason = f'OS {session.base_os} does not support Instance Hibernation for instances with RAM greater than {constants.DEFAULT_HIBERNATION_RAM_LIMIT_WINDOWS}GiB.'
                return session, False

    # // https://docs.aws.amazon.com/dcv/latest/adminguide/servers.html - AMD GPU, Windows support Console sessions only
    if session.type is VirtualDesktopSessionType.VIRTUAL and session.base_os == VirtualDesktopBaseOs.WINDOWS.value:
        session.failure_reason = f'{session.base_os} does not support Virtual Sessions'
        return session, False

    gpu_manufacturer = get_gpu_manufacturer(session.server.instance_type)
    if session.type is VirtualDesktopSessionType.VIRTUAL and gpu_manufacturer is VirtualDesktopGpu.AMD:
        session.failure_reason = f'Instance type: {session.server.instance_type} with GPU {gpu_manufacturer} does not support Virtual Sessions'
        return session, False

    if session.software_stack.placement and session.software_stack.placement.tenancy == VirtualDesktopTenancy.HOST and not dedicated_hosts_supported(session.server.instance_type):
        session.failure_reason = f'Instance type: {session.server.instance_type} does not support Dedicated Hosts tenancy'
        return session, False

    max_root_volume_size = cluster_settings.get_setting("vdc.dcv_session.max_root_volume_memory")
    if session.server.root_volume_size.value > max_root_volume_size:
        session.failure_reason = f'root volume size: {session.server.root_volume_size} is greater than maximum allowed root volume size: {max_root_volume_size} GB.'
        return session, False
    
    min_root_volume = software_stack.min_storage
    if session.hibernation_enabled:
        ram_mib, _ = get_instance_ram(session.server.instance_type)
        ram_gb = ram_mib * (1024 ** 2) / (1000 ** 3)
        min_root_volume = ResMemory(value=software_stack.min_storage.value + ram_gb, unit=software_stack.min_storage.unit)

    if session.server.root_volume_size.value < min_root_volume.value:
        session.failure_reason = f'root volume size: {session.server.root_volume_size.value} is less than the minimum required root volume size: {min_root_volume.value} when hibernation is {"enabled" if session.hibernation_enabled else "disabled"}.'
        return session, False

    return session, True


def complete_create_session_request(session: VirtualDesktopSession, user: str) -> VirtualDesktopSession:
    
    if not session.name:
        session.name = str(uuid4())

    gpu_manufacturer = get_gpu_manufacturer(session.server.instance_type if session.server else None)
    if not session.type:
        if session.base_os is VirtualDesktopBaseOs.WINDOWS or gpu_manufacturer is VirtualDesktopGpu.AMD:
            session.type = VirtualDesktopSessionType.CONSOLE
        else:
            session.type = VirtualDesktopSessionType[cluster_settings.get_setting('vdc.dcv_session.default_dcv_session_type')]

    if not session.server:
        session.server = VirtualDesktopServer()
    
    if not session.server.root_volume_iops:
        session.server.root_volume_iops = constants.DEFAULT_ROOT_VOL_IOPS

    if not getattr(session.project, 'policy_arns', None):
        session.server.instance_profile_arn = cluster_settings.get_setting('vdc.dcv_host_instance_profile_arn')
    else:
        session.server.instance_profile_arn = iam_utils.build_vdi_instance_profile_arn(session.project.name)

    if not session.server.key_pair_name:
        session.server.key_pair_name = cluster_settings.get_setting('cluster.network.ssh_key_pair')

    if not session.server.security_groups:
        session.server.security_groups = []

    security_group_ids = set(session.server.security_groups or [])
    security_group_ids.add(cluster_settings.get_setting('vdc.dcv_host_security_group_id'))
    additional_security_groups = cluster_settings.get_setting('vdc.dcv_session.additional_security_groups')
    security_group_ids.update(additional_security_groups)
    project_security_groups = getattr(session.project, 'security_groups', None)
    if project_security_groups:
        security_group_ids.update(project_security_groups)
    session.server.security_groups = list(security_group_ids)
    session.idea_session_id = str(uuid4())

    return session


def _validate_project_budget(session: VirtualDesktopSession) -> Tuple[VirtualDesktopSession, bool]:
    """Check if the project budget has been exceeded."""
    project_budget = getattr(session.project, 'budget', None)
    if not project_budget:
        logger.info(f"Project budget disabled or not configured for {session.project.name}")
        return session, True

    project_budget_name = getattr(project_budget, 'budget_name', None)
    if not project_budget_name:
        return session, True

    logger.info(f"Found Budget name: {project_budget_name}")
    try:
        budget_info = budget_utils.get_budget(budget_name=project_budget_name)
    except Exception as e:
        logger.warning(f"Failed to retrieve budget {project_budget_name}: {e}. Proceeding without budget check.")
        return session, True

    if budget_info and budget_info['actual_spend'] > budget_info['budget_limit']:
        logger.error(f"Budget exceeded for {project_budget_name}. Denying session request.")
        session.failure_reason = f"Project {project_budget_name} budget has been exceeded. Unable to start session. Contact your Administrator."
        return session, False

    return session, True


def validate_attempt_subnets(session: VirtualDesktopSession):
    configured_vdi_subnets = cluster_settings.get_setting('vdc.dcv_session.network.private_subnets')
    cluster_private_subnets = cluster_settings.get_setting('cluster.network.private_subnets')
    
    attempt_subnets = []
    if session.server and session.server.subnet_id:
        attempt_subnets.append(session.server.subnet_id)
    elif configured_vdi_subnets:
        logger.debug(f"Found configured VDI subnets: {', '.join(configured_vdi_subnets)}")
        attempt_subnets = configured_vdi_subnets
    else:
        logger.debug(f"Fallback to cluster private_subnets: {', '.join(cluster_private_subnets)}")
        attempt_subnets = cluster_private_subnets

    if not attempt_subnets:
        session.failure_reason = f'No subnets available for deployment'
        return session, False, attempt_subnets

    session.attempt_subnets = attempt_subnets

    return session, True


def _create_session(session: VirtualDesktopSession) -> VirtualDesktopSession: 
    try:
        default_schedule = res_schedules.get_default_schedules()
        if default_schedule:
            for day, day_schedule in default_schedule.items():
                default_schedule[day] = {
                    **day_schedule,
                    'idea_session_id': session.idea_session_id,
                    'idea_session_owner': session.owner,
                }
            session.schedule = default_schedule
        
        host_provisioning_response = build_user_data_and_provision_dcv_host_for_session(session)
        instances = host_provisioning_response.get('Instances', [])
        session.server.instance_id = instances[0].get('InstanceId', None)

    except Exception as e:
        logger.error(f"Failed to provision host for session: {session.failure_reason}")
        session.failure_reason = f'{e}'
        return session

    session.state = VirtualDesktopSessionState.PROVISIONING
    db_entry = res_sessions.create_session(session.to_ddb_dict())
    return VirtualDesktopSession.from_ddb_dict(db_entry)


def _has_fsx_lustre_file_systems() -> bool:
    """Check if any FSx Lustre file systems are onboarded."""
    entries = cluster_settings_utils.get_config_entries(
        query=r"shared-storage\..+\.fsx_lustre\..+"
    )
    return len(entries) > 0


def _build_userdata(session: VirtualDesktopSession):
    project_dict = session.project.to_dict() 

    gpu_family = "NONE"
    if gpu_utils.is_nvidia_gpu(session.server.instance_type):
        gpu_family = "NVIDIA"
    elif gpu_utils.is_amd_gpu(session.server.instance_type):
        gpu_family = "AMD"

    rerun_on_reboot = script_utils._retrieve_rerun_on_reboot(project_dict, ScriptOSType.LINUX)
    on_vdi_start_script_commands = script_utils._retrieve_scripts_as_commands(project_dict, ScriptOSType.LINUX, ScriptEventType.ON_VDI_START)
    on_vdi_configured_script_commands = script_utils._retrieve_scripts_as_commands(project_dict, ScriptOSType.LINUX, ScriptEventType.ON_VDI_CONFIGURED)

    on_vdi_start_script_store = script_utils._store_commands_as_linux_script(on_vdi_start_script_commands, ScriptEventType.ON_VDI_START.value)
    on_vdi_configured_script_store = script_utils._store_commands_as_linux_script(on_vdi_configured_script_commands, ScriptEventType.ON_VDI_CONFIGURED.value)

    lock_file = "/root/bootstrap/semaphore/custom_script.lock"
    instance_ready_lock_file = "/root/bootstrap/semaphore/instance_ready.lock"
    custom_script_check = [f"if [[ ! -f {lock_file} ]]; then"]
    if rerun_on_reboot:
        custom_script_check = [f"if [[ ! -f {lock_file} || -f {instance_ready_lock_file} ]]; then"]

    custom_script_commands = custom_script_check + [
        *on_vdi_start_script_store,
        *on_vdi_configured_script_store,
        f'/bin/bash scripts/virtual-desktop-host/linux/export_launch_script_env.sh -p {session.project.project_id} -o {session.owner} -n {session.project.name} -e {cluster_settings.get_setting("cluster.cluster_name")} -c {ScriptEventType.ON_VDI_CONFIGURED.value}.sh -s {ScriptEventType.ON_VDI_START.value}.sh -r {rerun_on_reboot}',
        'source /etc/launch_script_environment',
        f'/bin/bash scripts/virtual-desktop-host/linux/{ScriptEventType.ON_VDI_START.value}.sh',
        f"echo $(date +%s) > {lock_file}",
        "fi"
    ]

    custome_broker_api_url = cluster_settings.get_setting("vdc.custom_credential_broker_api_gateway_url")
    region = cluster_settings.get_setting("cluster.aws.region")
    jwt_token = "DefaultValue"

    try:
        secret_value = cluster_settings.get_secret("vdc.custom_credential_broker_secret_name")
        current_time = int(time.time())
        payload = {
            "region": region,
            "project_name": session.project.name,
            "session_owner": session.owner,
            "session_id": session.idea_session_id,
            "iat": current_time,
            "exp": current_time + 31536000,
            "role_arn": cluster_settings.get_setting("vdc.dcv_host_role_arn"),
            "role_session_name": f"{session.owner}-{session.idea_session_id}"
        }
        jwt_token = jwt.encode(payload, secret_value, algorithm="HS256")
    except Exception as e:
        logger.info(f"Error retriving secret from secret manager {str(e)}")

    session_type_name = session.type.name

    # Check if FSx Lustre file systems are onboarded
    enable_lustre = 'true' if _has_fsx_lustre_file_systems() else 'false'

    install_commands = custom_script_commands + [
        f'/bin/bash scripts/virtual-desktop-host/linux/install.sh -m {constants.MODULE_ID_VIRTUAL_DESKTOP_APP} -g {gpu_family} -u {custome_broker_api_url} -t {jwt_token} -p false -e {cluster_settings.get_setting("cluster.cluster_name")} -n {session.project.name} -o {session.owner} -d {session_type_name} -i {session.idea_session_id} -a {region} -h {session.hibernation_enabled or False} -l {enable_lustre}'
    ]

    if session.base_os == VirtualDesktopBaseOs.WINDOWS:
        install_commands = _build_windows_install_commands(session, project_dict, jwt_token, custome_broker_api_url)

    https_proxy = cluster_settings.get_setting('cluster.network.https_proxy')
    no_proxy = cluster_settings.get_setting('cluster.network.no_proxy')
    proxy_config = {}
    if https_proxy:
        proxy_config = {
            'http_proxy': https_proxy,
            'https_proxy': https_proxy,
            'no_proxy': no_proxy
        }

    user_data_builder = BootstrapUserDataBuilder(
        base_os=session.base_os.value,
        aws_region=cluster_settings.get_setting('cluster.aws.region'),
        bootstrap_package_uri=cluster_settings.get_setting('cluster.installation_scripts_uri'),
        install_commands=install_commands,
        proxy_config=proxy_config,
    )

    user_data = user_data_builder.build()
    return user_data


def _build_windows_install_commands(session: VirtualDesktopSession, project_dict: dict, jwt_token: str, broker_api_url: str) -> List[str]:
    """Build Windows-specific install commands for VDI bootstrap."""
    change_directory_command = ['cd \"scripts\\virtual-desktop-host\\windows\"']
    on_vdi_start_script_commands = script_utils._retrieve_scripts_as_commands(project_dict, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_START)
    on_vdi_configured_script_commands = script_utils._retrieve_scripts_as_commands(project_dict, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_CONFIGURED)
    on_vdi_start_script_store = script_utils._store_commands_as_windows_script(on_vdi_start_script_commands, ScriptEventType.ON_VDI_START.value)
    on_vdi_configured_script_store = script_utils._store_commands_as_windows_script(on_vdi_configured_script_commands, ScriptEventType.ON_VDI_CONFIGURED.value)
    export_env_variables_commands = ['Import-Module .\\ExportLaunchScriptEnv.ps1',
                                        f'Export-EnvironmentVariables -ProjectId "{session.project.project_id}" -OwnerId "{session.owner}" -EnvName "{cluster_settings.get_setting("cluster.cluster_name")}" -ProjectName "{session.project.name}" -OnVDIStartCommands "{ScriptEventType.ON_VDI_START.value}.ps1" -OnVDIConfigureCommands "{ScriptEventType.ON_VDI_CONFIGURED.value}.ps1"']
    on_vdi_start_script_commands = ['& .\\$env:ON_VDI_START_COMMANDS']
    return change_directory_command + export_env_variables_commands + on_vdi_start_script_store + on_vdi_configured_script_store + on_vdi_start_script_commands + [
        'Import-Module .\\Install.ps1',
        f'Install-WindowsEC2Instance -ConfigureForRESVDI -AWSRegion "{cluster_settings.get_setting("cluster.aws.region")}" -ENVName "{cluster_settings.get_setting("cluster.cluster_name")}" -ModuleID "{constants.MODULE_ID_VIRTUAL_DESKTOP_APP}" -ProjectName {session.project.name} -SessionOwner "{session.owner}" -SessionId "{session.idea_session_id}" -BootstrapToken "{jwt_token}" -CustomBrokerApi "{broker_api_url}" -OnVDIConfiguredCommands "{ScriptEventType.ON_VDI_CONFIGURED.value}.ps1"'
    ]


def build_user_data_and_provision_dcv_host_for_session(session: VirtualDesktopSession) -> dict:
    
    tags = {
        "Name": f'{cluster_settings.get_setting("cluster.cluster_name")}-{session.name}-{session.owner}',
        constants.RES_TAG_NODE_TYPE: constants.NODE_TYPE_DCV_HOST,
        constants.RES_TAG_ENVIRONMENT_NAME: cluster_settings.get_setting("cluster.cluster_name"),
        constants.RES_TAG_MODULE_ID: constants.MODULE_ID_VDC,
        constants.RES_TAG_MODULE_NAME: constants.MODULE_NAME_VDC,
        constants.RES_TAG_MODULE_VERSION: _module_version,
        constants.RES_TAG_BACKUP_PLAN: f'{cluster_settings.get_setting("cluster.cluster_name")}-{constants.MODULE_ID_VDC}',
        constants.RES_TAG_PROJECT: session.project.name,
        constants.RES_TAG_DCV_SESSION_ID: 'TBD'
    }

    project_tags = getattr(session.project, 'tags', None)
    if project_tags:
        for tag in project_tags:
            tags[tag.get("key")] = tag.get("value")

    custom_tags = cluster_settings.get_setting('global-settings.custom_tags')
    custom_tags_dict = res_tags.convert_custom_tags_to_key_value_pairs(custom_tags)
    session_tags = res_tags.convert_tags_list_of_dict_to_tags_dict(getattr(session, 'tags', []) or [])
    tags = {**custom_tags_dict, **tags, **session_tags}

    aws_tags = [{'Key': key, 'Value': value} for key, value in tags.items()]
    metadata_http_tokens = cluster_settings.get_setting('vdc.dcv_session.metadata_http_tokens')
    kms_key_id = cluster_settings.get_setting('cluster.ebs.kms_key_id') or 'alias/aws/ebs'
    logger.info(f"kms_key_id: {kms_key_id}")
    
    attempt_subnets = attempt_subnets = session.attempt_subnets
    
    subnet_autoretry_method = cluster_settings.get_setting('vdc.dcv_session.network.subnet_autoretry')
    randomize_subnet_method = cluster_settings.get_setting('vdc.dcv_session.network.randomize_subnets')
    
    if randomize_subnet_method:
        random.shuffle(attempt_subnets)
        logger.debug(f"Applying randomize to subnet list due to configuration.")

    placement = {"Tenancy": session.software_stack.placement.tenancy if session.software_stack.placement else VirtualDesktopTenancy.DEFAULT}
    if placement["Tenancy"] == VirtualDesktopTenancy.HOST:
        placement["Affinity"] = session.software_stack.placement.affinity
        if session.software_stack.placement.host_id:
            placement["HostId"] = session.software_stack.placement.host_id
        else:
            placement["HostResourceGroupArn"] = session.software_stack.placement.host_resource_group_arn

    logger.debug(f"Deployment Attempt Ready - Retry: {subnet_autoretry_method} Attempt_Subnets({len(attempt_subnets)}): {', '.join(attempt_subnets)}")

    return _provision_ec2_instance(session, attempt_subnets, subnet_autoretry_method, aws_tags, metadata_http_tokens, kms_key_id, placement)


def _provision_ec2_instance(session: VirtualDesktopSession, attempt_subnets: List[str], subnet_autoretry: bool, aws_tags: list, metadata_http_tokens: str, kms_key_id: str, placement: dict) -> dict:
    """Attempt to launch an EC2 instance, retrying across subnets if configured."""
    _deployment_loop = 0
    _attempt_provision = True

    while _attempt_provision:
        _deployment_loop += 1
        _subnet_to_try = attempt_subnets.pop(0)
        _remaining_subnet_count = len(attempt_subnets)

        logger.info(f"Deployment attempt #{_deployment_loop} subnet_id: {_subnet_to_try} Remaining Subnets: {_remaining_subnet_count}")
        _attempt_provision = _remaining_subnet_count > 0

        ami_id = session.software_stack.ami_id
        if ami_id and ami_id.startswith("arn:"):
            ami_id = f'resolve:ssm:{get_systems_manager_parameter(ami_id).get("Name", "")}'

        response = None

        logger.info(f"Session data before build userdata: {session}")
        user_data = _build_userdata(session)
        
        try:
            run_instances_params = {
                'UserData': user_data,
                'ImageId': ami_id,
                'InstanceType': session.server.instance_type,
                'TagSpecifications': [{'ResourceType': 'instance', 'Tags': aws_tags}],
                'MaxCount': 1,
                'MinCount': 1,
                'NetworkInterfaces': [{
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': False,
                    'SubnetId': _subnet_to_try,
                    'Groups': session.server.security_groups
                }],
                'IamInstanceProfile': {'Arn': session.server.instance_profile_arn},
                'BlockDeviceMappings': [{
                    'DeviceName': ec2_utils.get_ec2_block_device_name(session.base_os),
                    'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeSize': int(session.server.root_volume_size.value),
                        'Encrypted': constants.DEFAULT_VOLUME_ENCRYPTION_VDI,
                        'KmsKeyId': kms_key_id,
                        'VolumeType': constants.DEFAULT_VOLUME_TYPE_VDI,
                    }
                }],
                'HibernationOptions': {'Configured': session.hibernation_enabled or False},
                'MetadataOptions': {'HttpTokens': metadata_http_tokens, 'HttpEndpoint': 'enabled'},
                'Placement': placement,
            }
            
            if session.server.key_pair_name:
                logger.info(f"key pair name {session.server.key_pair_name}")
                run_instances_params['KeyName'] = session.server.key_pair_name
            
            response = ec2_client.run_instances(**run_instances_params)
        except Exception as err:
            logger.warning(f"Encountered Deployment Exception: {err} / Response: {response}")
            logger.debug(f"Remaining subnets {len(attempt_subnets)}: {attempt_subnets}")
            if subnet_autoretry and _attempt_provision:
                logger.debug(f"Continue with next attempt with remaining subnets..")
                continue
            else:
                logger.warning(f"Exhausted all deployment attempts. Cannot continue with this request.")
                raise err

        if response:
            logger.debug(f"Returning response: {response}")
            return response


def validate_batch_stop_sessions(sessions, user):
    """
    Validate and authorize sessions for batch stop.
    Returns (validated_sessions_list, unsuccessful_list) where unsuccessful_list is a list of BatchStopSessionFailure.
    """
    validated_sessions_list = []
    unsuccessful_list = []
    is_admin = accounts.is_active_admin(user)

    for session in sessions:
        if not session.idea_session_id:
            unsuccessful_list.append(BatchStopSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.BADREQUESTEXCEPTION,
                message="idea_session_id is required"
            ))
            continue

        if is_admin:
            validated_sessions_list.append(session)
            continue

        try:
            res_sessions.get_session(user, session.idea_session_id)
            validated_sessions_list.append(session)
        except res_exceptions.UserSessionNotFound:
            unsuccessful_list.append(BatchStopSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.FORBIDDENEXCEPTION,
                message="Non Admin users can submit requests for themselves only"
            ))
        except Exception as e:
            logger.error(f"Unexpected error checking session {session.idea_session_id}: {e}")
            unsuccessful_list.append(BatchStopSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
                message="Failed to verify session ownership"
            ))

    return validated_sessions_list, unsuccessful_list


def validate_batch_reboot_sessions(sessions, user):
    """
    Validate and authorize sessions for batch reboot.
    Checks: required fields, authorization, session exists, state, and active connections.
    Returns (validated_sessions_list, unsuccessful_list) where unsuccessful_list is a list of BatchRebootSessionFailure.
    """
    validated_sessions_list = []
    unsuccessful_list = []
    is_admin = accounts.is_active_admin(user)

    for session in sessions:
        if not session.idea_session_id:
            unsuccessful_list.append(BatchRebootSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.BADREQUESTEXCEPTION,
                message="idea_session_id is required"
            ))
            continue

        # Single DDB lookup — also serves as ownership check for non-admin
        try:
            lookup_owner = user if not is_admin else session.owner
            existing_session = res_sessions.get_session(lookup_owner, session.idea_session_id)
        except res_exceptions.UserSessionNotFound:
            error_code = BatchOperationErrorCode.FORBIDDENEXCEPTION if not is_admin else BatchOperationErrorCode.BADREQUESTEXCEPTION
            message = "Non Admin users can submit requests for themselves only" if not is_admin else f"Invalid RES Session ID: {session.idea_session_id}. Session not found."
            unsuccessful_list.append(BatchRebootSessionFailure(
                session=session,
                error_code=error_code,
                message=message,
            ))
            continue
        except Exception as e:
            logger.error(f"Unexpected error checking session {session.idea_session_id}: {e}")
            unsuccessful_list.append(BatchRebootSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
                message="Failed to verify session ownership"
            ))
            continue

        # Validate instance_id exists
        if not existing_session.get("server", {}).get("instance_id"):
            unsuccessful_list.append(BatchRebootSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.BADREQUESTEXCEPTION,
                message=f"Session {session.idea_session_id} has no associated instance."
            ))
            continue

        # Validate state
        state = existing_session.get("state", "")
        if state not in {"READY", "ERROR"}:
            unsuccessful_list.append(BatchRebootSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.BADREQUESTEXCEPTION,
                message=f"Session {session.idea_session_id} is in {state} state. Can't reboot. Wait for it to be READY or ERROR."
            ))
            continue

        # Check active connections unless force=True
        if not session.force:
            sessions_with_count = get_active_counts_for_sessions([existing_session])
            if sessions_with_count and sessions_with_count[0].get("connection_count", 0) > 0:
                count = sessions_with_count[0].get("connection_count")
                unsuccessful_list.append(BatchRebootSessionFailure(
                    session=session,
                    error_code=BatchOperationErrorCode.CONFLICTEXCEPTION,
                    message=f"There exists {count} active connection(s) for session_id: {session.idea_session_id}. Please terminate."
                ))
                continue

        validated_sessions_list.append(existing_session)

    return validated_sessions_list, unsuccessful_list


def validate_batch_delete_sessions(sessions, user):
    """
    Validate and authorize sessions for batch delete.
    Looks up each session in DDB to verify ownership and project rather than trusting client-provided values.
    Non-admin users can delete their own sessions, or others' sessions with vdis.create_terminate_others_sessions permission.
    Returns (validated_sessions_list, unsuccessful_list) where unsuccessful_list is a list of BatchDeleteSessionFailure.
    """
    validated_sessions_list = []
    unsuccessful_list = []
    is_admin = accounts.is_active_admin(user)

    for session in sessions:
        if not session.idea_session_id or not session.owner:
            unsuccessful_list.append(BatchDeleteSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.BADREQUESTEXCEPTION,
                message="idea_session_id and session.owner are required"
            ))
            continue

        # Look up session in DDB to get authoritative owner and project
        if is_admin:
            # Admin: trust client-provided owner for lookup since admin bypasses all auth checks
            try:
                ddb_session = res_sessions.get_session(session.owner, session.idea_session_id)
            except res_exceptions.UserSessionNotFound:
                unsuccessful_list.append(BatchDeleteSessionFailure(
                    session=session,
                    error_code=BatchOperationErrorCode.BADREQUESTEXCEPTION,
                    message="Session not found"
                ))
                continue
            except Exception as e:
                logger.error(f"Unexpected error looking up session {session.idea_session_id}: {e}")
                unsuccessful_list.append(BatchDeleteSessionFailure(
                    session=session,
                    error_code=BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
                    message="Failed to look up session"
                ))
                continue
            validated = VirtualDesktopSession.from_ddb_dict(ddb_session)
            validated.force = session.force
            validated_sessions_list.append(validated)
            continue

        # Non-admin: first try lookup with authenticated user (own session case)
        own_session = res_sessions.get_session_if_owner(user, session.idea_session_id)
        if own_session:
            validated = VirtualDesktopSession.from_ddb_dict(own_session)
            validated.force = session.force
            validated_sessions_list.append(validated)
            continue

        # Not the owner — look up session in DDB first, then check permission using authoritative project_id
        # This ensures we never trust client-provided project_id for authorization decisions
        try:
            ddb_session = res_sessions.get_session(session.owner, session.idea_session_id)
        except res_exceptions.UserSessionNotFound:
            unsuccessful_list.append(BatchDeleteSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.FORBIDDENEXCEPTION,
                message="You're not authorized to terminate others' sessions in this project."
            ))
            continue
        except Exception as e:
            logger.error(f"Unexpected error looking up session {session.idea_session_id}: {e}")
            unsuccessful_list.append(BatchDeleteSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
                message="Failed to look up session"
            ))
            continue

        ddb_project_id = ddb_session.get('project', {}).get('project_id')
        if not ddb_project_id:
            unsuccessful_list.append(BatchDeleteSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.FORBIDDENEXCEPTION,
                message="You're not authorized to terminate others' sessions in this project."
            ))
            continue

        resource_key = f'{ddb_project_id}:project'
        user_permissions = role_assignments.get_user_permissions(user, resource_key)
        if 'vdis.create_terminate_others_sessions' not in user_permissions:
            unsuccessful_list.append(BatchDeleteSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.FORBIDDENEXCEPTION,
                message="You're not authorized to terminate others' sessions in this project."
            ))
            continue

        logger.info(f'Session deletion requested by {user} for session {session.idea_session_id} owned by {ddb_session.get("owner")}')
        validated = VirtualDesktopSession.from_ddb_dict(ddb_session)
        validated.force = session.force
        validated_sessions_list.append(validated)

    return validated_sessions_list, unsuccessful_list


def validate_batch_start_sessions(sessions, user):
    """
    Validate and authorize sessions for batch start.
    Looks up each session in DDB to verify existence and ownership rather than trusting client-provided values.
    Returns (validated_sessions_list, unsuccessful_list) where unsuccessful_list is a list of BatchStartSessionFailure.
    """
    validated_sessions_list = []
    unsuccessful_list = []
    is_admin = accounts.is_active_admin(user)

    for session in sessions:
        if not session.idea_session_id or not session.owner:
            unsuccessful_list.append(BatchStartSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.BADREQUESTEXCEPTION,
                message="idea_session_id and session.owner are required"
            ))
            continue

        lookup_user = session.owner if is_admin else user
        try:
            ddb_session = res_sessions.get_session(lookup_user, session.idea_session_id)
        except res_exceptions.UserSessionNotFound:
            error_code = BatchOperationErrorCode.BADREQUESTEXCEPTION if is_admin else BatchOperationErrorCode.FORBIDDENEXCEPTION
            message = "Session not found" if is_admin else "Non Admin users can submit requests for themselves only"
            unsuccessful_list.append(BatchStartSessionFailure(
                session=session,
                error_code=error_code,
                message=message,
            ))
            continue
        except Exception as e:
            logger.error(f"Unexpected error looking up session {session.idea_session_id}: {e}")
            unsuccessful_list.append(BatchStartSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
                message="Failed to look up session"
            ))
            continue

        state = ddb_session.get('state', '')
        if state not in {'STOPPED', 'STOPPED_IDLE'}:
            unsuccessful_list.append(BatchStartSessionFailure(
                session=session,
                error_code=BatchOperationErrorCode.BADREQUESTEXCEPTION,
                message=f"Session is in {state} state. Can only start sessions in STOPPED or STOPPED_IDLE state"
            ))
            continue

        validated_sessions_list.append(VirtualDesktopSession.from_ddb_dict(ddb_session))

    return validated_sessions_list, unsuccessful_list
