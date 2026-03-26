#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from typing import Any, Dict

import res.exceptions as exceptions  # type: ignore
from res.utils import api_utils  # type: ignore

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resources.ad_sync import handle_ad_sync_event  # type: ignore
from resources.bastion_host_service import handle_bastion_host_lifecycle  # type: ignore
from async_connexion_app import create_async_app  # type: ignore
from serverless_asgi import lambda_handler  # type: ignore

asgi_handler = None


def _init_asgi_app() -> Any:
    """
    Initialize native ASGI app using connexion.AsyncApp.
    """
    async_app = create_async_app()
    return async_app


def handle_backend_event(event: Dict[str, Any], context: Any) -> Any:
    try:
        path = event.get("path", "")

        if path == "/res/config":
            return handle_bastion_host_lifecycle(event)
        elif path == "/res/ad-sync":
            return handle_ad_sync_event(event)
        else:
            global asgi_handler  # pylint: disable=global-statement,invalid-name
            if not asgi_handler:
                asgi_app = _init_asgi_app()
                asgi_handler = lambda_handler(asgi_app)

            os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_REGION", "us-east-1")
            return asgi_handler(event, context)
    except exceptions.UnauthorizedAccess:
        return api_utils._create_api_response(
            status_code=401,
            status_description="401 Unauthorized",
            body={"error": "Unauthorized access"},
        )
    except Exception as e:
        return api_utils._create_api_response(
            status_code=500,
            status_description="Service Error",
            body={"error": str(e)},
        )
