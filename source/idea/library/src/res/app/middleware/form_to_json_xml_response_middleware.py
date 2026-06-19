#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Awaitable, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class FormToJsonXmlResponseMiddleware(BaseHTTPMiddleware):
    """Middleware that converts form-urlencoded requests to JSON and JSON responses to XML.

    For configured routes, this middleware:
    - Inbound: parses application/x-www-form-urlencoded body, maps field names
      to JSON keys, and rewrites the request as application/json.
    - Outbound: converts the JSON response body to XML using a provided formatter,
      and sets Content-Type to application/xml.

    Args:
        app: The ASGI application.
        routes: List of route configurations, each a tuple of:
            - method: HTTP method (e.g. "POST")
            - path: URL path (e.g. "/")
            - field_mapping: Dict mapping form field names to JSON keys
            - xml_formatter: Callable that takes the JSON response dict and returns an XML string
    """

    def __init__(
        self,
        app,
        routes: Optional[
            List[Tuple[str, str, Dict[str, str], Callable[[dict], str]]]
        ] = None,
    ):
        super().__init__(app)
        self.routes = [
            (method.upper(), path, field_mapping, xml_formatter)
            for method, path, field_mapping, xml_formatter in (routes or [])
        ]

    def _match_route(
        self, method: str, path: str
    ) -> Optional[Tuple[Dict[str, str], Callable[[dict], str]]]:
        for route_method, route_path, field_mapping, xml_formatter in self.routes:
            if route_method != method.upper():
                continue
            if "{" in route_path:
                # Simple prefix match — sufficient for single parameterized route.
                # If multiple parameterized routes share a prefix, use proper path template parsing.
                prefix = route_path.split("{")[0]
                if path.startswith(prefix):
                    return field_mapping, xml_formatter
            elif path == route_path:
                return field_mapping, xml_formatter
        return None

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        config = self._match_route(request.method, request.url.path)
        if not config:
            return await call_next(request)

        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" not in content_type:
            return await call_next(request)

        field_mapping, xml_formatter = config

        # Convert form-urlencoded request to JSON
        body = await request.body()
        form_data = parse_qs(body.decode("utf-8"))
        json_body = json.dumps(
            {
                json_key: form_data.get(form_field, [""])[0]
                for form_field, json_key in field_mapping.items()
            }
        ).encode("utf-8")

        # Replace request with JSON version
        request._body = json_body
        new_headers = [
            (k, v)
            for k, v in request.scope["headers"]
            if k not in (b"content-type", b"content-length")
        ]
        new_headers.append((b"content-type", b"application/json"))
        new_headers.append((b"content-length", str(len(json_body)).encode("latin1")))
        request.scope["headers"] = new_headers

        response = await call_next(request)

        # Only convert successful responses to XML; let error responses pass
        # through unchanged so validation details are preserved.
        if not (200 <= response.status_code < 300):
            return response

        # Convert JSON response to XML
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += (
                chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
            )

        try:
            xml = xml_formatter(json.loads(response_body))
        except (json.JSONDecodeError, AttributeError, KeyError):
            xml = xml_formatter({})

        return Response(
            content=xml,
            status_code=response.status_code,
            headers={
                k: v
                for k, v in response.headers.items()
                if k.lower() not in ("content-type", "content-length")
            },
            media_type="application/xml",
        )
