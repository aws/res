#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""
Per-operation scope authorization for the backend Lambda.

Smithy operation tags do not propagate to the generated Python server-side
code, so the read/write scope each operation requires is tracked here and
checked by controllers via ``enforce_scope``.
"""
from __future__ import annotations

import os
from functools import lru_cache

from connexion.exceptions import OAuthProblem
from res.constants import (  # type: ignore
    ENVIRONMENT_NAME_KEY,
    MODULE_ID_CLUSTER_MANAGER,
    MODULE_ID_VDC,
)
from res.resources import cluster_settings  # type: ignore
from res.utils import aws_utils, logging_utils  # type: ignore

logger = logging_utils.get_logger(__name__)

# operationId -> required scope ("read" or "write"). Entries added as operations are migrated.
OPERATION_SCOPES: dict[str, str] = {
    "batch_create_session": "write",
    "list_sessions": "read",
    "batch_start_session": "write",
    "batch_stop_session": "write",
    "batch_delete_session": "write",
    "update_session_permissions": "write",
    "list_software_stacks": "read",
    "get_software_stack": "read",
    "create_software_stack": "write",
    "update_software_stack": "write",
    "delete_software_stack": "write",
    "get_permission_profile": "read",
    "create_permission_profile": "write",
    "delete_permission_profile": "write",
}

# Module IDs whose Cognito clients are permitted to invoke any scoped operation above via a service token.
ALLOWED_SERVICE_MODULES: set[str] = {MODULE_ID_CLUSTER_MANAGER, MODULE_ID_VDC}


@lru_cache
def _resolve_client_id(module_id: str) -> str:
    """Resolve the Cognito client_id for a module from cluster_settings + Secrets Manager.
    """
    try:
        arn = cluster_settings.get_setting(f"{module_id}.client_id")
        return aws_utils.get_secret_string(arn)
    except Exception as e:
        logger.error(
            f"Failed to resolve client_id for module {module_id}: {e}",
            exc_info=True,
        )
        raise OAuthProblem("Service configuration error")


def check_app_client_token(token_info: dict, operation_id: str) -> bool:
    """Return True if ``token_info`` is an app-client (service) token, after enforcing scope.

    Detecting an app-client token (presence of ``scope``) and validating it
    via :func:`enforce_scope`. User-issued tokens are passed through unchanged
    so the caller can keep applying its normal user-based authorization.
    """
    is_app_client = bool(token_info and "scope" in token_info)
    if is_app_client:
        enforce_scope(token_info, operation_id)
    return is_app_client


def enforce_scope(token_info: dict, operation_id: str) -> None:
    """
    Verify the service token has the required scope for the operation and was
    issued to a permitted service client.

    Should only be invoked for service-token requests; the token must carry
    ``{environment_name}-vdc/{read|write}`` matching the operation's required
    scope, and ``token_info["uid"]`` (the issuing Cognito client_id) must
    belong to a module in ``ALLOWED_SERVICE_MODULES``.

    :raises OAuthProblem: token does not carry the required scope,
        operation_id is not registered, or the client_id is not allowed.
    """
    if not token_info or "scope" not in token_info:
        raise OAuthProblem("Insufficient scope")

    required = OPERATION_SCOPES.get(operation_id)
    if required is None:
        raise OAuthProblem("Insufficient scope")

    expected = f"{os.environ[ENVIRONMENT_NAME_KEY]}-{MODULE_ID_VDC}/{required}"
    if expected not in token_info["scope"]:
        raise OAuthProblem("Insufficient scope")

    allowed_client_ids = {_resolve_client_id(m) for m in ALLOWED_SERVICE_MODULES}
    if token_info.get("uid") not in allowed_client_ids:
        raise OAuthProblem("Unauthorized client")
