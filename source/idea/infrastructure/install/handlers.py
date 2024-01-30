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


class EnvKeys:
    SFN_ARN = "SFN_ARN"
    CALLBACK_URL = "CALLBACK_URL"
    ERROR = "ERROR"
    RESULT = "RESULT"


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
