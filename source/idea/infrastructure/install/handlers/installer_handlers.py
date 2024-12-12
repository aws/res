#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from enum import Enum
from typing import Any, Dict, TypedDict, Union

import boto3
import botocore.exceptions

TAG_NAME = "res:EnvironmentName"
BASTION_HOST_INSTANCE_ID = "bastion-host.instance_id"
BASTION_HOST_HOSTNAME = "bastion-host.hostname"
BASTION_HOST_HOSTED_ZONE_ID = "cluster.route53.private_hosted_zone_id"
BASTION_HOST_HOSTED_ZONE_NAME = "cluster.route53.private_hosted_zone_name"


class EnvKeys(str, Enum):
    SFN_ARN = "SFN_ARN"
    CALLBACK_URL = "CALLBACK_URL"
    ERROR = "ERROR"
    RESULT = "RESULT"
    ENVIRONMENT_NAME = "ENVIRONMENT_NAME"
    INSTALLER_ECR_REPO_NAME = "INSTALLER_ECR_REPO_NAME"


class RequestType(str, Enum):
    CREATE = "Create"
    UPDATE = "Update"
    DELETE = "Delete"


class CustomResourceResponse(TypedDict):
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
    Status: str
    Reason: str
    PhysicalResourceId: str
    StackId: str
    RequestId: str
    LogicalResourceId: str


class CustomResourceResponseStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class WaitConditionResponse(TypedDict):
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-waitcondition.html
    Status: str
    Reason: str
    UniqueId: str
    Data: str


class WaitConditionResponseStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


def unprotect_cognito_user_pool(event: Dict[str, Any], _: Any) -> None:
    cognito_client = boto3.client("cognito-idp")

    describe_user_pool_paginator = cognito_client.get_paginator("list_user_pools")
    user_pool_iter = describe_user_pool_paginator.paginate(MaxResults=50)

    env_name = event["ResourceProperties"][EnvKeys.ENVIRONMENT_NAME]

    # Walk the list of user pools in the account looking for our matching pool
    # The pool must match the expected name, as well as having the proper
    # res:EnvironmentName tag for us to consider it as valid.
    for page in user_pool_iter:
        user_pools = page.get("UserPools", [])
        for pool in user_pools:
            pool_name = pool.get("Name", "")
            pool_id = pool.get("Id", None)
            if pool_name != f"{env_name}-user-pool" or not pool_id:
                continue
            print(f"Processing cognito pool: {pool_name}")
            describe_user_pool_result = cognito_client.describe_user_pool(
                UserPoolId=pool_id
            )
            pool_tags = describe_user_pool_result.get("UserPool", {}).get(
                "UserPoolTags", {}
            )
            pool_deletion_protection = describe_user_pool_result.get(
                "UserPool", {}
            ).get("DeletionProtection", "ACTIVE")
            for tag_name, tag_value in pool_tags.items():
                if (
                    tag_name == TAG_NAME
                    and tag_value == env_name
                    and pool_deletion_protection == "ACTIVE"
                ):
                    print("Removing active status for user pool")
                    cognito_client.update_user_pool(
                        UserPoolId=pool_id, DeletionProtection="INACTIVE"
                    )


def handle_custom_resource_lifecycle_event(event: Dict[str, Any], _: Any) -> None:
    sfn_arn = os.getenv(EnvKeys.SFN_ARN)
    client = boto3.client("stepfunctions")

    response = CustomResourceResponse(
        Status=CustomResourceResponseStatus.SUCCESS,
        Reason=CustomResourceResponseStatus.SUCCESS,
        PhysicalResourceId=event["LogicalResourceId"],
        StackId=event["StackId"],
        RequestId=event["RequestId"],
        LogicalResourceId=event["LogicalResourceId"],
    )
    try:
        client.start_execution(stateMachineArn=sfn_arn, input=json.dumps(event))
    except botocore.exceptions.ClientError as e:
        response["Status"] = CustomResourceResponseStatus.FAILED
        response["Reason"] = str(e)
        send_response(url=event["ResponseURL"], response=response)
        return

    if event.get("RequestType") != RequestType.DELETE:
        # Delete events don't use the wait condition, so send the response later
        send_response(url=event["ResponseURL"], response=response)


def send_wait_condition_response(event: Dict[str, Any], _: Any) -> Any:
    is_wait_condition_response = event.get("RequestType") != RequestType.DELETE

    response: Union[WaitConditionResponse, CustomResourceResponse] = (
        WaitConditionResponse(
            Status=WaitConditionResponseStatus.SUCCESS,
            UniqueId=str(uuid.uuid4()),
            Reason=WaitConditionResponseStatus.SUCCESS,
            Data="",
        )
    )
    if not is_wait_condition_response:
        response = CustomResourceResponse(
            Status=CustomResourceResponseStatus.SUCCESS,
            Reason=CustomResourceResponseStatus.SUCCESS,
            PhysicalResourceId=event["LogicalResourceId"],
            StackId=event["StackId"],
            RequestId=event["RequestId"],
            LogicalResourceId=event["LogicalResourceId"],
        )

    if EnvKeys.ERROR in event:
        response["Status"] = (
            WaitConditionResponseStatus.FAILURE
            if is_wait_condition_response
            else CustomResourceResponseStatus.FAILED
        )
        response["Reason"] = json.dumps(event[EnvKeys.ERROR])

    url = (
        event["ResourceProperties"][EnvKeys.CALLBACK_URL]
        if is_wait_condition_response
        else event["ResponseURL"]
    )

    send_response(url, response)


def send_response(
    url: str,
    response: Union[CustomResourceResponse, WaitConditionResponse],
) -> None:
    request = urllib.request.Request(
        method="PUT",
        url=url,
        data=json.dumps(response).encode("utf-8"),
    )
    urllib.request.urlopen(request)


def handle_security_group_delete(event: Dict[str, Any], _: Any) -> None:
    cr_response = CustomResourceResponse(
        Status=CustomResourceResponseStatus.SUCCESS,
        Reason=CustomResourceResponseStatus.SUCCESS,
        PhysicalResourceId=event["LogicalResourceId"],
        StackId=event["StackId"],
        RequestId=event["RequestId"],
        LogicalResourceId=event["LogicalResourceId"],
    )
    try:
        if event["RequestType"] == "Delete":
            print("received event for deletion")
            properties = event.get("ResourceProperties", {})
            vpc_id = properties.get("vpc_id")
            security_group_names = json.loads(properties.get("security_group_name"))

            ec2 = boto3.client("ec2")
            # First, we need to find the security group ID
            response = ec2.describe_security_groups(
                Filters=[
                    {"Name": "vpc-id", "Values": [vpc_id]},
                    {"Name": "group-name", "Values": security_group_names},
                ]
            )

            if not response["SecurityGroups"]:
                print(
                    f"No security group found with name '{security_group_names}' in VPC '{vpc_id}'"
                )
                send_response(event["ResponseURL"], cr_response)
                return

            for security_group in response["SecurityGroups"]:
                security_group_id = security_group["GroupId"]

                # Delete hanging ENIs
                network_interfaces = ec2.describe_network_interfaces(
                    Filters=[{"Name": "group-id", "Values": [security_group_id]}]
                )["NetworkInterfaces"]

                for eni in network_interfaces:
                    ec2.delete_network_interface(
                        NetworkInterfaceId=eni["NetworkInterfaceId"]
                    )

                print(
                    f"Successfully deleted all ENIs associated with security group (ID: {security_group_id})"
                )

                # Now we can delete the security group
                ec2.delete_security_group(GroupId=security_group_id)
                print(
                    f"Successfully deleted security group (ID: {security_group_id}) from VPC '{vpc_id}'"
                )
        send_response(url=event["ResponseURL"], response=cr_response)
    except Exception as e:
        cr_response = CustomResourceResponse(
            Status=CustomResourceResponseStatus.FAILED,
            Reason=str(e),
            PhysicalResourceId=event["LogicalResourceId"],
            StackId=event["StackId"],
            RequestId=event["RequestId"],
            LogicalResourceId=event["LogicalResourceId"],
        )
        print(e)
        send_response(url=event["ResponseURL"], response=cr_response)


def delete_dcv_broker_tables(event: Dict[str, Any], _: Any) -> None:
    print(event)
    request_type = event["RequestType"]
    if request_type == RequestType.DELETE:
        environmentName = event["ResourceProperties"]["environment_name"]
        client = boto3.client("dynamodb")
        dcvBrokerTables = []
        lastEvaluatedTableName = None
        while True:
            if not lastEvaluatedTableName:
                response = client.list_tables()
            else:
                response = client.list_tables(
                    ExclusiveStartTableName=lastEvaluatedTableName
                )
            dcvBrokerTables.extend(
                [
                    table
                    for table in response["TableNames"]
                    if table.startswith(f"{environmentName}.vdc.dcv-broker")
                ]
            )
            lastEvaluatedTableName = response.get("LastEvaluatedTableName", None)
            if not lastEvaluatedTableName:
                break
        print("Tables to be deleted: " + str(dcvBrokerTables))
        for table in dcvBrokerTables:
            client.delete_table(TableName=table)
    return


def handle_bastion_host_delete(event: Dict[str, Any], _: Any) -> None:
    cr_response = CustomResourceResponse(
        Status=CustomResourceResponseStatus.SUCCESS,
        Reason=CustomResourceResponseStatus.SUCCESS,
        PhysicalResourceId=event["LogicalResourceId"],
        StackId=event["StackId"],
        RequestId=event["RequestId"],
        LogicalResourceId=event["LogicalResourceId"],
    )
    properties = event.get("ResourceProperties", {})
    cluster_name = properties.get("cluster_name")
    CLUSTER_SETTINGS_TABLE = f"{cluster_name}.cluster-settings"

    if event["RequestType"] == "Delete":
        print("Received event for bastion host deletion")
        # Get the instance_id from the cluster-settings DynamoDB table
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(CLUSTER_SETTINGS_TABLE)
        response = table.get_item(Key={"key": BASTION_HOST_INSTANCE_ID})

        if "Item" not in response or not response["Item"].get("value"):
            # Nothing to delete
            send_response(url=event["ResponseURL"], response=cr_response)
            return

        instance_id = response["Item"].get("value")

        print(f"Retrieved instance ID {instance_id} from cluster-settings table")

        ec2 = boto3.client("ec2")

        # Terminate EC2 instance
        ec2.terminate_instances(InstanceIds=[instance_id])
        print(f"Successfully terminated EC2 instance (ID: {instance_id})")

        # Wait for the instance to be terminated
        waiter = ec2.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=[instance_id])
        print(f"EC2 instance (ID: {instance_id}) has been fully terminated")

        # Delete Route53 "A" record
        route53 = boto3.client("route53")

        # Retrieve necessary information from DynamoDB

        hostname = (
            table.get_item(Key={"key": BASTION_HOST_HOSTNAME})
            .get("Item", {})
            .get("value", "")
        )
        private_hosted_zone_id = (
            table.get_item(Key={"key": BASTION_HOST_HOSTED_ZONE_ID})
            .get("Item", {})
            .get("value", "")
        )
        private_hosted_zone_name = (
            table.get_item(Key={"key": BASTION_HOST_HOSTED_ZONE_NAME})
            .get("Item", {})
            .get("value", "")
        )

        if not all([hostname, private_hosted_zone_id, private_hosted_zone_name]):
            raise ValueError(
                "Missing required Route53 information in cluster-settings table"
            )

        # Get the current record details
        record_name = f"{hostname}.{private_hosted_zone_name}"
        response = route53.list_resource_record_sets(
            HostedZoneId=private_hosted_zone_id,
            StartRecordName=record_name,
            StartRecordType="A",
            MaxItems="1",
        )

        if response["ResourceRecordSets"]:
            current_record = response["ResourceRecordSets"][0]
            if (
                current_record["Name"].rstrip(".") == record_name.rstrip(".")
                and current_record["Type"] == "A"
            ):

                # Delete the record
                change_batch = {
                    "Changes": [
                        {
                            "Action": "DELETE",
                            "ResourceRecordSet": {
                                "Name": current_record["Name"],
                                "Type": current_record["Type"],
                                "TTL": current_record["TTL"],
                                "ResourceRecords": current_record["ResourceRecords"],
                            },
                        }
                    ]
                }

                route53.change_resource_record_sets(
                    HostedZoneId=private_hosted_zone_id, ChangeBatch=change_batch
                )
        print(
            f"Successfully deleted Route53 'A' record for {hostname}.{private_hosted_zone_name}"
        )
    send_response(url=event["ResponseURL"], response=cr_response)
