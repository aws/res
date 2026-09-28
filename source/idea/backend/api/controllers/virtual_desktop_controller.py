#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from connexion.exceptions import OAuthProblem
import uuid
import os

from res import exceptions as res_exceptions  # type: ignore

from api import exceptions as api_exceptions
from api.auth import check_app_client_token
from datamodel.models.batch_create_session_failure import BatchCreateSessionFailure  # noqa: E501
from datamodel.models.batch_create_session_request_content import BatchCreateSessionRequestContent  # noqa: E501
from datamodel.models.batch_create_session_response_content import BatchCreateSessionResponseContent  # noqa: E501
from datamodel.models.backend.batch_delete_session_request_content import BatchDeleteSessionRequestContent  # noqa: E501
from datamodel.models.backend.batch_delete_session_response_content import BatchDeleteSessionResponseContent  # noqa: E501
from datamodel.models.backend.batch_delete_session_failure import BatchDeleteSessionFailure  # noqa: E501
from datamodel.models.backend.batch_start_session_request_content import BatchStartSessionRequestContent  # noqa: E501
from datamodel.models.backend.batch_start_session_response_content import BatchStartSessionResponseContent  # noqa: E501
from datamodel.models.backend.batch_start_session_failure import BatchStartSessionFailure  # noqa: E501
from datamodel.models.backend.batch_stop_session_request_content import BatchStopSessionRequestContent  # noqa: E501
from datamodel.models.backend.batch_stop_session_response_content import BatchStopSessionResponseContent  # noqa: E501
from datamodel.models.backend.batch_stop_session_failure import BatchStopSessionFailure  # noqa: E501
from datamodel.models.backend.batch_reboot_session_request_content import BatchRebootSessionRequestContent  # noqa: E501
from datamodel.models.backend.batch_reboot_session_response_content import BatchRebootSessionResponseContent  # noqa: E501
from datamodel.models.backend.batch_reboot_session_failure import BatchRebootSessionFailure  # noqa: E501
from datamodel.models.backend.batch_get_session_screenshot_request_content import BatchGetSessionScreenshotRequestContent  # noqa: E501
from datamodel.models.backend.batch_get_session_screenshot_response_content import BatchGetSessionScreenshotResponseContent  # noqa: E501
from datamodel.models.backend.batch_get_session_screenshot_failure import BatchGetSessionScreenshotFailure  # noqa: E501
from datamodel.models.virtual_desktop_session_screenshot import VirtualDesktopSessionScreenshot  # noqa: E501
from datamodel.models.backend.batch_operation_error_code import BatchOperationErrorCode  # noqa: E501
from datamodel.models.delete_permission_profile_response_content import (
    DeletePermissionProfileResponseContent,
)  # noqa: E501
from datamodel.models.update_permission_profile_response_content import (
    UpdatePermissionProfileResponseContent,
)  # noqa: E501
from datamodel.models.update_permission_profile_request_content import (
    UpdatePermissionProfileRequestContent,
)  # noqa: E501
from datamodel.models.backend.create_software_stack_from_session_request_content import (
    CreateSoftwareStackFromSessionRequestContent,
)  # noqa: E501
from datamodel.models.backend.create_software_stack_from_session_response_content import (
    CreateSoftwareStackFromSessionResponseContent,
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
from datamodel.models.backend.update_session_permissions_request_content import (
    UpdateSessionPermissionsRequestContent,
)  # noqa: E501
from datamodel.models.backend.update_session_permissions_response_content import (
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
from datamodel.models.get_session_connection_request_content import GetSessionConnectionRequestContent  # noqa: E501
from datamodel.models.get_session_connection_response_content import GetSessionConnectionResponseContent  # noqa: E501
from datamodel.models.virtual_desktop_session_connection import VirtualDesktopSessionConnection  # noqa: E501
from datamodel.models.backend.virtual_desktop_session_state import VirtualDesktopSessionState  # noqa: E501
from datamodel.models.get_session_response_content import (
    GetSessionResponseContent,
)
from datamodel.models.update_session_request_content import (
    UpdateSessionRequestContent,
)  # noqa: E501
from datamodel.models.update_session_response_content import (
    UpdateSessionResponseContent,
)  # noqa: E501
from datamodel.models.virtual_desktop_session import VirtualDesktopSession

from api.utils.software_stack_utils import (
    validate_software_stack_fields,
    ami_name_exists,
)
from api.utils.virtual_desktop_controller_utils import (
    validate_date_range_filter,
)
from api.utils.session_permission_utils import (
    validate_update_session_permission_request,
    UPDATE_SESSION_PERMISSION_INVALID_REQUEST_ERROR_MESSAGE,
)
from res.resources.session_permissions import enrich_and_filter_permissions_with_session_data
from res.resources import (
    accounts,
    ad_automation,
    software_stacks,
    permission_profiles,
    projects as res_projects,
    session_permissions as res_session_permissions,
    sessions as res_sessions,
    vdi_management,
)
from res.clients.dcv_session_manager import dcv_session_manager_client
from api.utils.session_utils import (
    validate_update_session_request,
)
from res.utils import logging_utils
from api.utils import session_utils

logger = logging_utils.get_logger(__name__)


def batch_create_session(body, user=None, token_info=None):  # noqa: E501
    """batch_create_session

    Batch Create Sessions # noqa: E501

    :param batch_create_session_request_content:
    :type batch_create_session_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[BatchCreateSessionResponseContent, Tuple[BatchCreateSessionResponseContent, int], Tuple[BatchCreateSessionResponseContent, int, Dict[str, str]]
    """
    is_app_client = check_app_client_token(token_info, "batch_create_session")

    request = BatchCreateSessionRequestContent.from_dict(body)
    validated_sessions_list, unsuccessful_list = (
        session_utils.validate_batch_create_sessions(request.sessions, user, is_app_client=is_app_client)
    )

    dry_run_enabled = os.environ.get("DRY_RUN_ENABLED", "false").lower() == "true"
    if dry_run_enabled:
        logger.info(
            f"DRY RUN MODE ENABLED - Batch Create Session count: {len(validated_sessions_list)}"
        )
        return BatchCreateSessionResponseContent(
            successful_list=validated_sessions_list, unsuccessful_list=unsuccessful_list
        )

    successful_list = []
    for session in validated_sessions_list:
        try:
            session = session_utils.complete_create_session_request(session, user)
            session_ddb = vdi_management.create_virtual_desktop(session.to_ddb_dict())
            session = VirtualDesktopSession.from_ddb_dict(session_ddb)

            if not session.failure_reason:
                logger.info(
                    f"session created for user: {session.owner} with session name: {session.name} and idea_session_id: {session.idea_session_id}"
                )
                successful_list.append(session)
            else:
                failure_code = session_ddb.get("failure_code", res_exceptions.FAILURE_CODE_INTERNAL_SERVICE)
                error_code = (
                    BatchOperationErrorCode.BADREQUESTEXCEPTION
                    if failure_code == res_exceptions.FAILURE_CODE_BAD_REQUEST
                    else BatchOperationErrorCode.INTERNALSERVICEEXCEPTION
                )
                unsuccessful_list.append(
                    BatchCreateSessionFailure(
                        session=session,
                        error_code=error_code,
                        message=session.failure_reason,
                    )
                )
        except Exception as e:
            logger.error(f"Unexpected error creating session: {e}", exc_info=True)
            unsuccessful_list.append(
                BatchCreateSessionFailure(
                    session=session,
                    error_code=BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
                    message=str(e),
                )
            )

    return BatchCreateSessionResponseContent(
        successful_list=successful_list, unsuccessful_list=unsuccessful_list
    )


def batch_reboot_session(body, user=None, token_info=None):  # noqa: E501
    """batch_reboot_session

    Batch Reboot Sessions # noqa: E501

    :param batch_reboot_session_request_content:
    :type batch_reboot_session_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[BatchRebootSessionResponseContent, Tuple[BatchRebootSessionResponseContent, int], Tuple[BatchRebootSessionResponseContent, int, Dict[str, str]]
    """

    request = BatchRebootSessionRequestContent.from_dict(body)
    validated_sessions_list, unsuccessful_list = session_utils.validate_batch_reboot_sessions(request.sessions, user)

    if not validated_sessions_list:
        return BatchRebootSessionResponseContent(successful_list=[], unsuccessful_list=unsuccessful_list)

    dry_run_enabled = os.environ.get('DRY_RUN_ENABLED', 'false').lower() == 'true'
    if dry_run_enabled:
        session_ids = [s.get('idea_session_id') for s in validated_sessions_list]
        logger.info(f'DRY RUN MODE ENABLED - Batch Reboot Session count: {len(validated_sessions_list)}, session_ids: {session_ids}')
        return BatchRebootSessionResponseContent(
            successful_list=[VirtualDesktopSession.from_ddb_dict(s) for s in validated_sessions_list],
            unsuccessful_list=unsuccessful_list,
        )

    success_list, fail_list = vdi_management.reboot_sessions(validated_sessions_list)

    successful = [VirtualDesktopSession.from_ddb_dict(s) for s in success_list]
    for s in fail_list:
        unsuccessful_list.append(BatchRebootSessionFailure(
            session=VirtualDesktopSession.from_ddb_dict(s),
            error_code=BatchOperationErrorCode[s['failure_code']] if 'failure_code' in s else BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
            message=s.get('failure_reason', 'Reboot session failed')
        ))

    return BatchRebootSessionResponseContent(successful_list=successful, unsuccessful_list=unsuccessful_list)


def batch_delete_session(body, user=None, token_info=None):  # noqa: E501
    """batch_delete_session

    Batch Delete Sessions # noqa: E501

    :param batch_delete_session_request_content:
    :type batch_delete_session_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[BatchDeleteSessionResponseContent, Tuple[BatchDeleteSessionResponseContent, int], Tuple[BatchDeleteSessionResponseContent, int, Dict[str, str]]
    """
    is_app_client = check_app_client_token(token_info, "batch_delete_session")

    request = BatchDeleteSessionRequestContent.from_dict(body)
    validated_sessions_list, unsuccessful_list = session_utils.validate_batch_delete_sessions(
        request.sessions, user, is_app_client=is_app_client
    )

    if not validated_sessions_list:
        return BatchDeleteSessionResponseContent(successful_list=[], unsuccessful_list=unsuccessful_list)

    dry_run_enabled = os.environ.get('DRY_RUN_ENABLED', 'false').lower() == 'true'
    if dry_run_enabled:
        session_ids = [s.idea_session_id for s in validated_sessions_list]
        logger.info(f'DRY RUN MODE ENABLED - Batch Delete Session count: {len(validated_sessions_list)}, session_ids: {session_ids}')
        return BatchDeleteSessionResponseContent(successful_list=validated_sessions_list, unsuccessful_list=unsuccessful_list)

    sessions_ddb = [session.to_ddb_dict() for session in validated_sessions_list]
    try:
        success_list, fail_list = vdi_management.terminate_sessions(sessions_ddb)
    except Exception:
        session_ids = [s.get('idea_session_id') for s in sessions_ddb]
        logger.error(f"Failed to delete sessions: {session_ids}", exc_info=True)
        raise

    successful = [VirtualDesktopSession.from_ddb_dict(s) for s in success_list]
    for s in fail_list:
        unsuccessful_list.append(BatchDeleteSessionFailure(
            session=VirtualDesktopSession.from_ddb_dict(s),
            error_code=BatchOperationErrorCode[s['failure_code']] if 'failure_code' in s else BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
            message=s.get('failure_reason', 'Delete session failed')
        ))

    return BatchDeleteSessionResponseContent(successful_list=successful, unsuccessful_list=unsuccessful_list)


def batch_start_session(body, user=None, token_info=None):  # noqa: E501
    """batch_start_session

    Batch Start Sessions # noqa: E501

    :param batch_start_session_request_content:
    :type batch_start_session_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[BatchStartSessionResponseContent, Tuple[BatchStartSessionResponseContent, int], Tuple[BatchStartSessionResponseContent, int, Dict[str, str]]
    """

    is_app_client = check_app_client_token(token_info, "batch_start_session")

    request = BatchStartSessionRequestContent.from_dict(body)
    validated_sessions_list, unsuccessful_list = session_utils.validate_batch_start_sessions(
        request.sessions, user, is_app_client=is_app_client
    )

    if not validated_sessions_list:
        return BatchStartSessionResponseContent(successful_list=[], unsuccessful_list=unsuccessful_list)

    dry_run_enabled = os.environ.get('DRY_RUN_ENABLED', 'false').lower() == 'true'
    if dry_run_enabled:
        session_ids = [s.idea_session_id for s in validated_sessions_list]
        logger.info(f'DRY RUN MODE ENABLED - Batch Start Session count: {len(validated_sessions_list)}, session_ids: {session_ids}')
        return BatchStartSessionResponseContent(successful_list=validated_sessions_list, unsuccessful_list=unsuccessful_list)

    sessions_ddb = [session.to_ddb_dict() for session in validated_sessions_list]
    try:
        success_list, fail_list = vdi_management.start_sessions(sessions_ddb)
    except Exception:
        session_ids = [s.get('idea_session_id') for s in sessions_ddb]
        logger.error(f"Failed to start sessions: {session_ids}", exc_info=True)
        raise

    successful = [VirtualDesktopSession.from_ddb_dict(s) for s in success_list]
    for s in fail_list:
        unsuccessful_list.append(BatchStartSessionFailure(
            session=VirtualDesktopSession.from_ddb_dict(s),
            error_code=BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
            message=s.get('failure_reason', 'Start session failed')
        ))

    return BatchStartSessionResponseContent(successful_list=successful, unsuccessful_list=unsuccessful_list)


def batch_get_session_screenshot(body, user=None, token_info=None):  # noqa: E501
    """batch_get_session_screenshot

    Batch Get Session Screenshots # noqa: E501

    :param batch_get_session_screenshot_request_content:
    :type batch_get_session_screenshot_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[BatchGetSessionScreenshotResponseContent, Tuple[BatchGetSessionScreenshotResponseContent, int], Tuple[BatchGetSessionScreenshotResponseContent, int, Dict[str, str]]
    """

    screenshots = BatchGetSessionScreenshotRequestContent.from_dict(body).screenshots

    dry_run_enabled = os.environ.get('DRY_RUN_ENABLED', 'false').lower() == 'true'
    if dry_run_enabled:
        session_ids = [s.idea_session_id for s in screenshots]
        logger.info(f'DRY RUN MODE ENABLED - Batch Get Session Screenshot count: {len(screenshots)}, session_ids: {session_ids}')
        return BatchGetSessionScreenshotResponseContent(successful_list=screenshots, unsuccessful_list=[])

    session_ids = [s.idea_session_id for s in screenshots]
    try:
        response = dcv_session_manager_client.get_session_screenshots(session_ids, requester=user)
    except Exception:
        logger.error(f"Failed to get session screenshots: {session_ids}", exc_info=True)
        raise

    successful_list = [VirtualDesktopSessionScreenshot.from_ddb_dict(entry) for entry in response.get('successful_list') or []]
    unsuccessful_list = []
    for entry in response.get('unsuccessful_list') or []:
        failure_reason = entry.get('failure_reason', 'Get session screenshot failed')
        unsuccessful_list.append(BatchGetSessionScreenshotFailure(
            screenshot=VirtualDesktopSessionScreenshot.from_ddb_dict(entry),
            error_code=BatchOperationErrorCode.FORBIDDENEXCEPTION if failure_reason == res_session_permissions.ACCESS_DENIED_MSG else BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
            message=failure_reason
        ))

    return BatchGetSessionScreenshotResponseContent(successful_list=successful_list, unsuccessful_list=unsuccessful_list)


def batch_stop_session(body, user=None, token_info=None):  # noqa: E501
    """batch_stop_session

    Batch Stop Sessions # noqa: E501

    :param batch_stop_session_request_content:
    :type batch_stop_session_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[BatchStopSessionResponseContent, Tuple[BatchStopSessionResponseContent, int], Tuple[BatchStopSessionResponseContent, int, Dict[str, str]]
    """
    is_app_client = check_app_client_token(token_info, "batch_stop_session")

    request = BatchStopSessionRequestContent.from_dict(body)
    validated_sessions_list, unsuccessful_list = session_utils.validate_batch_stop_sessions(
        request.sessions, user, is_app_client=is_app_client
    )

    if not validated_sessions_list:
        return BatchStopSessionResponseContent(successful_list=[], unsuccessful_list=unsuccessful_list)

    dry_run_enabled = os.environ.get('DRY_RUN_ENABLED', 'false').lower() == 'true'
    if dry_run_enabled:
        session_ids = [s.idea_session_id for s in validated_sessions_list]
        logger.info(f'DRY RUN MODE ENABLED - Batch Stop Session count: {len(validated_sessions_list)}, session_ids: {session_ids}')
        return BatchStopSessionResponseContent(successful_list=validated_sessions_list, unsuccessful_list=unsuccessful_list)

    sessions_ddb = [session.to_ddb_dict() for session in validated_sessions_list]
    try:
        success_list, fail_list = vdi_management.stop_sessions(sessions_ddb)
    except Exception:
        session_ids = [s.get('idea_session_id') for s in sessions_ddb]
        logger.error(f"Failed to stop sessions: {session_ids}", exc_info=True)
        raise

    successful = [VirtualDesktopSession.from_ddb_dict(s) for s in success_list]
    for s in fail_list:
        unsuccessful_list.append(BatchStopSessionFailure(
            session=VirtualDesktopSession.from_ddb_dict(s),
            error_code=BatchOperationErrorCode[s['failure_code']] if 'failure_code' in s else BatchOperationErrorCode.INTERNALSERVICEEXCEPTION,
            message=s.get('failure_reason', 'Stop session failed')
        ))

    return BatchStopSessionResponseContent(successful_list=successful, unsuccessful_list=unsuccessful_list)


def create_software_stack_from_session(body, user=None, token_info=None):  # noqa: E501
    """create_software_stack_from_session

    Create a software stack from an existing session # noqa: E501

    :param create_software_stack_from_session_request_content:
    :type create_software_stack_from_session_request_content: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[CreateSoftwareStackFromSessionResponseContent, Tuple[CreateSoftwareStackFromSessionResponseContent, int], Tuple[CreateSoftwareStackFromSessionResponseContent, int, Dict[str, str]]
    """
    if not accounts.is_active_admin(user):
        raise OAuthProblem("Unauthorized user")

    request = CreateSoftwareStackFromSessionRequestContent.from_dict(body)
    session = request.session
    software_stack = request.software_stack

    if not session.owner:
        raise api_exceptions.BadRequestException(message="session.owner is required")
    if not session.idea_session_id:
        raise api_exceptions.BadRequestException(message="session.idea_session_id is required")

    # Validate session exists
    try:
        existing_session = res_sessions.get_session(
            owner=session.owner, session_id=session.idea_session_id
        )
    except res_exceptions.UserSessionNotFound:
        raise api_exceptions.BadRequestException(
            message=f"Session {session.idea_session_id} not found for owner {session.owner}"
        )

    # Validate session is in READY state
    session_state = existing_session.get("state")
    if session_state != VirtualDesktopSessionState.READY:
        raise api_exceptions.BadRequestException(
            message=f"Session must be in READY state to create a software stack. Current state: {session_state}"
        )

    dry_run_enabled = os.environ.get('DRY_RUN_ENABLED', 'false').lower() == 'true'

    # Validate software stack fields
    validated_stack, is_valid = validate_software_stack_fields(software_stack)
    if not is_valid:
        raise api_exceptions.BadRequestException(
            message=f"Invalid software stack: {validated_stack.failure_reason}"
        )

    # Check AMI name uniqueness (AMI will be created from the session's instance)
    if ami_name_exists(software_stack.name):
        raise api_exceptions.BadRequestException(
            message="ami with the same name exists in this account"
        )

    if dry_run_enabled:
        logger.info(f'DRY RUN MODE ENABLED - CreateSoftwareStackFromSession for session {session.idea_session_id}')
        return CreateSoftwareStackFromSessionResponseContent(
            software_stack=software_stack
        )

    # Clear stale AD automation record so the VDI gets a fresh OTP on rejoin after reboot
    instance_id = existing_session.get("server", {}).get("instance_id", "")
    if instance_id:
        ad_automation.remove_ad_authorization([instance_id])

    created_stack = software_stacks.create_software_stack_from_session(
        session_id=session.idea_session_id,
        owner=session.owner,
        software_stack_dict=software_stack.to_ddb_dict(),
    )

    return CreateSoftwareStackFromSessionResponseContent(
        software_stack=VirtualDesktopSoftwareStack.from_ddb_dict(created_stack)
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
    is_app_client = check_app_client_token(token_info, "create_software_stack")
    if not is_app_client and not accounts.is_active_admin(user):
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
    is_app_client = check_app_client_token(token_info, "delete_software_stack")
    if not is_app_client and not accounts.is_active_admin(user):
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
    is_app_client = check_app_client_token(token_info, "list_software_stacks")
    is_admin = is_app_client or accounts.is_active_admin(user)

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
    is_app_client = check_app_client_token(token_info, "update_software_stack")
    if not is_app_client and not accounts.is_active_admin(user):
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
    is_app_client = check_app_client_token(token_info, "get_software_stack")

    try:
        stack = software_stacks.get_software_stack(
            base_os=base_os, stack_id=stack_id, get_project_details=True
        )
    except res_exceptions.SoftwareStackNotFound as e:
        raise api_exceptions.BadRequestException(str(e))

    if not is_app_client and not accounts.is_active_admin(user):
        user_projects = res_projects.get_user_projects(username=user)
        user_project_ids = {p.get("project_id") for p in user_projects}
        stack_project_ids = {p.get("project_id") for p in stack.get("projects", [])}
        if not user_project_ids & stack_project_ids:
            raise api_exceptions.BadRequestException(
                f"Software stack {stack_id} not found"
            )

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
    is_app_client = check_app_client_token(token_info, "create_permission_profile")
    if not is_app_client and not accounts.is_active_admin(user):
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
    is_app_client = check_app_client_token(token_info, "delete_permission_profile")
    if not is_app_client and not accounts.is_active_admin(user):
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

    page_permissions, response_next_token = res_session_permissions.list_session_permissions(
        username=username,
        date_range_key=date_range_key,
        after=after,
        before=before,
        next_token=next_token,
    )

    enriched_permissions = enrich_and_filter_permissions_with_session_data(
        page_permissions,
        state=state,
        base_os=base_os,
        session_name=session_name,
    )

    permissions = [
        VirtualDesktopSessionPermission.from_ddb_dict(permission)
        for permission in enriched_permissions
    ]

    return ListSharedPermissionsResponseContent(listing=permissions, next_token=response_next_token)


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
    is_app_client = check_app_client_token(token_info, "update_session_permissions")

    request = UpdateSessionPermissionsRequestContent.from_dict(body)
    request.create = request.create if request.create is not None else []
    request.update = request.update if request.update is not None else []
    request.delete = request.delete if request.delete is not None else []

    if not is_app_client and not accounts.is_active_admin(user):
        for permission in request.create + request.delete + request.update:
            if user != permission.idea_session_owner:
                raise api_exceptions.BadRequestException(
                    message=f"INVALID PARAMS. Can update permission for session owned by user only, Error trying to retrive session: {permission.idea_session_id} with user: {user}"
                )

    is_valid, request = validate_update_session_permission_request(request)

    if not is_valid:
        failure_reasons = [
            p.failure_reason
            for p in request.create + request.update + request.delete
            if p.failure_reason
        ]
        raise api_exceptions.BadRequestException(
            message="; ".join(failure_reasons)
            if failure_reasons
            else UPDATE_SESSION_PERMISSION_INVALID_REQUEST_ERROR_MESSAGE
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
    is_app_client = check_app_client_token(token_info, "list_sessions")

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
        is_app_client=is_app_client,
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

def get_session_connection(body, user=None, token_info=None):  # noqa: E501
    """get_session_connection

    Get connection information for a virtual desktop session # noqa: E501

    :param body:
    :type body: dict | bytes

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[GetSessionConnectionResponseContent, Tuple[GetSessionConnectionResponseContent, int], Tuple[GetSessionConnectionResponseContent, int, Dict[str, str]]
    """
    request = GetSessionConnectionRequestContent.from_dict(body)
    connection = request.connection

    # Authorization: user must be admin, session owner, or have shared permission
    if not accounts.is_active_admin(user):
        if connection.idea_session_owner != user:
            try:
                res_session_permissions.get_session_permission(connection.idea_session_id, user)
            except res_exceptions.SessionPermissionsNotFound:
                raise OAuthProblem("User does not have permission to access this session")

    try:
        session = res_sessions.get_session(connection.idea_session_owner, connection.idea_session_id)
    except res_exceptions.UserSessionNotFound:
        raise api_exceptions.BadRequestException(
            f"Session with session_id {connection.idea_session_id} and owner {connection.idea_session_owner} does not exist."
        )
    except Exception as e:
        logger.error(f"Failed to retrieve session {connection.idea_session_id}: {e}")
        raise api_exceptions.InternalServiceException(
            f"Error retrieving session {connection.idea_session_id}"
        )

    state = session.get("state")
    if state != VirtualDesktopSessionState.READY:
        raise api_exceptions.BadRequestException(
            f"Session {connection.idea_session_id} is not ready for connection. Current state: {state}"
        )

    dry_run_enabled = os.environ.get('DRY_RUN_ENABLED', 'false').lower() == 'true'
    if dry_run_enabled:
        logger.info(f'DRY RUN MODE ENABLED - GetSessionConnection for session: {connection.idea_session_id}, owner: {connection.idea_session_owner}')
        return GetSessionConnectionResponseContent(
            connection=VirtualDesktopSessionConnection(
                idea_session_id=connection.idea_session_id,
                idea_session_owner=connection.idea_session_owner,
                endpoint="dry-run-endpoint",
                web_url_path="dry-run-web-url-path",
                access_token="dry-run-access-token",
            )
        )

    try:
        connection_result = res_sessions.get_session_connection(
            session_id=connection.idea_session_id,
            owner=connection.idea_session_owner,
            username=user,
        )
    except res_exceptions.SettingNotFound as e:
        logger.error(f"Cluster configuration error for session {connection.idea_session_id}: {e}")
        raise api_exceptions.InternalServiceException(
            f"Connection gateway is not configured for session {connection.idea_session_id}"
        )
    except Exception as e:
        logger.error(f"Failed to get session connection data for session {connection.idea_session_id}: {e}")
        res_sessions.update_session_state(connection.idea_session_owner, connection.idea_session_id, "ERROR")
        raise api_exceptions.InternalServiceException(
            f"Error retrieving session connection data for session {connection.idea_session_id}"
        )

    return GetSessionConnectionResponseContent(
        connection=VirtualDesktopSessionConnection.from_dict(connection_result)
    )


def update_session(body, res_session_id, user=None, token_info=None):  # noqa: E501
    """update_session

    Update Session # noqa: E501

    :param update_session_request_content:
    :type update_session_request_content: dict | bytes
    :param res_session_id: Session identifier
    :type res_session_id: str

    :param user: The authenticated user information
    :type user: str
    :param token_info: The token information from authentication
    :type token_info: dict
    :rtype: Union[UpdateSessionResponseContent, Tuple[UpdateSessionResponseContent, int], Tuple[UpdateSessionResponseContent, int, Dict[str, str]]
    """

    request = UpdateSessionRequestContent.from_dict(body)
    session = request.session

    if not session or not session.owner or not session.idea_session_id:
        raise api_exceptions.BadRequestException(
            message="Session owner and idea_session_id are required in the request body."
        )

    if not accounts.is_active_admin(user) and user != session.owner:
        raise OAuthProblem(
            "Unauthorized user. Non Admin users can submit requests for themselves only"
        )

    dry_run_enabled = os.environ.get('DRY_RUN_ENABLED', 'false').lower() == 'true'
    if dry_run_enabled:
        logger.info(f'DRY RUN MODE ENABLED - Update Session Request Object: {session}')
        return { "session": session }

    try:
        old_session_dict = res_sessions.get_session(session.owner, res_session_id)
    except res_exceptions.UserSessionNotFound:
        raise api_exceptions.BadRequestException(
            f"Session {res_session_id} does not exist"
        )

    validate_update_session_request(session, old_session_dict)

    try:
        updated_session = res_sessions.update_session(
            session.to_ddb_dict(), old_session_dict
        )
    except res_exceptions.ServerNotFound as e:
        raise api_exceptions.BadRequestException(str(e))

    session_obj = VirtualDesktopSession.from_ddb_dict(updated_session)

    return UpdateSessionResponseContent(session=session_obj)

