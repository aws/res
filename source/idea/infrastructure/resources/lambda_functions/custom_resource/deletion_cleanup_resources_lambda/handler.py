#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
import time
from typing import Any, Dict, List, Tuple

import boto3
from res.constants import (  # type: ignore
    ENVIRONMENT_NAME_KEY,
    ENVIRONMENT_NAME_TAG_KEY,
    INSTANCE_NODE_TYPE_TAG_KEY,
)
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

INFRA_HOST_NODE_TYPE = ["infra", "app"]
SECURITY_GROUP_IDS = "SECURITY_GROUP_IDS"
CLUSTER_NAME = os.environ.get(ENVIRONMENT_NAME_KEY, "")


def clean_up_ec2_instance_handler(
    event: Dict[str, Any], context: Dict[str, Any]
) -> None:
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
    )
    try:
        if event["RequestType"] == "Create" or event["RequestType"] == "Update":
            _, security_groups = _get_lambdas_and_security_groups_to_detach()
            response["Data"] = {
                SECURITY_GROUP_IDS: ",".join(security_groups),
            }
        elif event["RequestType"] == "Delete":
            _terminate_ec2_instances()
            logger.info(
                "Finished terminating ec2 instances during environment deletion."
            )
    except Exception as e:
        response["Status"] = "FAILED"
        error_msg = f"Failed to terminate ec2 instances: {str(e)}"
        response["Reason"] = error_msg
        logger.error(error_msg)
    finally:
        send_response(url=event["ResponseURL"], response=response)


def disable_cognito_protection_handler(
    event: Dict[str, Any], context: Dict[str, Any]
) -> None:
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
    )
    try:
        if event["RequestType"] == "Delete":
            _remove_cognito_userpool_protection()
            logger.info(
                "Finished disabling cognito protection during environment deletion."
            )
    except Exception as e:
        response["Status"] = "FAILED"
        error_msg = f"Failed to disable cognito protection: {str(e)}"
        response["Reason"] = error_msg
        logger.error(error_msg)
    finally:
        send_response(url=event["ResponseURL"], response=response)


def detach_vpc_from_lambdas_handler(
    event: Dict[str, Any], context: Dict[str, Any]
) -> None:
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
    )
    try:
        if event["RequestType"] == "Delete":
            security_groups = os.environ.get(SECURITY_GROUP_IDS, "").split(",")
            lambdas_to_detach, _ = _get_lambdas_and_security_groups_to_detach()

            if lambdas_to_detach:
                _detach_vpc_from_lambda_functions(lambdas_to_detach)

            wait_for_deletion = True
            while wait_for_deletion:
                network_interfaces = _get_network_interface_id(security_groups)
                logger.info(f"Existing network interfaces: {network_interfaces}")
                if network_interfaces:
                    logger.info(
                        "Waiting for lambda network interfaces to be deleted..."
                    )
                    time.sleep(60)
                else:
                    logger.info("All lambda network interfaces are deleted.")
                    wait_for_deletion = False
    except Exception as e:
        response["Status"] = "FAILED"
        error_msg = f"Failed to detach VPC from lambda and wait for network interface deletion: {str(e)}"
        response["Reason"] = error_msg
        logger.error(error_msg)
    finally:
        send_response(url=event["ResponseURL"], response=response)


def _find_ec2_instances() -> Tuple[List[str], List[str]]:
    ec2_client = boto3.client("ec2")
    ec2_instances_to_delete = []
    termination_protected_instances = []
    try:
        paginator = ec2_client.get_paginator("describe_instances")
        for page in paginator.paginate(
            Filters=[
                {
                    "Name": f"tag:{ENVIRONMENT_NAME_TAG_KEY}",
                    "Values": [CLUSTER_NAME],
                }
            ]
        ):
            for reservation in page.get("Reservations", []):
                if "Instances" not in reservation:
                    continue
                for instance in reservation.get("Instances", []):
                    instance_state = instance.get("State", {}).get("Name", "")
                    instance_id = instance.get("InstanceId", "")
                    if instance_state == "terminated":
                        continue

                    # check termination protection instances
                    describe_instance_attribute_result = (
                        ec2_client.describe_instance_attribute(
                            InstanceId=instance_id,
                            Attribute="disableApiTermination",
                        )
                    )
                    disable_api_termination_enabled = (
                        describe_instance_attribute_result["DisableApiTermination"][
                            "Value"
                        ]
                    )
                    if disable_api_termination_enabled:
                        termination_protected_instances.append(instance_id)
                    time.sleep(
                        0.1
                    )  # 10 tps - might need to be adjusted in-future. allowed 100 TPS - https://docs.aws.amazon.com/AWSEC2/latest/APIReference/throttling.html

                    instance_tags = instance.get("Tags", [])
                    host_node = True
                    for tag in instance_tags:
                        if (
                            tag["Key"] == INSTANCE_NODE_TYPE_TAG_KEY
                            and tag["Value"] in INFRA_HOST_NODE_TYPE
                        ):
                            host_node = False
                    if not host_node:
                        continue

                    logger.info(f"Found instance to be terminated: {instance_id}")
                    ec2_instances_to_delete.append(instance_id)
    except Exception as e:
        error_msg = f"Error when finding EC2 instances: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    return termination_protected_instances, ec2_instances_to_delete


def _terminate_ec2_instances() -> None:
    logger.info("Start terminating ec2 instances")

    ec2_client = boto3.client("ec2")
    termination_protected_instances, ec2_instances_to_delete = _find_ec2_instances()

    try:
        if termination_protected_instances:
            for instance_id in termination_protected_instances:
                logger.info(
                    f"Disabling terminate protection for EC2 instance: {instance_id}"
                )
                ec2_client.modify_instance_attribute(
                    InstanceId=instance_id,
                    DisableApiTermination={"Value": False},
                )
                logger.info(
                    f"Termination protection disabled for EC2 instance: {instance_id}"
                )
                time.sleep(0.1)

        if ec2_instances_to_delete:
            for i in range(0, len(ec2_instances_to_delete), 100):
                batch_ids = ec2_instances_to_delete[i : i + 100]
                logger.info(f"Terminating following instances in batch: {batch_ids}")
                ec2_client.terminate_instances(InstanceIds=batch_ids)

        logger.info("Finished terminating all EC2 instances.")
    except Exception as e:
        error_msg = f"Error when terminating EC2 instances: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def _get_lambdas_and_security_groups_to_detach() -> Tuple[List[str], List[str]]:
    logger.info("Start getting lambdas arns to detach.")

    lambda_client = boto3.client("lambda")
    lambdas_to_detach = []
    security_group_list = []
    try:
        paginator = lambda_client.get_paginator("list_functions")
        for page in paginator.paginate():
            for function in page.get("Functions", []):

                # Check if the function has VPC configuration and is created by current RES environment
                if "VpcConfig" in function:
                    vpc_config = function.get("VpcConfig", {})
                    subnets = vpc_config.get("SubnetIds", [])
                    security_groups = vpc_config.get("SecurityGroupIds", [])

                    if not subnets and not security_groups:
                        continue

                    function_arn = function.get("FunctionArn", "")
                    function_tags = lambda_client.list_tags(Resource=function_arn).get(
                        "Tags", {}
                    )
                    if function_tags.get(ENVIRONMENT_NAME_TAG_KEY, "") == CLUSTER_NAME:
                        logger.info(
                            f"Found lambda with vpc configuration: {function_arn}"
                        )
                        security_group_list.extend(security_groups)
                        lambdas_to_detach.append(function_arn)

        logger.info("Finished getting lambdas to detach.")

    except Exception as e:
        error_msg = f"Error when getting lambdas to detach: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    return lambdas_to_detach, security_group_list


def _detach_vpc_from_lambda_functions(lambdas_to_detach: List[str]) -> None:

    lambda_client = boto3.client("lambda")
    try:

        for function_arn in lambdas_to_detach:
            lambda_client.update_function_configuration(
                FunctionName=function_arn,
                VpcConfig={
                    "SubnetIds": [],
                    "SecurityGroupIds": [],
                },
            )
            logger.info(f"VPC configuration removed from function: {function_arn}")
        logger.info("Finished detaching VPC configurations from all lambdas.")
    except Exception as e:
        error_msg = f"Error when detaching vpc from lambda functions: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def _get_network_interface_id(security_groups: List[str]) -> List[str]:
    logger.info("Getting network interfaces to check deletion.")

    ec2_client = boto3.client("ec2")

    try:

        paginator = ec2_client.get_paginator("describe_network_interfaces")
        network_interface_list = []
        for page in paginator.paginate(
            Filters=[
                {
                    "Name": "group-id",
                    "Values": security_groups,
                },
                {
                    "Name": "interface-type",
                    "Values": ["lambda"],
                },
            ]
        ):
            for network_interface in page.get("NetworkInterfaces", []):
                network_interface_list.append(
                    network_interface.get("NetworkInterfaceId", "")
                )

    except Exception as e:
        error_msg = f"Error when getting network interfaces to check deletion: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    return network_interface_list


def _remove_cognito_userpool_protection() -> None:
    logger.info("Start unprotecting cognito user pool")
    cognito_client = boto3.client("cognito-idp")
    userpool_id = os.environ.get("cognito_user_pool_id", "")

    if not userpool_id:
        return

    try:
        cognito_client.update_user_pool(
            UserPoolId=userpool_id, DeletionProtection="INACTIVE"
        )
        logger.info(f"Removed deletion protection for cognito userpool: {userpool_id}")

    except Exception as e:
        error_msg = f"Error when removing cognito userpool protection: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)
