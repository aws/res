#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from typing import Any, Dict

import res.exceptions as exceptions  # type: ignore
from res.app.asgi_app import RESAsyncApp  # type: ignore
from res.app.serverless_asgi import lambda_handler  # type: ignore
from res.utils import api_utils  # type: ignore

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resources.ad_sync import handle_ad_sync_event  # type: ignore
from resources.bastion_host_service import handle_bastion_host_lifecycle  # type: ignore

asgi_handler = None


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
                asgi_app = RESAsyncApp(
                    import_name=__name__,
                    specification_dir="api/openapi/",
                    openapi_filename="RES.openapi.yaml",
                    api_title="RES API",
                )
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


if __name__ == "__main__":
    import uvicorn
    app = RESAsyncApp(
        import_name=__name__,
        specification_dir="api/openapi/",
        openapi_filename="RES.openapi.yaml",
        api_title="RES API",
        swagger_ui=True,
        validate_responses=True,
    )
    uvicorn.run(app, host="0.0.0.0", port=8080)
