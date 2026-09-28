#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import logging
from functools import cmp_to_key
from typing import Any, Dict, Optional

import pytest
from requests.exceptions import HTTPError
from res.constants import CLUSTER_ADMIN_USERNAME  # type: ignore
from res.resources.schedules import DayOfWeek  # type: ignore
from res.utils.memory_utils import mib_to_gb  # type: ignore
from res.utils.model_utils import remove_none_values  # type: ignore

from ideadatamodel import UpdateModuleSettingsRequest  # type: ignore
from tests.integration.framework.client.api_client import (
    ApiClient,
    BatchCreateSessionRequestContent,
    BatchDeleteSessionRequestContent,
    UpdateSessionRequestContent,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.session_utils import (
    is_insufficient_capacity,
    wait_for_deleting_session,
    wait_for_launching_session,
)

ListAllowedInstanceTypesForSessionRequestContent = get_backend_model_class(
    "list_allowed_instance_types_for_session_request_content",
    "ListAllowedInstanceTypesForSessionRequestContent",
)
VirtualDesktopSession_ = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
VirtualDesktopSoftwareStack_ = get_backend_model_class(
    "virtual_desktop_software_stack", "VirtualDesktopSoftwareStack"
)

logger = logging.getLogger(__name__)


def compare_instance_types(a: Dict[str, Any], b: Dict[str, Any]) -> int:
    a_instance_family: str = a.get("InstanceType", "").split(".")[0]
    b_instance_family: str = b.get("InstanceType", "").split(".")[0]
    if a_instance_family == b_instance_family:
        # same instance family - sort in reverse memory order
        return (
            1
            if b.get("MemoryInfo", {}).get("SizeInMiB", 0)
            > a.get("MemoryInfo", {}).get("SizeInMiB", 0)
            else -1
        )
    else:
        # diff instance family - return alphabetical
        return 1 if a_instance_family.lower() > b_instance_family.lower() else -1


def delete_session(api_client: ApiClient, session: Any) -> None:
    session_to_delete = VirtualDesktopSession_(
        idea_session_id=session.idea_session_id,
        owner=session.owner,
        force=True,
    )
    api_client.batch_delete_session(
        BatchDeleteSessionRequestContent(sessions=[session_to_delete])
    )
    wait_for_deleting_session(api_client, session)


def _wait_and_configure_session(
    api_client: ApiClient,
    session: Any,
) -> Any:
    """Wait for a session to reach READY, then disable its schedule."""
    try:
        session = wait_for_launching_session(api_client, session)
    except Exception as e:
        delete_session(api_client, session)
        raise e

    no_schedule = {"schedule_type": "NO_SCHEDULE"}
    session_dict = session.to_dict()
    session_dict["schedule"] = {day.value: no_schedule for day in DayOfWeek}
    session_dict.pop("software_stack", None)
    session_obj = VirtualDesktopSession_.from_dict(session_dict)
    update_request = UpdateSessionRequestContent(session=session_obj)
    api_client.update_session(
        session_id=session.idea_session_id, request_content=update_request
    )
    return session


def _prepare_session_dict(session: Any, software_stack: Any) -> Dict[str, Any]:
    """Build the base session dict with software stack and storage info."""
    session_dict: Dict[str, Any] = session.to_dict()

    session_dict["base_os"] = software_stack.base_os.value
    session_dict["software_stack_id"] = software_stack.stack_id

    if "server" not in session_dict or session_dict["server"] is None:
        session_dict["server"] = {}

    session_dict["server"]["root_volume_size"] = {
        "value": software_stack.min_storage.value,
        "unit": software_stack.min_storage.unit,
    }

    return session_dict


def create_session(
    session: Any,
    software_stack: Any,
    api_client: ApiClient,
) -> Optional[Any]:

    # Convert session to dict and recursively remove any fields with None values
    session_dict = remove_none_values(session.to_dict())

    session_obj = VirtualDesktopSession_.from_dict(session_dict)
    if session_obj.software_stack_id:
        logger.info(f"Session software_stack_id: {session_obj.software_stack_id}")

    request_content = ListAllowedInstanceTypesForSessionRequestContent(
        session=session_obj
    )

    allowed_instance_types_response = (
        api_client.list_allowed_instance_types_for_session(request_content)
    )

    allowed_instance_types = allowed_instance_types_response.listing  # type: ignore

    if not allowed_instance_types:
        pytest.skip(
            f"No allowed instance types are available for software stack {software_stack.name}"
        )

    allowed_instance_types = sorted(
        allowed_instance_types, key=cmp_to_key(compare_instance_types)
    )

    session_dict = _prepare_session_dict(session, software_stack)

    # Try different instance types smallest to largest, retrying on InsufficientInstanceCapacity errors.
    last_error = None
    for instance_type_info in reversed(allowed_instance_types):
        instance_type = instance_type_info.get("InstanceType", "")
        session_dict["server"]["instance_type"] = instance_type

        # Hibernation requires root volume >= storage + instance RAM.
        if session_dict.get("hibernation_enabled"):
            ram_mib = instance_type_info.get("MemoryInfo", {}).get("SizeInMiB", 0)
            session_dict["server"]["root_volume_size"] = {
                "value": software_stack.min_storage.value + mib_to_gb(ram_mib),
                "unit": software_stack.min_storage.unit,
            }

        try:
            session_to_send = VirtualDesktopSession_.from_dict(session_dict)
        except Exception as e:
            logger.warning(f"Failed to deserialize session dict, using raw dict: {e}")
            session_to_send = session_dict

        try:
            batch_response = api_client.batch_create_session(
                BatchCreateSessionRequestContent(sessions=[session_to_send])
            )
            if batch_response.unsuccessful_list:  # type: ignore[attr-defined]
                failure = batch_response.unsuccessful_list[0]  # type: ignore[attr-defined]
                if is_insufficient_capacity(failure.message):
                    logger.warning(
                        f"Insufficient capacity for {instance_type}, trying next instance type..."
                    )
                    last_error = HTTPError(failure.message)
                    continue
                raise HTTPError(failure.message)
            break
        except HTTPError as e:
            if is_insufficient_capacity(str(e)):
                last_error = e
                continue
            raise
    else:
        if last_error is not None and is_insufficient_capacity(str(last_error)):
            reason = (
                f"No EC2 capacity for software stack {software_stack.name} "
                f"(os={session_dict['base_os']}, "
                f"instance_type={session_dict['server']['instance_type']}): "
                f"{last_error}"
            )
            pytest.xfail(reason)
        raise last_error  # type: ignore[misc]

    session = batch_response.successful_list[0]  # type: ignore
    return _wait_and_configure_session(api_client, session)


def create_session_smart_retry(
    session: Any,
    software_stack: Any,
    api_client: ApiClient,
) -> Any:
    """Create a session without instance_type or subnet_id (smart retry handles selection)."""
    session_dict = _prepare_session_dict(session, software_stack)

    session_dict["server"].pop("instance_type", None)
    session_dict["server"].pop("subnet_id", None)

    session_to_send = VirtualDesktopSession_.from_dict(session_dict)

    batch_response = api_client.batch_create_session(
        BatchCreateSessionRequestContent(sessions=[session_to_send])
    )

    if batch_response.unsuccessful_list:  # type: ignore[attr-defined]
        failure = batch_response.unsuccessful_list[0]  # type: ignore[attr-defined]
        raise HTTPError(f"Smart retry session creation failed: {failure.message}")

    session = batch_response.successful_list[0]  # type: ignore
    return _wait_and_configure_session(api_client, session)


@pytest.fixture
def session(
    request: FixtureRequest,
    res_environment: ResEnvironment,
) -> Optional[Any]:
    """
    Fixture for setting up/tearing down the test project
    """
    session = request.param[0]
    project = request.getfixturevalue(request.param[1])
    software_stack = request.getfixturevalue(request.param[2])
    clientAuth = request.getfixturevalue(request.param[3])

    # The project fixture still returns a legacy (pydantic) Project. The new-model
    # session serializes `project` via to_dict(), which cannot serialize the legacy
    # object (it would drop to {} and lose project_id). Attach it by id instead.
    session.project = {"project_id": project.project_id}
    session.software_stack = software_stack
    session.base_os = software_stack.base_os
    session.software_stack_id = software_stack.stack_id

    # Append stack name to session name for easier identification
    # Use original param name to avoid mutation across parametrized runs
    original_name = request.param[0].name
    base_os = getattr(software_stack.base_os, "value", software_stack.base_os)
    arch = getattr(software_stack.architecture, "value", software_stack.architecture)
    session.name = f"{original_name}-{base_os}-{arch}"[:24]

    api_client = ApiClient(res_environment, clientAuth)

    session = create_session(session, software_stack, api_client)

    def tear_down() -> None:
        delete_session(api_client, session)

    request.addfinalizer(tear_down)

    return session


@pytest.fixture
def smart_retry_session(
    request: FixtureRequest,
    res_environment: ResEnvironment,
) -> Optional[Any]:
    """
    Fixture for creating a VDI session with smart retry enabled.
    Enables smart retry before session creation and disables it on teardown.
    Smart retry selects instance type and subnet automatically.
    """
    session = request.param[0]
    project = request.getfixturevalue(request.param[1])
    software_stack = request.getfixturevalue(request.param[2])
    clientAuth = request.getfixturevalue(request.param[3])

    session.project = {"project_id": project.project_id}
    session.software_stack = software_stack
    session.base_os = software_stack.base_os
    session.software_stack_id = software_stack.stack_id

    original_name = request.param[0].name
    base_os = getattr(software_stack.base_os, "value", software_stack.base_os)
    arch = getattr(software_stack.architecture, "value", software_stack.architecture)
    session.name = f"{original_name}-{base_os}-{arch}"[:24]

    api_invoker_type = request.config.getoption("--api-invoker-type")
    admin_client = ResClient(
        res_environment, ClientAuth(username=CLUSTER_ADMIN_USERNAME), api_invoker_type
    )

    logger.info("enabling smart retry for smart_retry_session fixture")
    admin_client.update_module_settings(
        request=UpdateModuleSettingsRequest(
            module_id="vdc",
            settings={"dcv_session": {"smart_retry": {"enabled": True}}},
        )
    )

    def disable_smart_retry() -> None:
        logger.info("disabling smart retry after smart_retry_session fixture")
        admin_client.update_module_settings(
            request=UpdateModuleSettingsRequest(
                module_id="vdc",
                settings={"dcv_session": {"smart_retry": {"enabled": False}}},
            )
        )

    request.addfinalizer(disable_smart_retry)

    api_client = ApiClient(res_environment, clientAuth)

    session = create_session_smart_retry(session, software_stack, api_client)

    def delete_vdi_session() -> None:
        delete_session(api_client, session)

    request.addfinalizer(delete_vdi_session)

    return session
