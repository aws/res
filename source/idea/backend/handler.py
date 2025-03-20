#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

import res.exceptions as exceptions  # type: ignore
from res.utils import api_utils  # type: ignore
from resources.ad_sync import handle_ad_sync_event
from resources.bastion_host_service import handle_bastion_host_lifecycle


def handle_backend_event(event: Dict[str, Any], _: Any) -> Any:
    try:
        path = event.get("path", "")

        if path == "/res/config":
            # This API can be used in the future to handle multi-configuration updates
            # For now, it only handles bastion host lifecycle
            return handle_bastion_host_lifecycle(event)
        elif path == "/res/ad-sync":
            return handle_ad_sync_event(event)

        # If the path or method is not recognized, return a bad request exception
        return api_utils._create_api_response(  # type: ignore
            status_code=400,
            status_description="bad request",
            body={"error": str(e)},
        )
    except Exception as e:
        return api_utils._create_api_response(  # type: ignore
            status_code=500,
            status_description="Service Error",
            body={"error": str(e)},
        )
