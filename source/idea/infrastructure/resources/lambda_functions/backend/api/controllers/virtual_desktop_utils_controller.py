#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from connexion.exceptions import OAuthProblem

from res.resources import accounts  # type: ignore
from res.resources import permission_profiles  # type: ignore
from res.utils import table_utils, time_utils  # type: ignore
import res.exceptions as exceptions  # type: ignore

from api.exceptions import BadRequestException, InternalServiceException
from api.models.bad_request_exception_response_content import BadRequestExceptionResponseContent  # noqa: E501
from api.models.get_permission_profile_response_content import GetPermissionProfileResponseContent  # noqa: E501
from api.models.internal_service_exception_response_content import InternalServiceExceptionResponseContent  # noqa: E501
from api.models.list_allowed_instance_types_for_session_request_content import ListAllowedInstanceTypesForSessionRequestContent  # noqa: E501
from api.models.list_allowed_instance_types_for_session_response_content import ListAllowedInstanceTypesForSessionResponseContent  # noqa: E501
from api.models.list_allowed_instance_types_request_content import ListAllowedInstanceTypesRequestContent  # noqa: E501
from api.models.list_allowed_instance_types_response_content import ListAllowedInstanceTypesResponseContent  # noqa: E501
from api.models.list_permission_profiles_response_content import ListPermissionProfilesResponseContent  # noqa: E501
from api.models.list_schedule_types_response_content import ListScheduleTypesResponseContent  # noqa: E501
from api.models.list_supported_gpus_response_content import ListSupportedGpusResponseContent  # noqa: E501
from api.models.list_supported_oses_response_content import ListSupportedOsesResponseContent  # noqa: E501
from api.models.virtual_desktop_base_os import VirtualDesktopBaseOs  # noqa: E501
from api.models.virtual_desktop_gpu import VirtualDesktopGpu  # noqa: E501
from api.models.virtual_desktop_permission_profile import VirtualDesktopPermissionProfile  # noqa: E501
from api.models.virtual_desktop_schedule_type import VirtualDesktopScheduleType  # noqa: E501
from api.utils import virtual_desktop_controller_utils, virtual_desktop_utils_utils, model_utils  # noqa: E501
from api import util


def get_permission_profile(profile_id, user=None, token_info=None):  # noqa: E501
    """get_permission_profile

    Get details of a permission profile # noqa: E501

    :param profile_id: Id of the profile
    :type profile_id: str

    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[GetPermissionProfileResponseContent, Tuple[GetPermissionProfileResponseContent, int], Tuple[GetPermissionProfileResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    try:
        profile = permission_profiles.get_permission_profile(profile_id)
    except exceptions.PermissionProfileNotFound as e:
        return BadRequestExceptionResponseContent(message=str(e)), 400

    # Convert from DynamoDB format (flattened permissions) to API format (permissions list)
    profile = virtual_desktop_utils_utils.convert_db_dict_to_api_format(profile)

    profile = model_utils.convert_timestamps_to_iso(profile)

    profile_obj = VirtualDesktopPermissionProfile.from_dict(profile)
    return GetPermissionProfileResponseContent(profile=profile_obj)


def list_allowed_instance_types(body=None, user=None, token_info=None):  # noqa: E501
    """list_allowed_instance_types

    List allowed instance types for virtual desktops # noqa: E501

    :param list_allowed_instance_types_request_content:
    :type list_allowed_instance_types_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListAllowedInstanceTypesResponseContent, Tuple[ListAllowedInstanceTypesResponseContent, int], Tuple[ListAllowedInstanceTypesResponseContent, int, Dict[str, str]]
    """
    request = ListAllowedInstanceTypesRequestContent.from_dict(body)

    hibernation_enabled = request.hibernation_support

    if request.software_stack is None:
        allowed_instance_types = (
            virtual_desktop_controller_utils.get_valid_instance_types_by_software_stack(
                hibernation_enabled
            )
        )
        return ListAllowedInstanceTypesResponseContent(listing=allowed_instance_types)

    virtual_desktop_controller_utils.set_software_stack_architecture(
        request.software_stack
    )

    allowed_instance_types = (
        virtual_desktop_controller_utils.get_valid_instance_types_by_software_stack(
            hibernation_enabled, software_stack=request.software_stack
        )
    )
    return ListAllowedInstanceTypesResponseContent(listing=allowed_instance_types)


def list_allowed_instance_types_for_session(body, user=None, token_info=None):  # noqa: E501
    """list_allowed_instance_types_for_session

    List allowed instance types for a virtual desktop session # noqa: E501

    :param list_allowed_instance_types_for_session_request_content:
    :type list_allowed_instance_types_for_session_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListAllowedInstanceTypesForSessionResponseContent, Tuple[ListAllowedInstanceTypesForSessionResponseContent, int], Tuple[ListAllowedInstanceTypesForSessionResponseContent, int, Dict[str, str]]
    """
    request = ListAllowedInstanceTypesForSessionRequestContent.from_dict(body)
    session = request.session

    virtual_desktop_controller_utils.set_software_stack_architecture(
        session.software_stack
    )

    allowed_instance_types_dict = (
        virtual_desktop_controller_utils.get_valid_instance_types_by_allowed_list(
            session.hibernation_enabled, session.software_stack.allowed_instance_types or []
        )
    )
    allowed_instance_types = []
    for instance_type_name, instance_info in allowed_instance_types_dict.items():
        if virtual_desktop_controller_utils.validate_min_ram(
            instance_type_name, session.software_stack
        ):
            allowed_instance_types.append(instance_info)

    return ListAllowedInstanceTypesForSessionResponseContent(listing=allowed_instance_types)


def list_permission_profiles(profile_id=None, next_token=None, user=None, token_info=None):  # noqa: E501
    """list_permission_profiles

    Get a list of permission profiles # noqa: E501

    :param profile_id: Filter by profileId
    :type profile_id: str
    :param next_token: Pagination token for next page
    :type next_token: str

    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListPermissionProfilesResponseContent, Tuple[ListPermissionProfilesResponseContent, int], Tuple[ListPermissionProfilesResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    table_name = "vdc.controller.permission-profiles"

    # Build ScanFilter if profile_id is provided
    scan_filter = None
    if profile_id:
        scan_filter = {
            'profile_id': {
                'AttributeValueList': [profile_id],
                'ComparisonOperator': 'CONTAINS'
            }
        }

    profiles = table_utils.list_items(table_name, scan_filter=scan_filter)

    # Convert from DynamoDB format to API format
    profiles = [virtual_desktop_utils_utils.convert_db_dict_to_api_format(profile) for profile in profiles]

    # Convert timestamps to ISO format strings and create VirtualDesktopPermissionProfile objects
    profile_objects = [
        VirtualDesktopPermissionProfile.from_dict(model_utils.convert_timestamps_to_iso(profile))
        for profile in profiles
    ]

    return ListPermissionProfilesResponseContent(listing=profile_objects)



def list_schedule_types(user=None, token_info=None):  # noqa: E501
    """list_schedule_types

    List available schedule types for virtual desktops # noqa: E501


    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListScheduleTypesResponseContent, Tuple[ListScheduleTypesResponseContent, int], Tuple[ListScheduleTypesResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem(detail="Unauthorized user")

    return ListScheduleTypesResponseContent(
        listing=[type_.value for type_ in VirtualDesktopScheduleType]
    )


def list_supported_gpus(user=None, token_info=None):  # noqa: E501
    """list_supported_gpus

    List supported GPUs for virtual desktops # noqa: E501


    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListSupportedGpusResponseContent, Tuple[ListSupportedGpusResponseContent, int], Tuple[ListSupportedGpusResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem(detail="Unauthorized user")

    return ListSupportedGpusResponseContent(listing=[gpu.value for gpu in VirtualDesktopGpu])


def list_supported_oses(user=None, token_info=None):  # noqa: E501
    """list_supported_o_ses

    List supported operating systems for virtual desktops # noqa: E501


    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListSupportedOsesResponseContent, Tuple[ListSupportedOsesResponseContent, int], Tuple[ListSupportedOsesResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem(detail="Unauthorized user")

    return ListSupportedOsesResponseContent(listing=[os.value for os in VirtualDesktopBaseOs])
