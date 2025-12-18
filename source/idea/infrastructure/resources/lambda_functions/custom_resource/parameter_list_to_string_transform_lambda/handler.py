#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Dict

from res.constants import OLD_CUSTOM_TAG_KEYS  # type: ignore
from res.resources import cluster_settings  # type: ignore
from res.utils import cluster_settings_utils  # type: ignore
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LB_SUBNETS = "LOAD_BALANCER_SUBNETS"
INFRA_SUBNETS = "INFRA_SUBNETS"
VDI_SUBNETS = "VDI_SUBNETS"


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

        old_custom_tag_keys = ""
        if event["RequestType"] == "Update":
            old_custom_tags_list_dict = (
                cluster_settings_utils.convert_custom_tags_to_dict_list(
                    cluster_settings.get_setting("global-settings.custom_tags")
                )
            )
            if old_custom_tags_list_dict:
                old_custom_tag_keys = ";".join(
                    [tag["Key"] for tag in old_custom_tags_list_dict]
                )

        response["Data"] = {
            LB_SUBNETS: load_balancer_subnets,
            INFRA_SUBNETS: infra_subnets,
            VDI_SUBNETS: vdi_subnets,
            OLD_CUSTOM_TAG_KEYS: old_custom_tag_keys,
        }
    except Exception as e:
        error_message = f"Failed to transform params from list to string: {str(e)}"
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logger.error(error_message)
    finally:
        send_response(url=event["ResponseURL"], response=response)
