#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from connexion.exceptions import OAuthProblem

from res.resources import accounts  # type: ignore
from res.resources import permission_profiles, software_stacks  # type: ignore
import res.exceptions as exceptions  # type: ignore
from res.utils import ec2_utils

from api import exceptions as api_exceptions
from datamodel.models.get_permission_profile_response_content import (
    GetPermissionProfileResponseContent,
)  # noqa: E501
from datamodel.models.list_allowed_instance_types_for_session_request_content import (
    ListAllowedInstanceTypesForSessionRequestContent,
)  # noqa: E501
from datamodel.models.list_allowed_instance_types_for_session_response_content import (
    ListAllowedInstanceTypesForSessionResponseContent,
)  # noqa: E501
from datamodel.models.list_allowed_instance_types_request_content import (
    ListAllowedInstanceTypesRequestContent,
)  # noqa: E501
from datamodel.models.list_allowed_instance_types_response_content import (
    ListAllowedInstanceTypesResponseContent,
)  # noqa: E501
from datamodel.models.list_permission_profiles_response_content import (
    ListPermissionProfilesResponseContent,
)  # noqa: E501
from datamodel.models.virtual_desktop_permission_profile import (
    VirtualDesktopPermissionProfile,
)  # noqa: E501
from api.utils import (
    software_stack_utils,
)  # noqa: E501


def get_permission_profile(profile_id, user=None, token_info=None):  # noqa: E501
    """get_permission_profile

    Get details of a permission profile # noqa: E501

    :param profile_id: Id of the profile
    :type profile_id: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[GetPermissionProfileResponseContent, Tuple[GetPermissionProfileResponseContent, int], Tuple[GetPermissionProfileResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    try:
        profile = permission_profiles.get_permission_profile(profile_id)
    except exceptions.PermissionProfileNotFound as e:
        raise api_exceptions.NotFoundException(
            message=f"Permission profile {profile_id} not found"
        )

    return GetPermissionProfileResponseContent(
        profile=VirtualDesktopPermissionProfile.from_ddb_dict(profile)
    )


def list_allowed_instance_types(body=None, user=None, token_info=None):  # noqa: E501
    """list_allowed_instance_types

    List allowed instance types for virtual desktops # noqa: E501

    :param list_allowed_instance_types_request_content:
    :type list_allowed_instance_types_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListAllowedInstanceTypesResponseContent, Tuple[ListAllowedInstanceTypesResponseContent, int], Tuple[ListAllowedInstanceTypesResponseContent, int, Dict[str, str]]
    """
    request = ListAllowedInstanceTypesRequestContent.from_dict(body)

    hibernation_enabled = request.hibernation_support
    
    if request.software_stack is None:
        allowed_instance_types = (
            software_stacks.get_valid_instance_types_by_software_stack(
                hibernation_enabled
            )
        )
        return ListAllowedInstanceTypesResponseContent(listing=allowed_instance_types)

    software_stack_utils.set_software_stack_architecture(request.software_stack)

    allowed_instance_types = software_stacks.get_valid_instance_types_by_software_stack(
        hibernation_enabled, software_stack=request.software_stack.to_ddb_dict()
    )
    return ListAllowedInstanceTypesResponseContent(listing=allowed_instance_types)


def list_allowed_instance_types_for_session(
    body, user=None, token_info=None
):  # noqa: E501
    """list_allowed_instance_types_for_session

    List allowed instance types for a virtual desktop session # noqa: E501

    :param list_allowed_instance_types_for_session_request_content:
    :type list_allowed_instance_types_for_session_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListAllowedInstanceTypesForSessionResponseContent, Tuple[ListAllowedInstanceTypesForSessionResponseContent, int], Tuple[ListAllowedInstanceTypesForSessionResponseContent, int, Dict[str, str]]
    """
    request = ListAllowedInstanceTypesForSessionRequestContent.from_dict(body)
    session = request.session

    if session.hibernation_enabled is None or not session.software_stack:
        missing = []
        if session.hibernation_enabled is None:
            missing.append("'hibernation_enabled'")
        if not session.software_stack:
            missing.append("'software_stack'")
        raise api_exceptions.BadRequestException(
            message=f"Invalid request: {', '.join(missing)} is a required property"
        )
    
    software_stack_utils.set_software_stack_architecture(session.software_stack)

    allowed_instance_types_dict = ec2_utils.get_valid_instance_types_by_allowed_list(
        session.hibernation_enabled, session.software_stack.allowed_instance_types or []
    )
    allowed_instance_types = []
    for instance_type_name, instance_info in allowed_instance_types_dict.items():
        if software_stacks.validate_min_ram(
            instance_type_name, session.software_stack.to_ddb_dict()
        ):
            allowed_instance_types.append(instance_info)

    return ListAllowedInstanceTypesForSessionResponseContent(
        listing=allowed_instance_types
    )


def list_permission_profiles(
    profile_id=None, next_token=None, user=None, token_info=None
):  # noqa: E501
    """list_permission_profiles

    Get a list of permission profiles # noqa: E501

    :param profile_id: Filter by profileId
    :type profile_id: str
    :param next_token: Pagination token for next page
    :type next_token: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListPermissionProfilesResponseContent, Tuple[ListPermissionProfilesResponseContent, int], Tuple[ListPermissionProfilesResponseContent, int, Dict[str, str]]
    """

    profiles, response_next_token = (
        permission_profiles.list_permission_profiles_paginated(
            profile_id=profile_id, next_token=next_token
        )
    )

    profile_objects = [
        VirtualDesktopPermissionProfile.from_ddb_dict(profile) for profile in profiles
    ]

    return ListPermissionProfilesResponseContent(
        listing=profile_objects, next_token=response_next_token
    )
