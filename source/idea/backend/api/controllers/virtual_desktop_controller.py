#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from connexion.exceptions import OAuthProblem
import uuid

from res import exceptions as res_exceptions  # type: ignore

from api import exceptions as api_exceptions
from datamodel.models.delete_permission_profile_response_content import (
    DeletePermissionProfileResponseContent,
)  # noqa: E501
from datamodel.models.update_permission_profile_response_content import (
    UpdatePermissionProfileResponseContent,
)  # noqa: E501
from datamodel.models.update_permission_profile_request_content import (
    UpdatePermissionProfileRequestContent,
)  # noqa: E501
from datamodel.models.create_software_stack_request_content import (
    CreateSoftwareStackRequestContent,
)  # noqa: E501
from datamodel.models.create_software_stack_response_content import (
    CreateSoftwareStackResponseContent,
)  # noqa: E501
from datamodel.models.delete_software_stack_response_content import (
    DeleteSoftwareStackResponseContent,
)  # noqa: E501
from datamodel.models.get_software_stack_response_content import (
    GetSoftwareStackResponseContent,
)  # noqa: E501
from datamodel.models.list_software_stacks_response_content import (
    ListSoftwareStacksResponseContent,
)  # noqa: E501
from datamodel.models.update_software_stack_request_content import (
    UpdateSoftwareStackRequestContent,
)  # noqa: E501
from datamodel.models.update_software_stack_response_content import (
    UpdateSoftwareStackResponseContent,
)  # noqa: E501
from datamodel.models.virtual_desktop_software_stack import (
    VirtualDesktopSoftwareStack,
)  # noqa: E501
from datamodel.models.list_sessions_response_content import (
    ListSessionsResponseContent,
)  # noqa: E501
from datamodel.models.list_session_permissions_response_content import (
    ListSessionPermissionsResponseContent,
)  # noqa: E501
from datamodel.models.list_shared_permissions_response_content import (
    ListSharedPermissionsResponseContent,
)  # noqa: E501
from datamodel.models.virtual_desktop_session_permission import (
    VirtualDesktopSessionPermission,
)  # noqa: E501
from datamodel.models.virtual_desktop_session import (
    VirtualDesktopSession,
)  # noqa: E501
from datamodel.models.update_session_permissions_request_content import (
    UpdateSessionPermissionsRequestContent,
)  # noqa: E501
from datamodel.models.update_session_permissions_response_content import (
    UpdateSessionPermissionsResponseContent,
)  # noqa: E501

from datamodel.models.virtual_desktop_permission_profile import (
    VirtualDesktopPermissionProfile,
)  # noqa: E501
from datamodel.models.create_permission_profile_request_content import (
    CreatePermissionProfileRequestContent,
)  # noqa: E501
from datamodel.models.create_permission_profile_response_content import (
    CreatePermissionProfileResponseContent,
)  # noqa: E501
from datamodel.models.get_session_response_content import (
    GetSessionResponseContent,
)
from datamodel.models.virtual_desktop_session import VirtualDesktopSession

from api.utils.software_stack_utils import (
    validate_software_stack_fields,
)
from api.utils.virtual_desktop_controller_utils import (
    validate_date_range_filter,
)
from api.utils.session_permission_utils import (
    validate_update_session_permission_request,
    UPDATE_SESSION_PERMISSION_INVALID_REQUEST_ERROR_MESSAGE,
)
from res.resources import (
    accounts,
    software_stacks,
    permission_profiles,
    session_permissions as res_session_permissions,
    sessions as res_sessions,
)


def create_software_stack(body, user=None, token_info=None):  # noqa: E501
    """create_software_stack

    Create Software Stack Session # noqa: E501

    :param create_software_stack_request_content:
    :type create_software_stack_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[CreateSoftwareStackResponseContent, Tuple[CreateSoftwareStackResponseContent, int], Tuple[CreateSoftwareStackResponseContent, int, Dict[str, str]]
    """

    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    request = CreateSoftwareStackRequestContent.from_dict(body)
    software_stack = request.software_stack

    if not software_stack.stack_id:
        software_stack.stack_id = str(uuid.uuid4())

    validated_stack, is_valid = validate_software_stack_fields(request.software_stack)
    if is_valid is False:
        raise api_exceptions.BadRequestException(
            message=f"Invalid software stack request: {validated_stack.failure_reason}"
        )

    software_stack_dict = software_stack.to_ddb_dict()
    created_software_stack = software_stacks.create_software_stack(software_stack_dict)

    return CreateSoftwareStackResponseContent(
        software_stack=VirtualDesktopSoftwareStack.from_ddb_dict(created_software_stack)
    )


def delete_software_stack(stack_id, body, user=None, token_info=None):  # noqa: E501
    """delete_software_stack

    Delete Software Stack # noqa: E501

    :param stack_id: The software stack ID from URL parameter
    :type stack_id: str
    :param delete_software_stack_request_content:
    :type delete_software_stack_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[DeleteSoftwareStackResponseContent, Tuple[DeleteSoftwareStackResponseContent, int], Tuple[DeleteSoftwareStackResponseContent, int, Dict[str, str]]
    """

    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    try:
        software_stacks.delete_software_stack(body["base_os"], stack_id)
        return DeleteSoftwareStackResponseContent(success=True)
    except res_exceptions.SoftwareStackNotFound:
        raise api_exceptions.NotFoundException(message="Software stack not found")
    except Exception as e:
        raise api_exceptions.InternalServiceException(message=str(e))


def list_software_stacks(
    project_id=None,
    base_os=None,
    software_stack_name=None,
    next_token=None,
    user=None,
    token_info=None,
):  # noqa: E501
    """list_software_stacks

    Get a list of software stacks # noqa: E501

    :param project_id: Filter by project ID
    :type project_id: str
    :param base_os: Filter by base operating system
    :type base_os: str
    :param software_stack_name: Filter by software stack name
    :type software_stack_name: str
    :param next_token: Pagination token for next page
    :type next_token: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListSoftwareStacksResponseContent, Tuple[ListSoftwareStacksResponseContent, int], Tuple[ListSoftwareStacksResponseContent, int, Dict[str, str]]
    """
    is_admin = accounts.is_active_admin(user)

    if not is_admin and not project_id:
        raise api_exceptions.BadRequestException(message="project_id is required field")

    stacks, response_next_token = software_stacks.list_software_stacks(
        project_id=project_id,
        base_os=base_os,
        name=software_stack_name,
        next_token=next_token,
    )

    return ListSoftwareStacksResponseContent(
        listing=[VirtualDesktopSoftwareStack.from_ddb_dict(stack) for stack in stacks],
        next_token=response_next_token,
    )


def update_software_stack(body, stack_id, user=None, token_info=None):  # noqa: E501
    """update_software_stack

    Update Software Stack # noqa: E501

    :param update_software_stack_request_content:
    :type update_software_stack_request_content: dict | bytes
    :param stack_id:
    :type stack_id: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[UpdateSoftwareStackResponseContent, Tuple[UpdateSoftwareStackResponseContent, int], Tuple[UpdateSoftwareStackResponseContent, int, Dict[str, str]]
    """

    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    request = UpdateSoftwareStackRequestContent.from_dict(body)
    software_stack = request.software_stack

    try:
        _existing_stack = software_stacks.get_software_stack(
            base_os=software_stack.base_os, stack_id=stack_id
        )
    except Exception:
        raise api_exceptions.NotFoundException(
            message=f"Software stack with {software_stack.base_os.value} and {stack_id} not found"
        )

    software_stack.stack_id = stack_id
    validated_stack, is_valid = validate_software_stack_fields(request.software_stack)
    if is_valid is False:
        raise api_exceptions.BadRequestException(
            message=f"Invalid software stack request: {validated_stack.failure_reason}"
        )

    updated_software_stack = software_stacks.update_software_stack(
        validated_stack.to_ddb_dict()
    )

    stack_obj = VirtualDesktopSoftwareStack.from_ddb_dict(updated_software_stack)

    return UpdateSoftwareStackResponseContent(software_stack=stack_obj)


def get_software_stack(stack_id, base_os, user=None, token_info=None):  # noqa: E501
    """get_software_stack

    Get details of a software stack # noqa: E501

    :param stack_id: Software stack identifier
    :type stack_id: str
    :param base_os: Base operating system for the software stack
    :type base_os: dict | bytes

    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[GetSoftwareStackResponseContent, Tuple[GetSoftwareStackResponseContent, int], Tuple[GetSoftwareStackResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    try:
        stack = software_stacks.get_software_stack(
            base_os=base_os, stack_id=stack_id, get_project_details=True
        )
    except res_exceptions.SoftwareStackNotFound as e:
        raise api_exceptions.BadRequestException(str(e))

    stack_obj = VirtualDesktopSoftwareStack.from_ddb_dict(stack)

    return GetSoftwareStackResponseContent(software_stack=stack_obj)


def create_permission_profile(body, user=None, token_info=None):  # noqa: E501
    """create_permission_profile

    Create Permission Profile # noqa: E501

    :param create_permission_profile_request_content:
    :type create_permission_profile_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[CreatePermissionProfileResponseContent, Tuple[CreatePermissionProfileResponseContent, int], Tuple[CreatePermissionProfileResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    request = CreatePermissionProfileRequestContent.from_dict(body)
    profile = request.profile

    try:
        existing_profile_dict = permission_profiles.get_permission_profile(
            profile_id=profile.profile_id
        )
        if existing_profile_dict:
            raise api_exceptions.BadRequestException(
                f"profile_id: {profile.profile_id} already exists."
            )
    except res_exceptions.PermissionProfileNotFound:
        pass

    profile_dict = profile.to_ddb_dict()
    profile = permission_profiles.create_permission_profile(profile_dict)

    return CreatePermissionProfileResponseContent(
        profile=VirtualDesktopPermissionProfile.from_ddb_dict(profile)
    )


def update_permission_profile(
    body, profile_id, user=None, token_info=None
):  # noqa: E501
    """update_permission_profile

    Update Permission Profile # noqa: E501

    :param update_permission_profile_request_content:
    :type update_permission_profile_request_content: dict | bytes
    :param profile_id:
    :type profile_id: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[UpdatePermissionProfileResponseContent, Tuple[UpdatePermissionProfileResponseContent, int], Tuple[UpdatePermissionProfileResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    request = UpdatePermissionProfileRequestContent.from_dict(body)
    profile = request.profile

    if profile_id != profile.profile_id:
        raise api_exceptions.BadRequestException(
            f"Profile ID: {profile_id} does not match the permission profile to update: {profile.profile_id}"
        )

    try:
        _existing_profile_dict = permission_profiles.get_permission_profile(
            profile_id=profile_id
        )
    except res_exceptions.PermissionProfileNotFound:
        raise api_exceptions.NotFoundException(
            f"Profile ID: {profile_id} does not exist"
        )

    profile_dict = profile.to_ddb_dict()
    profile_dict = permission_profiles.update_permission_profile(profile_dict)

    return UpdatePermissionProfileResponseContent(
        profile=VirtualDesktopPermissionProfile.from_ddb_dict(profile_dict)
    )


def delete_permission_profile(profile_id, user=None, token_info=None):  # noqa: E501
    """delete_permission_profile

    Delete Permission Profile # noqa: E501

    :param profile_id:
    :type profile_id: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[DeletePermissionProfileResponseContent, Tuple[DeletePermissionProfileResponseContent, int], Tuple[DeletePermissionProfileResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    try:
        permission_profiles.delete_permission_profile(profile_id)
        return DeletePermissionProfileResponseContent(success=True)
    except res_exceptions.PermissionProfileNotFound:
        raise api_exceptions.NotFoundException(message="Permission profile not found")
    except Exception as e:
        raise api_exceptions.InternalServiceException(message=str(e))


def list_session_permissions(
    res_session_id, next_token=None, user=None, token_info=None
):  # noqa: E501
    """list_session_permissions

    Get a list of session permissions # noqa: E501

    :param res_session_id: Filter by resSessionId
    :type res_session_id: str
    :param next_token: Pagination token for next page
    :type next_token: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListSessionPermissionsResponseContent, Tuple[ListSessionPermissionsResponseContent, int], Tuple[ListSessionPermissionsResponseContent, int, Dict[str, str]]
    """

    if not accounts.is_active_admin(user):
        try:
            res_sessions.get_session(owner=user, session_id=res_session_id)
        except Exception as e:
            raise api_exceptions.BadRequestException(
                message=f"Only session owner can request to list_session_permissions for session {res_session_id}"
            )

    permissions, response_next_token = res_session_permissions.list_session_permissions(
        session_id=res_session_id, next_token=next_token
    )

    permissions = [
        VirtualDesktopSessionPermission.from_ddb_dict(permission)
        for permission in permissions
    ]

    return ListSessionPermissionsResponseContent(
        listing=permissions, next_token=response_next_token
    )


def list_shared_permissions(
    next_token=None,
    username=None,
    state=None,
    base_os=None,
    session_name=None,
    date_range_key=None,
    after=None,
    before=None,
    user=None,
    token_info=None,
):  # noqa: E501
    """list_shared_permissions

    Get a list of shared permissions # noqa: E501

    :param next_token: Pagination token for next page
    :type next_token: str
    :param username: Username of the shared permissions
    :type username: str
    :param state: Filter by state
    :type state: str
    :param base_os: Filter by baseOs
    :type base_os: str
    :param session_name: Filter by sessionName
    :type session_name: str
    :param date_range_key: The attribute name to filter on for date range
    :type date_range_key: str
    :param after: Start of the date range
    :type after: str
    :param before: End of the date range
    :type before: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListSharedPermissionsResponseContent, Tuple[ListSharedPermissionsResponseContent, int], Tuple[ListSharedPermissionsResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        if username and username != user:
            raise OAuthProblem(
                "Non admin user cannot list shared permissions of other users"
            )
    if not username:
        username = user

    validate_date_range_filter(date_range_key, after, before)

    permissions, response_next_token = res_session_permissions.list_session_permissions(
        username=username,
        state=state,
        base_os=base_os,
        session_name=session_name,
        date_range_key=date_range_key,
        after=after,
        before=before,
        next_token=next_token,
    )

    permissions = [
        VirtualDesktopSessionPermission.from_ddb_dict(permission)
        for permission in permissions
    ]

    return ListSharedPermissionsResponseContent(
        listing=permissions, next_token=response_next_token
    )


def update_session_permissions(body=None, user=None, token_info=None):  # noqa: E501
    """update_session_permissions

    Get a list of session permissions # noqa: E501

    :param update_session_permissions_request_content:
    :type update_session_permissions_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: dict
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[UpdateSessionPermissionsResponseContent, Tuple[UpdateSessionPermissionsResponseContent, int], Tuple[UpdateSessionPermissionsResponseContent, int, Dict[str, str]]
    """
    request = UpdateSessionPermissionsRequestContent.from_dict(body)
    request.create = request.create if request.create is not None else []
    request.update = request.update if request.update is not None else []
    request.delete = request.delete if request.delete is not None else []

    if not accounts.is_active_admin(user):
        for permission in request.create + request.delete + request.update:
            if user != permission.idea_session_owner:
                raise api_exceptions.BadRequestException(
                    message=f"INVALID PARAMS. Can update permission for session owned by user only, Error trying to retrive session: {permission.idea_session_id} with user: {user}"
                )

    is_valid, request = validate_update_session_permission_request(request)

    if not is_valid:
        raise api_exceptions.BadRequestException(
            message=UPDATE_SESSION_PERMISSION_INVALID_REQUEST_ERROR_MESSAGE
        )

    for permission in request.create:
        try:
            existing_session_permission_dict = (
                res_session_permissions.get_session_permission(
                    session_id=permission.idea_session_id, user=permission.actor_name
                )
            )
            if existing_session_permission_dict:
                raise api_exceptions.BadRequestException(
                    f"Session permission with session_id {permission.idea_session_id} and actor_name {permission.actor_name} already exists."
                )
        except res_exceptions.SessionPermissionsNotFound:
            pass

    for permission in request.update + request.delete:
        try:
            _existing_session_permission_dict = (
                res_session_permissions.get_session_permission(
                    session_id=permission.idea_session_id, user=permission.actor_name
                )
            )
        except res_exceptions.SessionPermissionsNotFound:
            raise api_exceptions.BadRequestException(
                f"Session permission with session_id {permission.idea_session_id} and actor_name {permission.actor_name} does not exist."
            )

    permissions_to_create = [permission.to_ddb_dict() for permission in request.create]
    permissions_to_update = [permission.to_ddb_dict() for permission in request.update]
    permissions_to_delete = [permission.to_ddb_dict() for permission in request.delete]

    permissions = res_session_permissions.update_permissions_for_sessions(
        permissions_to_create, permissions_to_update, permissions_to_delete
    )
    permission_objects = [
        VirtualDesktopSessionPermission.from_ddb_dict(permission)
        for permission in permissions
    ]
    return UpdateSessionPermissionsResponseContent(permissions=permission_objects)


def list_sessions(
    state=None,
    base_os=None,
    session_name=None,
    stack_id=None,
    date_range_key=None,
    after=None,
    before=None,
    next_token=None,
    owner=None,
    user=None,
    token_info=None,
):  # noqa: E501
    """list_sessions

    Get a list of sessions # noqa: E501

    :param state: Filter by state
    :type state: str
    :param base_os: Filter by baseOs
    :type base_os: str
    :param session_name: Filter by sessionName
    :type session_name: str
    :param stack_id: Filter by stackId
    :type stack_id: str
    :param date_range_key: The attribute name to filter on for date range
    :type date_range_key: str
    :param after: Start of the date range
    :type after: str
    :param before: End of the date range
    :type before: str
    :param next_token: Pagination token for next page
    :param owner: Filter by owner
    :type next_token: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[ListSessionsResponseContent, Tuple[ListSessionsResponseContent, int], Tuple[ListSessionsResponseContent, int, Dict[str, str]]
    """
    validate_date_range_filter(date_range_key, after, before)

    sessions, response_next_token = res_sessions.list_sessions(
        user=user,
        state=state,
        base_os=base_os,
        session_name=session_name,
        stack_id=stack_id,
        date_range_key=date_range_key,
        after=after,
        before=before,
        next_token=next_token,
        owner=owner,
    )

    sessions = [VirtualDesktopSession.from_ddb_dict(session) for session in sessions]

    return ListSessionsResponseContent(listing=sessions, next_token=response_next_token)


def get_session(res_session_id, owner, user=None, token_info=None):  # noqa: E501
    """get_session

    Get details of a session # noqa: E501

    :param res_session_id: Session identifier
    :type res_session_id: str
    :param owner: Owner of the session
    :type owner: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[GetSessionResponseContent, Tuple[GetSessionResponseContent, int], Tuple[GetSessionResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        if owner != user:
            raise OAuthProblem("Non admin user cannot get session info of other users")

    try:
        session_dict = res_sessions.get_session(owner, res_session_id)
    except res_exceptions.UserSessionNotFound:
        raise api_exceptions.BadRequestException(
            f"Session with session_id {res_session_id} and owner {owner} does not exist."
        )

    return GetSessionResponseContent(
        session=VirtualDesktopSession.from_ddb_dict(session_dict)
    )
