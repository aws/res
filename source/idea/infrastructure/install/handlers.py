#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, TypedDict, Union

import boto3
import botocore.exceptions

TAG_NAME = "res:EnvironmentName"


class EnvKeys:
    SFN_ARN = "SFN_ARN"
    CALLBACK_URL = "CALLBACK_URL"
    ERROR = "ERROR"
    RESULT = "RESULT"
    ENVIRONMENT_NAME = "ENVIRONMENT_NAME"
    INSTALLER_ECR_REPO_NAME = "INSTALLER_ECR_REPO_NAME"


class RequestType:
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


class CustomResourceResponseStatus:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class WaitConditionResponse(TypedDict):
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-waitcondition.html
    Status: str
    Reason: str
    UniqueId: str
    Data: str


class WaitConditionResponseStatus:
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


def delete_installer_ecr_images(event: Dict[str, Any], _: Any) -> None:
    installer_ecr_repo_name = event["ResourceProperties"][
        EnvKeys.INSTALLER_ECR_REPO_NAME
    ]
    ecr_client = boto3.client("ecr")
    paginator = ecr_client.get_paginator("list_images")
    page_iterator = paginator.paginate(repositoryName=installer_ecr_repo_name)
    for page in page_iterator:
        ecr_client.batch_delete_image(
            repositoryName=installer_ecr_repo_name, imageIds=page["imageIds"]
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
    url: str, response: Union[CustomResourceResponse, WaitConditionResponse]
) -> None:
    request = urllib.request.Request(
        method="PUT",
        url=url,
        data=json.dumps(response).encode("utf-8"),
    )

    urllib.request.urlopen(request)
