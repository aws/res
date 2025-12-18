#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import functools
import json
import logging
from typing import Any, Awaitable, Callable, Optional, Union

import connexion
from api.jsonifier import CustomJsonifier
from api.exceptions import BadRequestException, InternalServiceException
from api.models.bad_request_exception_response_content import BadRequestExceptionResponseContent
from api.models.internal_service_exception_response_content import InternalServiceExceptionResponseContent
from connexion.exceptions import OAuthProblem
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from res.utils import logging_utils  # type: ignore
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

LOGGER = logging_utils.get_logger(__name__)


def json_dumps(obj, **kwargs):
    """Custom JSON dumps function that uses our custom serializer."""
    return CustomJsonifier.dumps(obj, **kwargs)


def log_response_error(
    func: Callable[..., Awaitable[Response]]
) -> Callable[..., Awaitable[Response]]:
    @functools.wraps(func)
    async def _log_response_error(*args: Any, **kwargs: Any) -> Response:
        response = await func(*args, **kwargs)
        status_code = getattr(response, "status_code", 200)
        LOGGER.log(
            logging.ERROR if status_code >= 500 else logging.INFO,
            "Handling exception (status code %s): %s",
            status_code,
            getattr(response, "body", ""),
            exc_info=status_code >= 500,
        )
        return response

    return _log_response_error


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
                json.loads(data)  # Validate JSON
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


class RESAsyncApp(connexion.AsyncApp):  # type: ignore[misc]
    """Async Flask app that implements the RES API using ASGI."""

    def __init__(
        self, swagger_ui: bool = False, validate_responses: bool = False
    ) -> None:
        options = {"swagger_ui": swagger_ui}

        super().__init__(__name__, specification_dir="api/openapi/")

        # Use the custom jsonifier class to handle Model objects
        self.add_api(
            "RES.openapi.yaml",
            arguments={"title": "RES API"},
            pythonic_params=True,
            options=options,
            validate_responses=validate_responses,
            jsonifier=CustomJsonifier(),
        )

        self.add_middleware(LoggingMiddleware)

        self.add_error_handler(HTTPException, self._handle_exception)
        self.add_error_handler(OAuthProblem, self._handle_exception)
        self.add_error_handler(BadRequestException, self._handle_lambda_exception)
        self.add_error_handler(InternalServiceException, self._handle_lambda_exception)
        self.add_error_handler(Exception, self._handle_unexpected_exception)

    @staticmethod
    @log_response_error
    async def _handle_lambda_exception(
        request: ConnexionRequest, exception: Union[BadRequestException, InternalServiceException]
    ) -> ConnexionResponse:
        """Handle Lambda-specific exceptions that wrap auto-generated models."""
        
        # Get Lambda response format from the exception
        lambda_response = exception.to_lambda_response()
        
        return ConnexionResponse(
            status_code=lambda_response["statusCode"],
            body=lambda_response["body"],  # Already JSON string
            headers=lambda_response.get("headers", {})
        )

    @staticmethod
    @log_response_error
    async def _handle_exception(
        request: ConnexionRequest, exception: Union[HTTPException, OAuthProblem]
    ) -> ConnexionResponse:
        """Render a HTTPException according to RES API specs."""
        
        # Create proper response model based on status code
        if exception.status_code == 400:
            response_body = BadRequestExceptionResponseContent(message=exception.detail)
        elif exception.status_code == 500:
            response_body = InternalServiceExceptionResponseContent(message=exception.detail)
        else:
            # Fallback for other status codes
            response_body = {"error": exception.detail}
        
        return ConnexionResponse(
            status_code=exception.status_code,
            body=json_dumps(response_body.to_dict() if hasattr(response_body, 'to_dict') else response_body),
        )

    @staticmethod
    async def _handle_unexpected_exception(
        request: ConnexionRequest, exception: Exception
    ) -> ConnexionResponse:
        """Handle an unexpected exception."""
        LOGGER.critical("Unexpected exception: %s", exception, exc_info=True)

        response_body = InternalServiceExceptionResponseContent(message=str(exception))
        return ConnexionResponse(
            status_code=500, body=json_dumps(response_body.to_dict())
        )

    def start_local_server(self, port: int = 8080) -> None:
        """Start a local development server."""
        try:
            import uvicorn

            # uvicorn.run is synchronous
            # connexion.AsyncApp is callable and serves as the ASGI app
            uvicorn.run(self, host="0.0.0.0", port=port)
        except ImportError:
            LOGGER.error("uvicorn not installed. Install with: pip install uvicorn")
            raise


def create_async_app(
    swagger_ui: bool = False, validate_responses: bool = False
) -> RESAsyncApp:
    """Create and return an async RES application."""
    return RESAsyncApp(swagger_ui=swagger_ui, validate_responses=validate_responses)


if __name__ == "__main__":
    app = create_async_app(swagger_ui=True, validate_responses=True)
    app.start_local_server()
