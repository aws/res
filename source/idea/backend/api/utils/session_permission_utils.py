#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List

from datamodel.models.virtual_desktop_session_permission import VirtualDesktopSessionPermission
from datamodel.models.backend.update_session_permissions_request_content import (
    UpdateSessionPermissionsRequestContent,
)

from res.resources import sessions
from res.utils.string_utils import INVALID_ACTOR_NAME_MESSAGE, validate_actor_name

UPDATE_SESSION_PERMISSION_INVALID_REQUEST_ERROR_MESSAGE = (
    "Invalid request. No session permission modified."
)

def validate_update_session_permission_request(
    request: UpdateSessionPermissionsRequestContent,
) -> tuple[bool, UpdateSessionPermissionsRequestContent]:
    is_valid_request = True
    if request.create and len(request.create) > 0:
        for permission in request.create:
            session = sessions.get_session_if_owner(
                username=permission.idea_session_owner,
                res_session_id=permission.idea_session_id,
            )
            is_valid, message = _validate_session_for_session_permission_request(
                session
            )
            if not is_valid:
                permission.failure_reason = message
            is_valid_request = is_valid_request and is_valid

    if request.update and len(request.update) > 0:
        for permission in request.update:
            session = sessions.get_session_if_owner(
                username=permission.idea_session_owner,
                res_session_id=permission.idea_session_id,
            )
            is_valid, message = _validate_session_for_session_permission_request(
                session
            )
            if not is_valid:
                permission.failure_reason = message
            is_valid_request = is_valid_request and is_valid

    """
    for permission in request.delete:
        pass
    """

    if is_valid_request:
        is_valid, message = _validate_actors_for_session_permission_requests(
            request.create + request.update + request.delete
        )
        is_valid_request = is_valid_request and is_valid

    if not is_valid_request:
        for permission in request.create + request.update + request.delete:
            if not permission.failure_reason:
                permission.failure_reason = (
                    UPDATE_SESSION_PERMISSION_INVALID_REQUEST_ERROR_MESSAGE
                )
    return is_valid_request, request


def _validate_actors_for_session_permission_requests(
    session_permissions: List[VirtualDesktopSessionPermission],
) -> tuple[bool, str]:
    if not session_permissions:
        return False, "Invalid session_permissions"

    actors_seen = set()
    duplicate_actors = set()
    invalid_actor_count = 0
    is_valid = True
    for session_permission in session_permissions:
        actor_name = session_permission.actor_name
        try:
            validate_actor_name(actor_name)
        except ValueError:
            invalid_actor_count += 1
            is_valid = False
            continue
        if actor_name not in actors_seen:
            actors_seen.add(actor_name)
        else:
            duplicate_actors.add(actor_name)
            is_valid = False

    message = ""
    if invalid_actor_count:
        message = f"{invalid_actor_count} actor name(s) contain invalid characters. {INVALID_ACTOR_NAME_MESSAGE}"
    if duplicate_actors:
        dup_msg = f"actors: {duplicate_actors} not unique"
        message = f"{message} {dup_msg}" if message else dup_msg
    return is_valid, message


def _validate_session_for_session_permission_request(session: Any) -> tuple[bool, str]:
    if session is None:
        return False, "Invalid session"
    if session["base_os"] == "windows":
        return (
            False,
            "Windows sessions do not support sessions permissions for OpenLDAP",
        )
    return True, ""
