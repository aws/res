#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import logging
from typing import Any, Dict

from res.clients.ad_sync.ad_sync_client import start_ad_sync  # type: ignore
from res.exceptions import ADSyncConfigurationNotFound, ADSyncInProcess  # type: ignore

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], _: Any) -> None:
    try:
        detail_type = event["detail-type"]
        if detail_type != "Scheduled Event":
            raise Exception(
                "only EventBridge Scheduled Event is supported for the lambda"
            )
        start_ad_sync()

    except (ADSyncConfigurationNotFound, ADSyncInProcess) as e:
        logger.warning(e)
    except Exception as e:
        logger.exception(f"Error in handling scheduled AD Sync event, error: {e}")
        raise e
