#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Custom exceptions that wrap auto-generated models and return proper Lambda response format.
This allows you to raise exceptions using your OpenAPI-generated models while ensuring
the Lambda function returns the correct response structure for API Gateway.
"""

import json
from typing import Any, Dict, Optional

from datamodel.models.bad_request_exception_response_content import (
    BadRequestExceptionResponseContent,
)
from datamodel.models.forbidden_exception_response_content import (
    ForbiddenExceptionResponseContent,
)
from datamodel.models.internal_service_exception_response_content import (
    InternalServiceExceptionResponseContent,
)
from datamodel.models.not_found_exception_response_content import (
    NotFoundExceptionResponseContent,
)


class BadRequestException(Exception):
    """
    Exception that wraps BadRequestExceptionResponseContent and returns proper Lambda response.

    Usage:
        raise BadRequestException("Missing software_stack.ami_id")

    This will create a Lambda response with:
    - statusCode: 400
    - headers: {"Content-Type": "application/json"}
    - body: JSON string from your auto-generated model
    """

    def __init__(self, message: str, headers: Optional[Dict[str, str]] = None):
        self.message = message
        self.status_code = 400
        self.headers = headers or {"Content-Type": "application/json"}

        # Use your auto-generated model
        self.response_model = BadRequestExceptionResponseContent(message=message)

        super().__init__(message)

    def to_lambda_response(self) -> Dict[str, Any]:
        return {
            "statusCode": self.status_code,
            "headers": self.headers,
            "body": json.dumps(self.response_model.to_dict()),
        }


class InternalServiceException(Exception):
    """
    Exception that wraps InternalServiceExceptionResponseContent and returns proper Lambda response.

    Usage:
        raise InternalServiceException("Database connection failed")
    """

    def __init__(self, message: str, headers: Optional[Dict[str, str]] = None):
        self.message = message
        self.status_code = 500
        self.headers = headers or {"Content-Type": "application/json"}

        # Use your auto-generated model
        self.response_model = InternalServiceExceptionResponseContent(message=message)

        super().__init__(message)

    def to_lambda_response(self) -> Dict[str, Any]:
        return {
            "statusCode": self.status_code,
            "headers": self.headers,
            "body": json.dumps(self.response_model.to_dict()),
        }


class ForbiddenException(Exception):
    """
    Exception for 403 Forbidden responses.

    Usage:
        raise ForbiddenException("Session not found or access denied")
    """

    def __init__(self, message: str, headers: Optional[Dict[str, str]] = None):
        self.message = message
        self.status_code = 403
        self.headers = headers or {"Content-Type": "application/json"}

        self.response_model = ForbiddenExceptionResponseContent(message=message)

        super().__init__(message)

    def to_lambda_response(self) -> Dict[str, Any]:
        return {
            "statusCode": self.status_code,
            "headers": self.headers,
            "body": json.dumps(self.response_model.to_dict()),
        }


class NotFoundException(Exception):
    """
    Exception that wraps NotFoundExceptionResponseContent and returns proper Lambda response.

    Usage:
        raise NotFoundException("<Record> was not found")
    """

    def __init__(self, message: str, headers: Optional[Dict[str, str]] = None):
        self.message = message
        self.status_code = 404
        self.headers = headers or {"Content-Type": "application/json"}

        # Use your auto-generated model
        self.response_model = NotFoundExceptionResponseContent(message=message)

        super().__init__(message)

    def to_lambda_response(self) -> Dict[str, Any]:
        return {
            "statusCode": self.status_code,
            "headers": self.headers,
            "body": json.dumps(self.response_model.to_dict()),
        }
