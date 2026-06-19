#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import functools
import json
import logging
from typing import Any, Awaitable, Callable, Union

import connexion
from connexion.exceptions import OAuthProblem
from connexion.lifecycle import ConnexionRequest, ConnexionResponse
from datamodel.jsonifier import CustomJsonifier
from datamodel.models.bad_request_exception_response_content import (
    BadRequestExceptionResponseContent,
)
from datamodel.models.internal_service_exception_response_content import (
    InternalServiceExceptionResponseContent,
)
from res.app.exceptions import (  # type: ignore
    BadRequestException,
    InternalServiceException,
    NotFoundException,
)
from res.app.middleware.logging_middleware import LoggingMiddleware  # type: ignore
from res.utils import logging_utils  # type: ignore
from starlette.exceptions import HTTPException

LOGGER = logging_utils.get_logger(__name__)


def json_dumps(obj, **kwargs):
    """Custom JSON dumps function that uses our custom serializer."""
    return CustomJsonifier.dumps(obj, **kwargs)


def log_response_error(
    func: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    @functools.wraps(func)
    async def _log_response_error(*args: Any, **kwargs: Any) -> Any:
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


class RESAsyncApp(connexion.AsyncApp):  # type: ignore[misc]
    """Async Flask app that implements the RES API using ASGI."""

    def __init__(
        self,
        import_name: str,
        specification_dir: str,
        openapi_filename: str,
        api_title: str,
        swagger_ui: bool = False,
        validate_responses: bool = False,
    ) -> None:
        super().__init__(import_name, specification_dir=specification_dir)

        # Use the custom jsonifier class to handle Model objects
        self.add_api(
            openapi_filename,
            arguments={"title": api_title},
            pythonic_params=True,
            options={"swagger_ui": swagger_ui},
            validate_responses=validate_responses,
            jsonifier=CustomJsonifier(),
        )

        self.add_middleware(LoggingMiddleware)

        self.add_error_handler(HTTPException, self._handle_exception)
        self.add_error_handler(OAuthProblem, self._handle_exception)
        self.add_error_handler(BadRequestException, self._handle_lambda_exception)
        self.add_error_handler(InternalServiceException, self._handle_lambda_exception)
        self.add_error_handler(NotFoundException, self._handle_lambda_exception)
        self.add_error_handler(Exception, self._handle_unexpected_exception)

    @staticmethod
    @log_response_error
    async def _handle_lambda_exception(
        request: ConnexionRequest,
        exception: Union[
            BadRequestException, InternalServiceException, NotFoundException
        ],
    ) -> ConnexionResponse:
        """Handle Lambda-specific exceptions that wrap auto-generated models."""

        # Get Lambda response format from the exception
        lambda_response = exception.to_lambda_response()

        return ConnexionResponse(
            status_code=lambda_response["statusCode"],
            body=lambda_response["body"],  # Already JSON string
            headers=lambda_response.get("headers", {}),
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
            response_body = InternalServiceExceptionResponseContent(
                message=exception.detail
            )
        else:
            # Fallback for other status codes
            response_body = {"error": exception.detail}

        return ConnexionResponse(
            status_code=exception.status_code,
            body=json_dumps(
                response_body.to_dict()
                if hasattr(response_body, "to_dict")
                else response_body
            ),
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
