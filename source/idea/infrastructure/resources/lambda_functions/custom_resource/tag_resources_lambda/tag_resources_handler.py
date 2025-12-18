#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Dict, List, Optional, Set

import boto3
from botocore.exceptions import ClientError
from res.clients.aws.aws_client_provider import AwsClientProvider  # type: ignore
from res.constants import (  # type: ignore
    AWS_TAG_CFN_STACK_NAME,
    ENVIRONMENT_NAME_KEY,
    ENVIRONMENT_NAME_TAG_KEY,
    EVENT_SOURCE_MAPPING_RESOURCE_TYPE,
    EVENTBRIDGE_RULE_RESOURCE_TYPE,
    INSTANCE_NODE_TYPE_TAG_KEY,
    INSTANCE_PROFILE_RESOURCE_TYPE,
    LAUNCH_TEMPLATE_RESOURCE_TYPE,
    LOAD_BALANCER_RESOURCE_TYPE,
    MANAGED_POLICY_RESOURCE_TYPE,
    OLD_CUSTOM_TAG_KEYS,
    PARENT_STACK_NAME_KEY,
)
from res.resources import cluster_settings  # type: ignore
from res.utils import cluster_settings_utils, iam_utils  # type: ignore
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    logger.info(f"Start tag resources not supporting Cloudformation level tagging...")
    resource_properties = event.get("ResourceProperties", {})
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
        Data={},
    )
    try:
        cluster_name = os.environ.get(ENVIRONMENT_NAME_KEY, "")
        parent_stack_name = os.environ.get(PARENT_STACK_NAME_KEY, "")
        old_custom_tag_keys_string = resource_properties.get(OLD_CUSTOM_TAG_KEYS, "")
        if event["RequestType"] == "Create" or event["RequestType"] == "Update":
            custom_tags = cluster_settings_utils.convert_custom_tags_to_dict_list(
                cluster_settings.get_setting("global-settings.custom_tags")
            )

            if not custom_tags and not old_custom_tag_keys_string:
                logger.info(
                    "No old and new custom tags found, skipping resource tagging."
                )
                return

            old_custom_tag_keys = (
                old_custom_tag_keys_string.split(";")
                if old_custom_tag_keys_string
                else []
            )

            iam_resource_prefix = cluster_settings.get_setting(
                "cluster.iam.iam_resource_prefix"
            )
            iam_resource_prefix = iam_resource_prefix if iam_resource_prefix else ""

            # Get current environment Cloudformation stacks based on the tagging
            stack_ids: List[str] = [parent_stack_name]
            managed_policy_arns: List[str] = []
            instance_profile_names: List[str] = []
            load_blanacer_arns: List[str] = []
            eventbridge_names: List[str] = []
            launch_template_ids: List[str] = []
            event_source_mapping_uuids: List[str] = []

            resource_collectors = {
                MANAGED_POLICY_RESOURCE_TYPE: managed_policy_arns,
                INSTANCE_PROFILE_RESOURCE_TYPE: instance_profile_names,
                LOAD_BALANCER_RESOURCE_TYPE: load_blanacer_arns,
                EVENTBRIDGE_RULE_RESOURCE_TYPE: eventbridge_names,
                LAUNCH_TEMPLATE_RESOURCE_TYPE: launch_template_ids,
                EVENT_SOURCE_MAPPING_RESOURCE_TYPE: event_source_mapping_uuids,
            }

            cfn_client = boto3.client("cloudformation")

            stack_paginator = cfn_client.get_paginator("list_stacks")
            for page in stack_paginator.paginate(
                StackStatusFilter=[
                    "CREATE_IN_PROGRESS",
                    "CREATE_COMPLETE",
                    "UPDATE_IN_PROGRESS",
                    "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS",
                    "UPDATE_COMPLETE",
                ]
            ):
                for stack_summary in page.get("StackSummaries", []):
                    stack_name = stack_summary.get("StackName", "")

                    describe_response = cfn_client.describe_stacks(StackName=stack_name)
                    stack = describe_response["Stacks"][0]

                    # Check tags
                    for tag in stack.get("Tags", []):
                        if (
                            tag.get("Key", "") == ENVIRONMENT_NAME_TAG_KEY
                            and tag.get("Value", "") == cluster_name
                        ):
                            stack_ids.append(stack.get("StackId", ""))
                            break

            for stack_id in stack_ids:
                resources_paginator = cfn_client.get_paginator("list_stack_resources")
                for page in resources_paginator.paginate(StackName=stack_id):
                    for resource in page.get("StackResourceSummaries", []):
                        resource_type = resource.get("ResourceType", "")
                        physical_id = resource.get("PhysicalResourceId", "")

                        if resource_type in resource_collectors:
                            resource_collectors[resource_type].append(physical_id)

            # Update tagging for resources that do not support Cloudformation level tagging
            _tag_managed_policies(custom_tags, old_custom_tag_keys, managed_policy_arns)
            _tag_instance_profile(
                custom_tags, old_custom_tag_keys, instance_profile_names
            )
            _tag_load_balancer_listeners(
                custom_tags, old_custom_tag_keys, load_blanacer_arns
            )
            _tag_eventbridge_rules(custom_tags, old_custom_tag_keys, eventbridge_names)
            _tag_event_source_mappings(
                custom_tags, old_custom_tag_keys, event_source_mapping_uuids
            )
            _tag_network_interface(
                custom_tags, old_custom_tag_keys, cluster_name, parent_stack_name
            )
            _tag_launch_templates(custom_tags, old_custom_tag_keys, launch_template_ids)

            #  Update tagging for resources created during runtime that cannot be handled by Cloudformation
            if event["RequestType"] == "Update":
                logger.info(
                    "Start updating tags for resources not tracked by CloudFormation."
                )
                _update_tags_secrets(custom_tags, old_custom_tag_keys, cluster_name)
                _update_tags_existing_hosts(
                    custom_tags, old_custom_tag_keys, cluster_name, iam_resource_prefix
                )
                _update_tags_dcv_ddb(custom_tags, old_custom_tag_keys, cluster_name)

    except Exception as e:
        error_message = f"Failed to tag resources not supporting Cloudformation level tagging: {str(e)}"
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logger.error(error_message)
    finally:
        send_response(url=event["ResponseURL"], response=response)


def _tag_managed_policies(
    tags: List[Dict[str, Any]], old_tags_keys: List[str], managed_policy_arns: List[str]
) -> None:

    # Update tags for customer managed policies which does not support Cloudformation level tagging
    iam_client = boto3.client("iam")
    try:
        policies_paginator = iam_client.get_paginator("list_policies")
        for page in policies_paginator.paginate(Scope="Local"):
            for policy in page.get("Policies", []):
                policy_arn = policy.get("Arn", "")
                if policy_arn in managed_policy_arns:
                    if old_tags_keys:
                        iam_client.untag_policy(
                            PolicyArn=policy_arn, TagKeys=old_tags_keys
                        )
                    if tags:
                        iam_client.tag_policy(PolicyArn=policy_arn, Tags=tags)
        logger.info("Successfully tagged managed policies.")
    except Exception as e:
        logger.error(f"Failed to tag managed policies: {e}")


def _tag_instance_profile(
    tags: List[Dict[str, Any]],
    old_tags_keys: List[str],
    instance_profile_names: List[str],
) -> None:

    # Update tags for instance profile which does not support Cloudformation level tagging
    iam_client = boto3.client("iam")

    try:
        profile_paginator = iam_client.get_paginator("list_instance_profiles")
        for page in profile_paginator.paginate():
            for profile in page.get("InstanceProfiles", []):
                profile_name = profile.get("InstanceProfileName", "")
                if profile_name in instance_profile_names:
                    if old_tags_keys:
                        iam_client.untag_instance_profile(
                            InstanceProfileName=profile_name,
                            TagKeys=old_tags_keys,
                        )
                    if tags:
                        iam_client.tag_instance_profile(
                            InstanceProfileName=profile_name, Tags=tags
                        )
        logger.info("Successfully tagged instance profiles.")
    except Exception as e:
        logger.error(f"Failed to tag instance profiles: {e}")


def _tag_launch_templates(
    tags: List[Dict[str, Any]],
    old_tags_keys: List[str],
    launch_template_ids: List[str],
) -> None:

    if not launch_template_ids:
        logger.warning(f"No launch templates found, skipping...")

    # Update tags for launch templates which do not support Cloudformation level tagging
    aws_client_provider = AwsClientProvider()
    ec2_client = aws_client_provider.ec2()

    try:
        if old_tags_keys:
            ec2_client.delete_tags(
                Resources=launch_template_ids,
                Tags=[{"Key": key} for key in old_tags_keys],
            )
        if tags:
            ec2_client.create_tags(Resources=launch_template_ids, Tags=tags)
        logger.info("Successfully tagged launch templates.")
    except Exception as e:
        logger.error(f"Failed to tag launch templates: {e}")


def _tag_load_balancer_listeners(
    tags: List[Dict[str, Any]], old_tags_keys: List[str], load_blanacer_arns: List[str]
) -> None:

    # Update tags for loadbalancer listener which does not support Cloudformation level tagging
    elb_client = boto3.client("elbv2")

    try:
        for lb_arn in load_blanacer_arns:
            listener_paginator = elb_client.get_paginator("describe_listeners")
            for listener_page in listener_paginator.paginate(LoadBalancerArn=lb_arn):
                for listener in listener_page.get("Listeners", []):
                    listener_arn = listener.get("ListenerArn", "")
                    if old_tags_keys:
                        elb_client.remove_tags(
                            ResourceArns=[listener_arn], TagKeys=old_tags_keys
                        )
                    if tags:
                        elb_client.add_tags(ResourceArns=[listener_arn], Tags=tags)
        logger.info("Successfully tagged load balancer listeners.")
    except Exception as e:
        logger.error(f"Failed to tag load balancer listeners: {e}")


def _tag_eventbridge_rules(
    tags: List[Dict[str, Any]], old_tags_keys: List[str], eventbridge_names: List[str]
) -> None:

    # Update tags for eventbridge rule which does not support Cloudformation level tagging
    events_client = boto3.client("events")
    try:
        paginator = events_client.get_paginator("list_rules")
        for page in paginator.paginate():
            for rule in page.get("Rules", []):
                rule_name = rule.get("Name", "")
                rule_arn = rule.get("Arn", "")
                if rule_name in eventbridge_names:
                    if old_tags_keys:
                        events_client.untag_resource(
                            ResourceARN=rule_arn, TagKeys=old_tags_keys
                        )
                    if tags:
                        events_client.tag_resource(ResourceARN=rule_arn, Tags=tags)
        logger.info("Successfully tagged eventbridge rules.")
    except Exception as e:
        logger.error(f"Failed to tag eventbridge rules: {e}")


def _tag_event_source_mappings(
    tags: List[Dict[str, Any]],
    old_tags_keys: List[str],
    event_source_mapping_uuids: List[str],
) -> None:

    # Update tags for Lambda event source mappings which do not support Cloudformation level tagging
    aws_client_provider = AwsClientProvider()
    lambda_client = aws_client_provider.lambda_()

    region = os.environ.get("region")
    account_id = os.environ.get("account_id")

    try:
        for uuid in event_source_mapping_uuids:
            try:
                response = lambda_client.get_event_source_mapping(UUID=uuid)
                # Construct the event source mapping ARN using the UUID
                event_source_mapping_arn = (
                    f"arn:aws:lambda:{region}:{account_id}:event-source-mapping:{uuid}"
                )

                # Convert custom tags list to dict format
                custom_tags = {tag["Key"]: tag["Value"] for tag in tags} if tags else {}

                if old_tags_keys:
                    lambda_client.untag_resource(
                        Resource=event_source_mapping_arn, TagKeys=old_tags_keys
                    )
                if custom_tags:
                    lambda_client.tag_resource(
                        Resource=event_source_mapping_arn, Tags=custom_tags
                    )
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    logger.warning(
                        f"Event source mapping {uuid} not found, skipping..."
                    )
                else:
                    raise
        logger.info("Successfully tagged event source mappings.")
    except Exception as e:
        logger.error(f"Failed to tag event source mappings: {e}")


def _update_tags_secrets(
    tags: List[Dict[str, Any]], old_tags_keys: List[str], cluster_name: str
) -> None:

    # Update tags for secret created during runtime if exists
    secretmanager_client = boto3.client("secretsmanager")
    secret_names_list = [
        f"{cluster_name}-sso-client-secret",
    ]

    try:
        for secret_name in secret_names_list:
            if old_tags_keys:
                secretmanager_client.untag_resource(
                    SecretId=secret_name, TagKeys=old_tags_keys
                )
            if tags:
                secretmanager_client.tag_resource(SecretId=secret_name, Tags=tags)
            logger.info(f"Successfully tagged secret {secret_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.warning(f"Secret {secret_name} not found, skipping...")
        else:
            logger.error(f"Failed to tag secret {secret_name}: {e}")


def _update_tags_existing_hosts(
    tags: List[Dict[str, Any]],
    old_tags_keys: List[str],
    cluster_name: str,
    iam_resource_prefix: str,
) -> None:

    instance_ids: List[str] = []
    ebs_volumes_ids: List[str] = []
    network_interface_ids: List[str] = []
    project_names: Set[str] = set()
    ec2_client = boto3.client("ec2")
    iam_client = boto3.client("iam")

    # Helper function to extract resources IDs and project name from EC2 instances
    def _extract_instance_resources(
        instance: Dict[str, Any],
        instance_ids: List[str],
        ebs_volumes_ids: List[str],
        network_interface_ids: List[str],
        project_names: Optional[Set[str]] = None,
    ) -> None:
        instance_ids.append(instance.get("InstanceId", ""))

        for volume in instance.get("BlockDeviceMappings", []):
            ebs_volumes_ids.append(volume.get("Ebs", {}).get("VolumeId", ""))

        for network_interface in instance.get("NetworkInterfaces", []):
            network_interface_ids.append(
                network_interface.get("NetworkInterfaceId", "")
            )

        if project_names is not None:
            for tag in instance.get("Tags", []):
                if tag.get("Key", "") == "res:Project":
                    project_names.add(tag.get("Value", ""))
                    break

    try:
        # Retrieve VDI ec2 instance info if exists
        instance_paginator = ec2_client.get_paginator("describe_instances")
        for page in instance_paginator.paginate(
            Filters=[
                {
                    "Name": f"tag:{INSTANCE_NODE_TYPE_TAG_KEY}",
                    "Values": [
                        "virtual-desktop-dcv-host",
                    ],
                },
                {
                    "Name": f"tag:{ENVIRONMENT_NAME_TAG_KEY}",
                    "Values": [
                        cluster_name,
                    ],
                },
            ]
        ):
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    _extract_instance_resources(
                        instance,
                        instance_ids,
                        ebs_volumes_ids,
                        network_interface_ids,
                        project_names,
                    )

    except Exception as e:
        logger.error(
            f"Failed to retrieve VDI instances, EBS volumes, and network interfaces: {e}"
        )

    # Retrieve infra-host ec2 instance info if exists
    try:
        host_paginator = ec2_client.get_paginator("describe_instances")
        for page in host_paginator.paginate(
            Filters=[
                {
                    "Name": f"tag:Name",
                    "Values": [
                        f"{cluster_name}-bastion-host",
                        f"{cluster_name}-vdc-controller",
                        f"{cluster_name}-vdc-broker",
                        f"{cluster_name}-vdc-gateway",
                        f"{cluster_name}-cluster-manager",
                    ],
                },
                {
                    "Name": f"tag:{ENVIRONMENT_NAME_TAG_KEY}",
                    "Values": [
                        cluster_name,
                    ],
                },
            ]
        ):
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    _extract_instance_resources(
                        instance,
                        instance_ids,
                        ebs_volumes_ids,
                        network_interface_ids,
                        project_names,
                    )
    except Exception as e:
        logger.error(
            f"Failed to retrieve infra host instance, ebs volumes, and network interfaces: {e}"
        )

    # Update tagging for VDI and infra host EC2 instances, ebs volumes, and network interfaces in batches
    # Note: Other infra hosts will be handled by CloudFormation level tagging
    all_resource_ids = instance_ids + ebs_volumes_ids + network_interface_ids
    batch_size = 50
    for i in range(0, len(all_resource_ids), batch_size):
        batch = all_resource_ids[i : i + batch_size]

        try:
            if old_tags_keys:
                ec2_client.delete_tags(
                    Resources=batch, Tags=[{"Key": key} for key in old_tags_keys]
                )
            if tags:
                ec2_client.create_tags(Resources=batch, Tags=tags)

            logger.info(
                f"Successfully tagged instance, ebs volues, network interfaces in batch: {batch}"
            )
        except Exception as e:
            logger.error(
                f"Failed to update tags for VDI and infra host instance, ebs volumes, and network interfaces in batch: {e}"
            )

    # Update tagging for IAM roles created for projects
    # Note: Instance profiles are handled by _tag_instance_profile
    for project_name in list(project_names):
        role_name = iam_utils.get_vdi_role_name(project_name)

        try:
            if old_tags_keys:
                iam_client.untag_role(RoleName=role_name, TagKeys=old_tags_keys)
                iam_client.untag_instance_profile(
                    InstanceProfileName=role_name,
                    TagKeys=old_tags_keys,
                )
            if tags:
                iam_client.tag_role(RoleName=role_name, Tags=tags)
                iam_client.tag_instance_profile(
                    InstanceProfileName=role_name, Tags=tags
                )
            logger.info(
                f"Successfully tagged IAM role and instance profile {role_name}."
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                logger.warning(
                    f"IAM Role and instance profile {role_name} not found, skipping tags update..."
                )
            else:
                logger.error(
                    f"Failed to update tags for IAM role and instance profile {role_name}: {e}"
                )


def _update_tags_dcv_ddb(
    tags: List[Dict[str, Any]], old_tags_keys: List[str], cluster_name: str
) -> None:

    # Update tags for DCV created DDB tables
    PARTITION = os.environ.get("partition", "")
    REGION = os.environ.get("region", "")
    ACCOUNT_ID = os.environ.get("account_id", "")
    dcv_table_name_prefix = f"{cluster_name}.vdc.dcv-broker"
    ddb_client = boto3.client("dynamodb")
    try:
        table_paginator = ddb_client.get_paginator("list_tables")
        for page in table_paginator.paginate():
            for table_name in page.get("TableNames", []):
                if table_name.startswith(dcv_table_name_prefix):
                    table_arn = f"arn:{PARTITION}:dynamodb:{REGION}:{ACCOUNT_ID}:table/{table_name}"

                    if old_tags_keys:
                        ddb_client.untag_resource(
                            ResourceArn=table_arn, TagKeys=old_tags_keys
                        )
                    if tags:
                        ddb_client.tag_resource(ResourceArn=table_arn, Tags=tags)
        logger.info("Successfully tagged DCV DDB tables.")
    except Exception as e:
        logger.error(f"Failed to update tags for DCV DDB tables: {e}")


def _tag_network_interface(
    tags: List[Dict[str, Any]],
    old_tags_keys: List[str],
    cluster_name: str,
    stack_name: str,
) -> None:

    security_group_ids = []
    network_interface_ids = []
    ec2_client = boto3.client("ec2")

    # Update tags for network interfaces associated with security groups created automatically
    try:
        security_group_paginator = ec2_client.get_paginator("describe_security_groups")
        for page in security_group_paginator.paginate():
            for security_group in page.get("SecurityGroups", []):
                group_id = security_group.get("GroupId", "")
                for tag in security_group.get("Tags", []):
                    tag_key = tag.get("Key", "")
                    tag_value = tag.get("Value", "")
                    if (
                        tag_key == ENVIRONMENT_NAME_TAG_KEY
                        and tag_value == cluster_name
                    ) or (
                        tag_key == AWS_TAG_CFN_STACK_NAME and tag_value == stack_name
                    ):
                        security_group_ids.append(group_id)
                        break

        eni_paginator = ec2_client.get_paginator("describe_network_interfaces")
        for page in eni_paginator.paginate(
            Filters=[{"Name": "group-id", "Values": security_group_ids}]
        ):
            for eni in page.get("NetworkInterfaces", []):
                network_interface_ids.append(eni.get("NetworkInterfaceId", ""))

        if old_tags_keys:
            ec2_client.delete_tags(
                Resources=network_interface_ids,
                Tags=[{"Key": key} for key in old_tags_keys],
            )
        if tags:
            ec2_client.create_tags(Resources=network_interface_ids, Tags=tags)

        logger.info("Successfully tagged network interfaces.")
    except Exception as e:
        logger.error(f"Failed to tag network interfaces: {e}")
