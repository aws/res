#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Dict, Union


def _create_api_response(
    status_code: int,
    status_description: str,
    body: Union[Dict[str, Any], str, None] = None,
    is_base64_encoded: bool = False,
) -> Dict[str, Any]:
    """
    Creates a standardized API response.

    Args:
        status_code (int): The HTTP status code.
        status_description (str): A brief description of the response status.
        body (Union[Dict, str, None], optional): The response body. If a dict is provided,
                                                 it will be JSON-encoded. Defaults to None.
        is_base64_encoded (bool, optional): Whether the body is Base64 encoded. Defaults to False.

    Returns:
        Dict[str, Any]: A formatted response dictionary.
    """
    response = {
        "isBase64Encoded": is_base64_encoded,
        "statusCode": status_code,
        "statusDescription": status_description,
        "headers": {"Content-Type": "application/json"},
    }

    if isinstance(body, dict):
        response["body"] = json.dumps(body)
    elif isinstance(body, str):
        response["body"] = body
    else:
        response["body"] = json.dumps({})

    return response
