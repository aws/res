#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Dict, Optional

import res.exceptions as exceptions  # type: ignore
from res.clients.ad_sync import ad_sync_client  # type: ignore
from res.constants import (  # type: ignore
    AD_SYNC_STATUS_SUBMISSION_TIME_KEY,
    AD_SYNC_STATUS_TTL_KEY,
    AD_SYNC_STATUS_UPDATE_TIME_KEY,
)
from res.utils import api_utils  # type: ignore

from .common import check_admin_authorized


def handle_ad_sync_event(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        check_admin_authorized(event)

        http_method = event.get("httpMethod", "")
        body = json.loads(event.get("body") or "{}")
        if http_method == "GET":
            parameters = event.get("queryStringParameters", {})
            task_id = parameters.get("id", "")
            return api_utils._create_api_response(  # type: ignore
                status_code=200,
                status_description="Retrieved AD Sync status",
                body=_get_ad_sync_status_from_ddb(task_id),
            )
        elif http_method == "PUT":
            try:
                id = ad_sync_client.start_ad_sync()
            except (
                exceptions.ADSyncInProcess,
                exceptions.ADSyncConfigurationNotFound,
            ) as e:
                return api_utils._create_api_response(  # type: ignore
                    status_code=400,
                    status_description="Client Error",
                    body={"error": str(e)},
                )
            return api_utils._create_api_response(  # type: ignore
                status_code=200,
                status_description="Started AD Sync",
                body={"id": id},
            )
        elif http_method == "DELETE":
            _task_id = ad_sync_client.stop_ad_sync(body.get("id"))

            return api_utils._create_api_response(  # type: ignore
                status_code=200,
                status_description="Stopped AD Sync",
            )
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


def _get_ad_sync_status_from_ddb(task_id: Optional[str] = None) -> Dict[str, Any]:
    ad_sync_status: Optional[Dict[str, Any]] = ad_sync_client.get_ad_sync_status(
        task_id
    )
    if not ad_sync_status:
        return {}

    ad_sync_status[AD_SYNC_STATUS_SUBMISSION_TIME_KEY] = str(
        ad_sync_status.get(AD_SYNC_STATUS_SUBMISSION_TIME_KEY, "")
    )
    ad_sync_status[AD_SYNC_STATUS_UPDATE_TIME_KEY] = str(
        ad_sync_status.get(AD_SYNC_STATUS_UPDATE_TIME_KEY, "")
    )
    ad_sync_status[AD_SYNC_STATUS_TTL_KEY] = str(
        ad_sync_status.get(AD_SYNC_STATUS_TTL_KEY, "")
    )

    return ad_sync_status
