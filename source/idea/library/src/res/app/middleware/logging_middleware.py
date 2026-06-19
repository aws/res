#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Awaitable, Callable, Optional, Set

from res.utils import logging_utils  # type: ignore
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

LOGGER = logging_utils.get_logger(__name__)

_SENSITIVE_FIELDS: Set[str] = {
    "authentication_token",
    "authenticationToken",
    "password",
    "token",
    "secret",
}
_REDACTED = "***"


def redact_sensitive_fields(raw: str) -> str:
    """Redact sensitive fields from a JSON string."""
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
    if not isinstance(parsed, dict):
        return raw
    for key in _SENSITIVE_FIELDS:
        if key in parsed:
            parsed[key] = _REDACTED
    return json.dumps(parsed)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging in async context."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Log request
        try:
            body = await request.body()
            data = body.decode("utf-8") if body else "EMPTY"
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    for key in _SENSITIVE_FIELDS:
                        if key in parsed:
                            parsed[key] = _REDACTED
                    data = json.dumps(parsed)
            except (json.JSONDecodeError, ValueError):
                if body:
                    data = "INVALID"
        except Exception:
            LOGGER.error("Exception while reading request body.")
            data = "INVALID"

        LOGGER.info(
            "Handling request: %s %s - Body: %s",
            request.method,
            request.url.path,
            data,
        )

        response = await call_next(request)

        # Log response
        response_data = await self._safely_read_response_body(response)
        if response_data:
            response_data = redact_sensitive_fields(response_data)
        LOGGER.info(
            "Responding to request %s %s: %s - Body: %s",
            request.method,
            request.url.path,
            response.status_code,
            response_data,
        )

        return response

    @staticmethod
    async def _safely_read_response_body(response: Response) -> Optional[str]:
        try:
            if hasattr(response, "body_iterator"):
                body_parts = []
                async for chunk in response.body_iterator:
                    if isinstance(chunk, (bytes, memoryview)):
                        body_parts.append(bytes(chunk))
                    else:
                        body_parts.append(str(chunk).encode("utf-8"))

                full_body = b"".join(body_parts)

                # Create a new streaming response with the same body
                def recreate_body():
                    yield full_body

                new_response = StreamingResponse(
                    recreate_body(),
                    status_code=response.status_code,
                    headers=response.headers,
                    media_type=getattr(response, "media_type", None),
                )

                # Update the original response object to maintain reference
                response.__dict__.update(new_response.__dict__)

                try:
                    return full_body.decode("utf-8")
                except UnicodeDecodeError:
                    return f"BINARY_DATA({len(full_body)} bytes)"

        except Exception as e:
            LOGGER.error("Exception while reading response body: %s", str(e))
            return f"ERROR_READING_BODY: {str(e)}"
