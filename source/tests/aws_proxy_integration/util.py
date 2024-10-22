import os
from typing import Any

import requests


def post_api_response_data(url_path: str, headers: Any, request_body: Any) -> Any:
    """
    Makes an API request with the provided headers and request body, and returns the JSON response data.
    """
    response = post_api_response(url_path, headers, request_body)
    response.raise_for_status()  # Raise an exception for non-2xx status codes

    data = response.json()
    return data


def post_api_response(url_path: str, headers: Any, request_body: Any) -> Any:
    """
    Makes an API request with the provided headers and request body, and returns the JSON response data.
    """
    base_url = os.environ.get("BASE_URL")
    if not base_url:
        raise ValueError("BASE_URL environment variable is not set")

    url = f"{base_url}{url_path}"
    response = requests.post(url, headers=headers, json=request_body, verify=False)
    return response


def get_api_response_data(url_path: str, headers: Any) -> Any:
    """
    Makes an API request with the provided headers and request body, and returns the JSON response data.
    """
    response = get_api_response(url_path, headers)
    response.raise_for_status()  # Raise an exception for non-2xx status codes

    data = response.json()
    return data


def get_api_response(url_path: str, headers: Any) -> Any:
    """
    Makes an API request with the provided headers and request body, and returns the JSON response data.
    """
    base_url = os.environ.get("BASE_URL")
    if not base_url:
        raise ValueError("BASE_URL environment variable is not set")

    url = f"{base_url}{url_path}"
    response = requests.get(url, headers=headers, verify=False)
    return response
