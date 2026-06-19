#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from typing import Any, Dict
from xml.sax.saxutils import escape as xml_escape

from res.app.asgi_app import RESAsyncApp  # type: ignore
from res.app.middleware.form_to_json_xml_response_middleware import FormToJsonXmlResponseMiddleware  # type: ignore
from res.app.serverless_asgi import lambda_handler  # type: ignore
from res.utils import api_utils  # type: ignore

from connexion.middleware import MiddlewarePosition  # type: ignore

asgi_handler = None


def _dcv_auth_xml_formatter(data: Dict[str, str]) -> str:
    """Format a JSON auth response as DCV external auth XML."""
    result = data.get("result", "no")
    if result == "yes":
        return f'<auth result="yes"><username>{xml_escape(data.get("username") or "")}</username></auth>'
    message = data.get("message") or "Authentication failed"
    return f'<auth result="no"><message>{xml_escape(message)}</message></auth>'


_DCV_EXTERNAL_AUTH_ROUTE = (
    "POST",
    "/externalAuth/{resSessionId}",
    {
        "sessionId": "session_id",
        "authenticationToken": "authentication_token",
        "clientAddress": "client_address",
    },
    _dcv_auth_xml_formatter,
)


def handle_dcv_session_management_event(event: Dict[str, Any], context: Any) -> Any:
    try:
        global asgi_handler  # pylint: disable=global-statement
        if not asgi_handler:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            asgi_app = RESAsyncApp(
                import_name=__name__,
                specification_dir="api/openapi/",
                openapi_filename="DCVSessionManagement.openapi.yaml",
                api_title="DCV Session Management",
            )
            asgi_app.add_middleware(
                FormToJsonXmlResponseMiddleware,
                position=MiddlewarePosition.BEFORE_EXCEPTION,
                routes=[_DCV_EXTERNAL_AUTH_ROUTE],
            )
            asgi_handler = lambda_handler(asgi_app)

        os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_REGION", "us-east-1")
        return asgi_handler(event, context)
    except Exception as e:
        return api_utils._create_api_response(
            status_code=500,
            status_description="Service Error",
            body={"error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    app = RESAsyncApp(
        import_name=__name__,
        specification_dir="api/openapi/",
        openapi_filename="DCVSessionManagement.openapi.yaml",
        api_title="DCV Session Management",
        swagger_ui=True,
        validate_responses=True,
    )
    app.add_middleware(
        FormToJsonXmlResponseMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        routes=[_DCV_EXTERNAL_AUTH_ROUTE],
    )
    uvicorn.run(app, host="0.0.0.0", port=8080)
