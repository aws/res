#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from typing import Any, Dict, TypedDict
from urllib.request import Request, urlopen

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LB_SUBNETS = "LOAD_BALANCER_SUBNETS"
INFRA_SUBNETS = "INFRA_SUBNETS"
VDI_SUBNETS = "VDI_SUBNETS"


class CustomResourceResponse(TypedDict):
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
    Status: str
    Reason: str
    PhysicalResourceId: str
    StackId: str
    RequestId: str
    LogicalResourceId: str


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    logger.info(f"Transform params from list to string")
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
    )
    try:
        load_balancer_subnets = os.environ.get(LB_SUBNETS)
        infra_subnets = os.environ.get(INFRA_SUBNETS)
        vdi_subnets = os.environ.get(VDI_SUBNETS)
        if not load_balancer_subnets or not infra_subnets or not vdi_subnets:
            raise Exception("Subnet list empty")
        logger.info(f"Lb subnets {load_balancer_subnets}")
        logger.info(f"Infra subnets {infra_subnets}")
        logger.info(f"VDI subnets {vdi_subnets}")
        response["Data"] = {
            LB_SUBNETS: load_balancer_subnets,
            INFRA_SUBNETS: infra_subnets,
            VDI_SUBNETS: vdi_subnets,
        }
    except Exception as e:
        response["Status"] = "FAILED"
        response["Reason"] = "FAILED"
        logger.error(f"Failed to transform params from list to string: {str(e)}")
    finally:
        _send_response(url=event["ResponseURL"], response=response)


def _send_response(url: str, response: CustomResourceResponse) -> None:
    request = Request(
        method="PUT",
        url=url,
        data=json.dumps(response).encode("utf-8"),
    )

    urlopen(request)
