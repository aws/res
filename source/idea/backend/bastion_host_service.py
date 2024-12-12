#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
import json
import os
import time
from typing import Any, Dict

import boto3
import res.exceptions as exceptions  # type: ignore
from botocore.exceptions import ClientError
from res.constants import (  # type: ignore
    BASTION_HOST_ENABLE_DETAILED_MONITORING,
    BASTION_HOST_ENABLE_TERMINATION_PROTECTION,
    BASTION_HOST_HOSTNAME,
    BASTION_HOST_INSTANCE_AMI,
    BASTION_HOST_INSTANCE_ID,
    BASTION_HOST_INSTANCE_PROFILE_NAME,
    BASTION_HOST_INSTANCE_TYPE,
    BASTION_HOST_IS_PUBLIC,
    BASTION_HOST_KMS_KEY_ID,
    BASTION_HOST_PRIVATE_DNS_NAME,
    BASTION_HOST_PRIVATE_IP,
    BASTION_HOST_PUBLIC_IP,
    BASTION_HOST_REQUIRE_IMDSV2,
    BASTION_HOST_SECURITY_GROUP_ID,
    BASTION_HOST_USER_DATA,
    BASTION_HOST_VOLUME_SIZE,
    CLUSTER_KEYPAIR_NAME,
    CLUSTER_ROUTE53_PRIVATE_HOSTED_ZONE_ID,
    CLUSTER_ROUTE53_PRIVATE_HOSTED_ZONE_NAME,
    COGNITO_SSO_IDP_PROVIDER_NAME,
    NODE_TYPE_APP,
    PUBLIC_SUBNETS,
)
from res.resources import accounts, cluster_settings, token  # type: ignore
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME  # type: ignore
from res.utils import api_utils, auth_utils, table_utils  # type: ignore


def check_admin_authorized(event: Dict[str, Any]) -> None:
    # Add Auth logic for active admins to perform this action
    auth_header = event.get("headers", {}).get("authorization", "")
    jwt_token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
    decoded_token = token.decode_token(token=jwt_token)
    if not decoded_token.get("username"):
        raise exceptions.UnauthorizedAccess(message="Username missing in token")

    idp_name_record = table_utils.get_item(
        table_name=CLUSTER_SETTINGS_TABLE_NAME,
        key={"key": COGNITO_SSO_IDP_PROVIDER_NAME},
    )
    idp_name = idp_name_record.get("value") if idp_name_record else None
    username = auth_utils.get_ddb_user_name(
        username=decoded_token["username"], idp_name=idp_name
    )

    if not accounts.is_active_admin(username):
        raise exceptions.UnauthorizedAccess()


def handle_bastion_host_lifecycle(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        check_admin_authorized(event)
        http_method = event.get("httpMethod", "")
        if http_method == "GET":
            return get_bastion_host()
        elif http_method == "PUT":
            return modify_bastion_host(event)
        else:
            return api_utils._create_api_response(  # type: ignore
                status_code=404,
                status_description="404 Not Found",
                body={"error": "Not Found"},
            )
    except exceptions.UnauthorizedAccess as e:
        return api_utils._create_api_response(  # type: ignore
            status_code=401,
            status_description="401 Unauthorized",
            body={"error": str(e)},
        )


def get_bastion_host() -> Dict[str, Any]:
    """
    Retrieves the details of a bastion host EC2 instance from a DynamoDB table, including its
    instance ID, private IP, public IP, and private DNS name.
    It returns a dictionary with the retrieved details or an error message if the DynamoDB operation fails.
    """

    # Query the DynamoDB table for the bastion host's details
    bastion_host_details = _get_bastion_host_details_from_ddb()

    if not bastion_host_details.get("instance_id"):
        return api_utils._create_api_response(  # type: ignore
            status_code=200,
            status_description="Bastion Host is unavailable",
            body="Bastion Host unavailable",
        )

    return api_utils._create_api_response(  # type: ignore
        status_code=200,
        status_description="SSH Access turned on with Bastion Host",
        body=bastion_host_details,
    )


def modify_bastion_host(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates or terminates a bastion host EC2 instance based on the provided event payload.
    It returns a dictionary with a success or error message based on the operation's outcome.
    """

    # Implement the logic for PUT /res/config here
    body = json.loads(event.get("body", "{}"))
    # if ssh_enabled is true, bastion host needs to be created (if one doesn't exist already)
    ssh_enabled = bool(body.get("ssh_enabled", False))
    if ssh_enabled:
        # Check if bastion host already exists
        bastion_host_details = _get_bastion_host_details_from_ddb()
        if bastion_host_details.get("instance_id"):
            return api_utils._create_api_response(  # type: ignore
                status_code=200,
                status_description="Bastion host already exists",
                body=bastion_host_details,
            )
        else:
            bastion_host_config = _get_bastion_host_config_from_ddb()
            new_bastion_host_details = _provision_bastion_host(bastion_host_config)
            _create_route53_record_set(new_bastion_host_details)
            _run_ssm_command_on_vdi_sessions(ssh_enabled)

            # return instance details
            return api_utils._create_api_response(  # type: ignore
                status_code=200,
                status_description="SSH Access is enabled",
                body=new_bastion_host_details,
            )
    else:
        # if ssh_enabled is false, bastion host needs to be terminated (if it exists)
        bastion_host_details = _get_bastion_host_details_from_ddb()
        instance_id = bastion_host_details.get("instance_id")
        if instance_id:
            _cleanup_bastion_host(instance_id)
        _run_ssm_command_on_vdi_sessions(ssh_enabled)

        return api_utils._create_api_response(  # type: ignore
            status_code=200, status_description="SSH Access turned off", body={}
        )


def _run_ssm_command_on_vdi_sessions(enable_ssh: bool) -> None:
    # Initialize DynamoDB and SSM clients
    dynamodb = boto3.resource("dynamodb")
    ssm = boto3.client("ssm")

    # Define the table name
    table_name = f'{os.environ["environment_name"]}.vdc.controller.user-sessions'
    table = dynamodb.Table(table_name)

    # Pre-define SSM commands
    SSH_COMMANDS = {
        "ubuntu2204": f"""
            sudo su -
            systemctl {'enable' if enable_ssh else 'disable'} ssh
            systemctl {'start' if enable_ssh else 'stop'} ssh
        """,
        "default": f"""
            sudo su -
            systemctl {'enable' if enable_ssh else 'disable'} sshd.service
            systemctl {'start' if enable_ssh else 'stop'} sshd.service
            systemctl {'enable' if enable_ssh else 'disable'} sshd.socket
            systemctl {'start' if enable_ssh else 'stop'} sshd.socket
        """,
    }

    try:
        instances = {}
        last_evaluated_key = None

        # Scan DynamoDB table
        while True:
            scan_params = {
                "ProjectionExpression": "server.instance_id, base_os",
                "FilterExpression": "NOT contains(#base_os, :windows)",
                "ExpressionAttributeNames": {"#base_os": "base_os"},
                "ExpressionAttributeValues": {":windows": "windows"},
            }

            if last_evaluated_key:
                scan_params["ExclusiveStartKey"] = last_evaluated_key

            response = table.scan(**scan_params)

            # Update instances dictionary
            instances.update(
                {
                    item["server"]["instance_id"]: str(item["base_os"]).lower()
                    for item in response["Items"]
                }
            )

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        # Run SSM command on each instance
        for instance_id, base_os in instances.items():
            try:
                ssm.send_command(
                    InstanceIds=[instance_id],
                    DocumentName="AWS-RunShellScript",
                    Parameters={
                        "commands": [SSH_COMMANDS.get(base_os, SSH_COMMANDS["default"])]
                    },
                )
                print(f"SSM command sent to instance {instance_id}")
            except ClientError as e:
                print(f"Error sending SSM command to instance {instance_id}: {e}")

    except ClientError as e:
        print(f"Error scanning DynamoDB table or running SSM command: {e}")


def _cleanup_bastion_host(instance_id: str) -> None:
    # Terminate EC2 instance
    ec2 = boto3.client("ec2")
    ec2.terminate_instances(InstanceIds=[instance_id])

    keys_to_delete = [
        BASTION_HOST_INSTANCE_ID,
        BASTION_HOST_PRIVATE_IP,
        BASTION_HOST_PUBLIC_IP,
        BASTION_HOST_PRIVATE_DNS_NAME,
    ]

    for key in keys_to_delete:
        table_utils.delete_item(
            table_name=CLUSTER_SETTINGS_TABLE_NAME, key={"key": key}
        )


def _provision_bastion_host(bastion_host_config: Dict[str, Any]) -> Dict[str, str]:
    ec2 = boto3.client("ec2")

    # Launch the bastion host instance
    instance = ec2.run_instances(
        ImageId=bastion_host_config.get("instance_ami"),
        InstanceType=bastion_host_config.get("instance_type"),
        MinCount=1,
        MaxCount=1,
        KeyName=bastion_host_config.get("key_pair"),
        SecurityGroupIds=[bastion_host_config.get("security_group_id")],
        SubnetId=bastion_host_config.get("subnet_id"),
        UserData=bastion_host_config.get("user_data", ""),
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/xvda",
                "Ebs": {
                    "VolumeSize": bastion_host_config.get("volume_size", 200),
                    "VolumeType": "gp3",
                    "Encrypted": True,
                    "KmsKeyId": bastion_host_config.get("kms_key_id"),
                },
            }
        ],
        MetadataOptions={
            "HttpTokens": (
                "required"
                if bastion_host_config.get("require_imdsv2", False)
                else "optional"
            ),
            "HttpEndpoint": "enabled",
        },
        Monitoring={
            "Enabled": bastion_host_config.get("enable_detailed_monitoring", False)
        },
        IamInstanceProfile={"Name": bastion_host_config.get("instance_profile")},
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "res:ModuleName", "Value": "bastion-host"},
                    {"Key": "res:ModuleId", "Value": "bastion-host"},
                    {"Key": "res:ModuleVersion", "Value": os.environ["version"]},
                    {"Key": "res:NodeType", "Value": NODE_TYPE_APP},
                    {
                        "Key": "res:BackupPlan",
                        "Value": f'{os.environ["environment_name"]}-cluster',
                    },
                    {
                        "Key": "Name",
                        "Value": f'{os.environ["environment_name"]}-bastion-host',
                    },
                    {
                        "Key": "res:EnvironmentName",
                        "Value": f'{os.environ["environment_name"]}',
                    },
                ],
            },
        ],
        DisableApiTermination=bastion_host_config.get(
            "enable_termination_protection", False
        ),
    )

    instance_id = instance["Instances"][0]["InstanceId"]

    # Enable detailed monitoring if required
    if bastion_host_config.get("enable_detailed_monitoring", False):
        ec2.monitor_instances(InstanceIds=[instance_id])

    # Describe the instance to get all details, including public IP
    max_retries = 10
    retry_delay = 2
    instance_details = None

    for attempt in range(max_retries):
        try:
            describe_response = ec2.describe_instances(InstanceIds=[instance_id])
            instance_details = describe_response["Reservations"][0]["Instances"][0]
            break
        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                print(
                    f"Instance not found, retrying... (Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(retry_delay)
            else:
                raise  # Re-raise the exception if it's not the "not found" error

    if instance_details is None:
        raise Exception(
            f"Failed to retrieve instance details after {max_retries} attempts"
        )

    # Record instance details in DDB table
    new_bastion_host_details = {
        "instance_id": instance_id,
        "private_ip": str(instance_details["PrivateIpAddress"]),
        "private_dns_name": str(instance_details["PrivateDnsName"]),
        "hostname": f'bastion-host.{os.environ["environment_name"]}.{os.environ["aws_region"]}.local',
    }

    if bastion_host_config.get("is_public", False):
        # Wait for the public IP to be assigned (it might take a few seconds)
        for _ in range(max_retries):
            if "PublicIpAddress" in instance_details:
                new_bastion_host_details["public_ip"] = str(
                    instance_details["PublicIpAddress"]
                )
                break
            time.sleep(retry_delay)  # Wait for 2 seconds before checking again
            describe_response = ec2.describe_instances(InstanceIds=[instance_id])
            instance_details = describe_response["Reservations"][0]["Instances"][0]
        else:
            print("Warning: Public IP was not assigned within the expected time.")

    _modify_bastion_host_details_in_ddb(new_bastion_host_details)
    return new_bastion_host_details


def _create_route53_record_set(bastion_host_details: Dict[str, str]) -> None:
    """
    Create a Route 53 A record for the bastion host in a private hosted zone.

    :param config: A dictionary containing configuration values
    :param instance_private_ip: The private IP address of the EC2 instance
    """
    route53 = boto3.client("route53")

    hostname = bastion_host_details.get("hostname")
    instance_private_ip = bastion_host_details.get("private_ip")
    private_hosted_zone_id = cluster_settings.get_setting(
        key=CLUSTER_ROUTE53_PRIVATE_HOSTED_ZONE_ID
    )
    private_hosted_zone_name = cluster_settings.get_setting(
        key=CLUSTER_ROUTE53_PRIVATE_HOSTED_ZONE_NAME
    )

    # Ensure all required parameters are present
    if not all(
        [
            hostname,
            private_hosted_zone_id,
            private_hosted_zone_name,
            instance_private_ip,
        ]
    ):
        raise ValueError("Missing required parameters for Route 53 record creation")

    try:
        response = route53.change_resource_record_sets(
            HostedZoneId=private_hosted_zone_id,
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": f"{hostname}.{private_hosted_zone_name}",
                            "Type": "A",
                            "TTL": 300,
                            "ResourceRecords": [{"Value": instance_private_ip}],
                        },
                    }
                ]
            },
        )

        print(
            f"Successfully created/updated Route 53 record: {response['ChangeInfo']['Id']}"
        )

    except Exception as e:
        print(f"Error creating Route 53 record: {str(e)}")
        raise e


def _get_bastion_host_details_from_ddb() -> Dict[str, str]:
    keys = [
        BASTION_HOST_INSTANCE_ID,
        BASTION_HOST_PRIVATE_IP,
        BASTION_HOST_PUBLIC_IP,
        BASTION_HOST_PRIVATE_DNS_NAME,
    ]

    batch_results = table_utils.batch_get_items(
        table_name=CLUSTER_SETTINGS_TABLE_NAME, keys=[{"key": key} for key in keys]
    )

    # Create a dictionary to map keys to their corresponding values
    result_dict = {item["key"]: str(item["value"]) for item in batch_results if item}

    return {
        "instance_id": result_dict.get(BASTION_HOST_INSTANCE_ID, ""),
        "private_ip": result_dict.get(BASTION_HOST_PRIVATE_IP, ""),
        "public_ip": result_dict.get(BASTION_HOST_PUBLIC_IP, ""),
        "private_dns_name": result_dict.get(BASTION_HOST_PRIVATE_DNS_NAME, ""),
    }


def _get_bastion_host_config_from_ddb() -> Dict[str, Any]:
    # These values are placed in DDB during installation and will always be expected to exist.
    keys = [
        BASTION_HOST_INSTANCE_AMI,
        BASTION_HOST_INSTANCE_TYPE,
        CLUSTER_KEYPAIR_NAME,
        BASTION_HOST_SECURITY_GROUP_ID,
        PUBLIC_SUBNETS,
        BASTION_HOST_VOLUME_SIZE,
        BASTION_HOST_KMS_KEY_ID,
        BASTION_HOST_REQUIRE_IMDSV2,
        BASTION_HOST_ENABLE_DETAILED_MONITORING,
        BASTION_HOST_ENABLE_TERMINATION_PROTECTION,
        BASTION_HOST_INSTANCE_PROFILE_NAME,
        BASTION_HOST_USER_DATA,
        BASTION_HOST_IS_PUBLIC,
    ]

    batch_results = table_utils.batch_get_items(
        table_name=CLUSTER_SETTINGS_TABLE_NAME, keys=[{"key": key} for key in keys]
    )

    # Create a dictionary to map keys to their corresponding values
    result_dict = {item["key"]: item["value"] for item in batch_results}

    config = {
        "instance_ami": result_dict[BASTION_HOST_INSTANCE_AMI],
        "instance_type": result_dict[BASTION_HOST_INSTANCE_TYPE],
        "key_pair": result_dict[CLUSTER_KEYPAIR_NAME],
        "security_group_id": result_dict[BASTION_HOST_SECURITY_GROUP_ID],
        "subnet_id": result_dict[PUBLIC_SUBNETS][0],
        "volume_size": int(result_dict.get(BASTION_HOST_VOLUME_SIZE, 200)),
        "kms_key_id": result_dict.get(BASTION_HOST_KMS_KEY_ID),
        "require_imdsv2": result_dict.get(BASTION_HOST_REQUIRE_IMDSV2, "")
        == "required",
        "enable_detailed_monitoring": result_dict.get(
            BASTION_HOST_ENABLE_DETAILED_MONITORING
        ),
        "enable_termination_protection": result_dict.get(
            BASTION_HOST_ENABLE_TERMINATION_PROTECTION
        ),
        "instance_profile": result_dict.get(BASTION_HOST_INSTANCE_PROFILE_NAME),
        "user_data": base64.b64decode(result_dict.get(BASTION_HOST_USER_DATA, "")),
        "is_public": result_dict.get(BASTION_HOST_IS_PUBLIC, "") == "true",
    }

    return config


def _modify_bastion_host_details_in_ddb(
    new_bastion_host_details: Dict[str, str]
) -> None:
    details_to_update = [
        (BASTION_HOST_INSTANCE_ID, "instance_id"),
        (BASTION_HOST_PRIVATE_IP, "private_ip"),
        (BASTION_HOST_PUBLIC_IP, "public_ip"),
        (BASTION_HOST_PRIVATE_DNS_NAME, "private_dns_name"),
        (BASTION_HOST_HOSTNAME, "hostname"),
    ]

    for ddb_key, detail_key in details_to_update:
        table_utils.create_item(
            table_name=CLUSTER_SETTINGS_TABLE_NAME,
            item={
                "key": ddb_key,
                "value": new_bastion_host_details.get(detail_key),
            },
        )
