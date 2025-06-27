#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import random
import time
from functools import lru_cache
from typing import Any, Dict

from res.resources import cluster_settings
from res.utils import aws_utils, instance_metadata_utils, logging_utils, table_utils

MAX_AD_AUTHORIZATION_ATTEMPTS = 5

logger = logging_utils.get_logger("ad-automation")


@lru_cache
def ad_authorization_nonce():
    return str(random.randint(0, 32767))


@lru_cache
def ad_authorization_instance_id() -> str:
    return instance_metadata_utils.get_instance_id()


def get_authorization() -> Dict[str, Any]:
    try:
        nonce = ad_authorization_nonce()
        authorization = table_utils.get_item(
            "ad-automation",
            {
                "instance_id": ad_authorization_instance_id(),
                "nonce": nonce,
            },
        )
        return authorization
    except Exception as e:
        logger.error(f"Error getting AD authorization: {str(e)}")
        return {}


def request_ad_authorization() -> bool:
    attempt_count = 0

    while attempt_count <= MAX_AD_AUTHORIZATION_ATTEMPTS:
        if _send_authorization_message():
            return True

        sleep_time = random.randint(8, 40)
        logger.error(
            f"({attempt_count} of {MAX_AD_AUTHORIZATION_ATTEMPTS}) failed to request authorization to join AD, retrying in {sleep_time} seconds ..."
        )
        time.sleep(sleep_time)
        attempt_count += 1

    return False


def _send_authorization_message() -> bool:
    logger.info(
        f"Request AD authorization for instance {ad_authorization_instance_id()}"
    )

    try:
        payload = {
            "header": {"namespace": "ADAutomation.PresetComputer"},
            "payload": {
                "nonce": ad_authorization_nonce(),
                "instance_id": ad_authorization_instance_id(),
                "hostname": os.environ.get("COMPUTERNAME", ""),
            },
        }

        aws_utils.sqs_send_message(
            payload,
            cluster_settings.get_setting(
                "directoryservice.ad_automation.sqs_queue_url"
            ),
            ad_authorization_instance_id(),
            f"ADAutomation.PresetComputer.{ad_authorization_instance_id()}.{ad_authorization_nonce()}",
        )

        return True
    except Exception as e:
        assert False, f"Error sending AD authorization message: {str(e)}"
        return False
