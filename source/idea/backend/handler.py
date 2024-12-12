#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

import res.exceptions as exceptions  # type: ignore
from bastion_host_service import handle_bastion_host_lifecycle


def handle_backend_event(event: Dict[str, Any], _: Any) -> Any:
    path = event.get("path", "")

    if path == "/res/config":
        # This API can be used in the future to handle multi-configuration updates
        # For now, it only handles bastion host lifecycle
        return handle_bastion_host_lifecycle(event)

    # If the path or method is not recognized, return a bad request exception
    return exceptions.BadRequest()
