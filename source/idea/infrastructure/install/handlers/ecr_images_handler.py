#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from enum import Enum
from typing import Any, Dict, TypedDict

import boto3

logger = logging.getLogger("ad-sync")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


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


def handle_request(event: Dict[str, Any], _: Any) -> None:
    response = CustomResourceResponse(
        Status=CustomResourceResponseStatus.SUCCESS,
        Reason=CustomResourceResponseStatus.SUCCESS,
        PhysicalResourceId=event["LogicalResourceId"],
        StackId=event["StackId"],
        RequestId=event["RequestId"],
        LogicalResourceId=event["LogicalResourceId"],
    )

    if event["RequestType"] == "Create" or event["RequestType"] == "Update":
        logger.info("Start copying container images to the RES ECR repository")

        client = boto3.client("codebuild")
        build = client.start_build(
            projectName=event["ResourceProperties"]["ProjectName"],
        )
        build_id = build.get("build", {}).get("id")

        while build_id:
            build = client.batch_get_builds(ids=[build_id])
            build_status = build["builds"][0]["buildStatus"]

            if build_status == "SUCCEEDED":
                logger.info(
                    "Copied container images to the RES ECR repository successfully"
                )

                _send_response(url=event["ResponseURL"], response=response)
                return
            elif (
                build_status == "FAILED"
                or build_status == "FAULT"
                or build_status == "STOPPED"
                or build_status == "TIMED_OUT"
            ):
                logger.error(
                    f"Failed to copy container images to the RES ECR repository. Status {build_status}"
                )

                response["Status"] = CustomResourceResponseStatus.FAILED
                _send_response(url=event["ResponseURL"], response=response)
                return

            # Wait for the code build project to complete
            time.sleep(5)

    elif event["RequestType"] == "Delete":
        logger.info("Start deleting container images from the RES ECR repository")

        ecr_client = boto3.client("ecr")
        paginator = ecr_client.get_paginator("list_images")
        page_iterator = paginator.paginate(
            repositoryName=event["ResourceProperties"]["ResEcrRepositoryName"]
        )
        for page in page_iterator:
            ecr_client.batch_delete_image(
                repositoryName=event["ResourceProperties"]["ResEcrRepositoryName"],
                imageIds=page["imageIds"],
            )

        logger.info("Deleted container images from the RES ECR repository successfully")

        _send_response(url=event["ResponseURL"], response=response)


def _send_response(url: str, response: CustomResourceResponse) -> None:
    request = urllib.request.Request(
        method="PUT",
        url=url,
        data=json.dumps(response).encode("utf-8"),
    )

    urllib.request.urlopen(request)
