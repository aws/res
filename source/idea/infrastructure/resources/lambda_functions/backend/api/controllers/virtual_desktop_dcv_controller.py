#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Dict, Tuple, Union

import connexion
from api import util
from api.exceptions import BadRequestException
from api.models.bad_request_exception_response_content import (  # noqa: E501
    BadRequestExceptionResponseContent,
)
from api.models.batch_get_dcv_sessions_request_content import (  # noqa: E501
    BatchGetDCVSessionsRequestContent,
)
from api.models.batch_get_dcv_sessions_response_content import (  # noqa: E501
    BatchGetDCVSessionsResponseContent,
)
from api.models.internal_service_exception_response_content import (  # noqa: E501
    InternalServiceExceptionResponseContent,
)
from api.models.list_dcv_servers_response_content import (  # noqa: E501
    ListDCVServersResponseContent,
)
from connexion.exceptions import OAuthProblem
from res.clients import dcv_swagger_client
from res.clients.dcv_broker import dcv_broker_client
from res.clients.dcv_swagger_client.api.servers_api import ServersApi
from res.clients.dcv_swagger_client.models.describe_servers_request_data import (
    DescribeServersRequestData,
)
from res.resources import accounts
from res.utils import logging_utils

logger = logging_utils.get_logger(__name__)


def _get_servers_api() -> ServersApi:
    """Get configured ServersApi instance using dcv_broker_client utilities"""
    api_instance = ServersApi(
        dcv_swagger_client.ApiClient(dcv_broker_client._get_client_configuration())
    )
    dcv_broker_client._set_request_headers(api_instance.api_client)
    return api_instance


def batch_get_dcv_sessions(body=None, user=None, token_info=None):  # noqa: E501
    """batch_get_dcv_sessions

    Retrieve details of DCV sessions # noqa: E501

    :param body: Request body containing sessions to query
    :type body: dict

    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[BatchGetDCVSessionsResponseContent, Tuple[BatchGetDCVSessionsResponseContent, int], Tuple[BatchGetDCVSessionsResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    request = BatchGetDCVSessionsRequestContent.from_dict(body)
    sessions = request.sessions if request.sessions is not None else []
    
    # Convert session objects to dictionaries for dcv_broker_client
    sessions_list = []
    if sessions:
        for session in sessions:
            sessions_list.append(session.to_dict())
    
    # Call describe_sessions from dcv_broker_client
    response = dcv_broker_client.describe_sessions(sessions_list, request.next_token)
    
    # Extract next_token if present in response
    response_next_token = response.pop('next_token', None)        
    return BatchGetDCVSessionsResponseContent(response=response, next_token=response_next_token)


def list_dcv_servers(next_token=None, user=None, token_info=None):  # noqa: E501
    """list_dcv_servers

    List DCV Servers # noqa: E501

    :param next_token: Pagination token for next page
    :type next_token: str
    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dictequest_data = DescribeServersRequestData(next_token=next_token)
    :rtype: Union[ListDCVServersResponseContent, Tuple[ListDCVServersResponseContent, int], Tuple[ListDCVServersResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")
    
    servers_api = _get_servers_api()
    request_data = DescribeServersRequestData(next_token=next_token)
    response = servers_api.describe_servers(body=request_data)
    response_dict = response.to_dict()

    # Extract next_token from response attribute into its own
    response_next_token = response_dict.pop('next_token', None)

    return ListDCVServersResponseContent(response=response_dict, next_token=response_next_token)
