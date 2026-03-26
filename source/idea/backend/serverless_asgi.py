#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# ASGI equivalent of serverless_wsgi.py
# Adapted from https://github.com/logandk/serverless-wsgi/blob/master/serverless_wsgi.py
# Copyright (c) 2016 Logan Raarup
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

import asyncio
import base64
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union
from urllib.parse import unquote, unquote_plus, urlencode

# List of MIME types that should not be base64 encoded. MIME types within `text/*`
# are included by default.
TEXT_MIME_TYPES = [
    "application/json",
    "application/javascript",
    "application/xml",
    "application/vnd.api+json",
    "image/svg+xml",
]

# HTTP status codes mapping
HTTP_STATUS_CODES = {
    100: "Continue",
    101: "Switching Protocols",
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    304: "Not Modified",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    410: "Gone",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def all_casings(input_string: str) -> Generator[str, None, None]:
    """
    Permute all casings of a given string.
    A pretty algoritm, via @Amber
    http://stackoverflow.com/questions/6792803/finding-all-possible-case-permutations-in-python
    """
    if not input_string:
        yield ""
    else:
        first = input_string[:1]
        if first.lower() == first.upper():
            for sub_casing in all_casings(input_string[1:]):
                yield first + sub_casing
        else:
            for sub_casing in all_casings(input_string[1:]):
                yield first.lower() + sub_casing
                yield first.upper() + sub_casing


def split_headers(headers: Dict[str, List[str]]) -> Dict[str, str]:
    """
    If there are multiple occurrences of headers, create case-mutated variations
    in order to pass them through APIGW. This is a hack that's currently
    needed. See: https://github.com/logandk/serverless-wsgi/issues/11
    Source: https://github.com/Miserlou/Zappa/blob/master/zappa/middleware.py
    """
    new_headers = {}

    for key, values in headers.items():
        if len(values) > 1:
            for value, casing in zip(values, all_casings(key)):
                new_headers[casing] = value
        elif len(values) == 1:
            new_headers[key] = values[0]

    return new_headers


def group_headers(headers: List[Tuple[bytes, bytes]]) -> Dict[str, List[str]]:
    """Group headers by name for multi-value header support."""
    grouped: Dict[str, List[str]] = {}
    for name, value in headers:
        name_str = name.decode("latin1")
        value_str = value.decode("latin1")
        if name_str in grouped:
            grouped[name_str].append(value_str)
        else:
            grouped[name_str] = [value_str]
    return grouped


def is_alb_event(event: Dict[str, Any]) -> bool:
    """Check if the event comes from Application Load Balancer."""
    return event.get("requestContext", {}).get("elb") is not None


def encode_query_string(event: Dict[str, Any]) -> str:
    """Encode query string parameters from Lambda event."""
    params = event.get("multiValueQueryStringParameters")
    if not params:
        params = event.get("queryStringParameters")
    if not params:
        params = event.get("query")
    if not params:
        return ""

    if is_alb_event(event):
        # For ALB events, decode URL-encoded parameters
        decoded_params = []
        for key, values in params.items():
            if isinstance(values, list):
                for value in values:
                    decoded_params.append((unquote_plus(key), unquote_plus(value)))
            else:
                decoded_params.append((unquote_plus(key), unquote_plus(values)))
        return urlencode(decoded_params)

    # For non-ALB events, return empty string for now
    return ""


def get_body_bytes(event: Dict[str, Any], body: Optional[str]) -> bytes:
    """Convert event body to bytes."""
    if not body:
        return b""

    if event.get("isBase64Encoded", False):
        return base64.b64decode(body)

    if isinstance(body, str):
        return body.encode("utf-8")

    return body


def build_asgi_scope(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Build ASGI scope from Lambda event."""
    headers = event.get("multiValueHeaders") or event.get("headers", {})

    # Convert headers to ASGI format (list of 2-tuples of byte strings)
    asgi_headers = []
    if isinstance(headers, dict):
        if "multiValueHeaders" in event:
            # Multi-value headers
            for name, values in headers.items():
                if isinstance(values, list):
                    for value in values:
                        asgi_headers.append(
                            (name.lower().encode("latin1"), str(value).encode("latin1"))
                        )
                else:
                    asgi_headers.append(
                        (name.lower().encode("latin1"), str(values).encode("latin1"))
                    )
        else:
            # Single-value headers
            for name, value in headers.items():
                if value is not None:
                    asgi_headers.append(
                        (name.lower().encode("latin1"), str(value).encode("latin1"))
                    )

    path_info = event.get("path", "/")
    query_string = encode_query_string(event)

    # Extract JWT token from authorization header for OpenAPI security
    auth_header = event.get("headers", {}).get("authorization", "")
    jwt_token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.1"},
        "http_version": "1.1",
        "method": event.get("httpMethod", "GET"),
        "path": unquote(path_info),
        "raw_path": path_info.encode("utf-8"),
        "query_string": query_string.encode("latin1"),
        "root_path": "",
        "scheme": (
            headers.get("x-forwarded-proto", "https")
            if isinstance(headers, dict)
            else "https"
        ),
        "server": (
            (
                headers.get("host", "localhost").split(":")[0]
                if isinstance(headers, dict)
                else "localhost"
            ),
            (
                int(headers.get("x-forwarded-port", "443"))
                if isinstance(headers, dict)
                else 443
            ),
        ),
        "headers": asgi_headers,
        "aws.event": event,
        "aws.context": context,
        "jwt_token": jwt_token,
    }

    return scope


async def handle_request(
    app: Any, event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """Handle AWS Lambda request and convert to ASGI."""
    if event.get("source") in ["aws.events", "serverless-plugin-warmup"]:
        print("Lambda warming event received, skipping handler")
        return {}

    return await handle_payload(app, event, context)


async def handle_payload(
    app: Any, event: Dict[str, Any], context: Any
) -> Dict[str, Any]:
    """Process the Lambda event payload through ASGI application."""
    scope = build_asgi_scope(event, context)

    # Get request body
    body = event.get("body") or ""
    body_bytes = get_body_bytes(event, body)

    # ASGI message containers
    response_started: bool = False
    status_code: int = 200
    response_headers: List[Tuple[bytes, bytes]] = []
    response_body: List[bytes] = []

    async def receive() -> Dict[str, Any]:
        """ASGI receive callable."""
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False,
        }

    async def send(message: Dict[str, Any]) -> None:
        """ASGI send callable."""
        nonlocal response_started, status_code, response_headers, response_body

        if message["type"] == "http.response.start":
            response_started = True
            status_code = message["status"]
            response_headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            body_data = message.get("body", b"")
            if body_data:
                response_body.append(body_data)

    # Call the ASGI application
    await app(scope, receive, send)

    # Build Lambda response
    return generate_response(
        status_code, response_headers, b"".join(response_body), event
    )


def generate_response(
    status_code: int,
    headers: List[Tuple[bytes, bytes]],
    body: bytes,
    event: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate AWS Lambda response from ASGI response."""
    returndict: Dict[str, Any] = {"statusCode": status_code}

    # Process headers
    grouped_headers = group_headers(headers)

    if "multiValueHeaders" in event:
        returndict["multiValueHeaders"] = grouped_headers
    else:
        returndict["headers"] = split_headers(grouped_headers)

    if is_alb_event(event):
        # If the request comes from ALB we need to add a status description
        returndict["statusDescription"] = (
            f"{status_code} {HTTP_STATUS_CODES.get(status_code, 'Unknown')}"
        )

    # Process response body
    if body:
        # Determine content type
        content_type = "text/plain"
        content_encoding = ""

        for name, values in grouped_headers.items():
            if name.lower() == "content-type" and values:
                content_type = values[0]
            elif name.lower() == "content-encoding" and values:
                content_encoding = values[0]

        # Determine if body should be base64 encoded
        if (
            content_type.startswith("text/") or content_type in TEXT_MIME_TYPES
        ) and not content_encoding:
            try:
                returndict["body"] = body.decode("utf-8")
                returndict["isBase64Encoded"] = False
            except UnicodeDecodeError:
                returndict["body"] = base64.b64encode(body).decode("utf-8")
                returndict["isBase64Encoded"] = True
        else:
            returndict["body"] = base64.b64encode(body).decode("utf-8")
            returndict["isBase64Encoded"] = True
    else:
        returndict["body"] = ""
        returndict["isBase64Encoded"] = False

    return returndict


# Compatibility function for synchronous Lambda handlers
def lambda_handler(app: Any) -> Callable[[Dict[str, Any], Any], None]:
    """Create a Lambda handler function for an ASGI application."""

    def handler(event: Dict[str, Any], context: Any) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(handle_request(app, event, context))
        finally:
            loop.close()

    return handler
