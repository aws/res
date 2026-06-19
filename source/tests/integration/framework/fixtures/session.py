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

import json
import logging
from functools import cmp_to_key
from typing import Any, Dict, Optional

import pytest
from requests.exceptions import HTTPError
from res.resources.schedules import DayOfWeek  # type: ignore

from ideadatamodel import (  # type: ignore
    CreateSessionRequest,
    DeleteProjectRequest,
    DeleteSessionRequest,
    ListAllowedInstanceTypesForSessionRequest,
    ListAllowedInstanceTypesRequest,
    Project,
    SocaMemory,
    SocaMemoryUnit,
    VirtualDesktopServer,
    VirtualDesktopSession,
    VirtualDesktopSoftwareStack,
)
from tests.integration.framework.client.api_client import (
    ApiClient,
    CreateSessionRequestContent,
    CreateSessionResponseContent,
    UpdateSessionRequestContent,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.utils.model_utils import (
    get_backend_model_class,
    remove_none_values,
)
from tests.integration.framework.utils.session_utils import (
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


def delete_session(
    client: ResClient, api_client: ApiClient, session: VirtualDesktopSession
) -> None:
    session.force = True
    client.delete_sessions(DeleteSessionRequest(sessions=[session]))
    wait_for_deleting_session(api_client, session)


def create_session(
    session: VirtualDesktopSession,
    software_stack: VirtualDesktopSoftwareStack,
    client: ResClient,
    api_client: ApiClient,
) -> Optional[VirtualDesktopSession]:

    # Convert session to dict and recursively remove any fields with None values
    session_dict = remove_none_values(json.loads(session.json()))

    session_obj = VirtualDesktopSession_.from_dict(session_dict)
    if session_obj.software_stack:
        logger.info(
            f"Session software_stack.projects: {session_obj.software_stack.projects}"
        )

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

    session_dict = json.loads(session.json())

    session_dict["base_os"] = session.software_stack.base_os
    session_dict["software_stack_id"] = session.software_stack.stack_id

    if "server" not in session_dict or session_dict["server"] is None:
        session_dict["server"] = {}

    session_dict["server"]["root_volume_size"] = {
        "value": software_stack.min_storage.value,
        "unit": software_stack.min_storage.unit,
    }

    # Try different instance types smallest to largest, retrying on InsufficientInstanceCapacity errors.
    last_error = None
    for instance_type_info in reversed(allowed_instance_types):
        instance_type = instance_type_info.get("InstanceType", "")
        session_dict["server"]["instance_type"] = instance_type

        try:
            session_to_send = VirtualDesktopSession_.from_dict(session_dict)
        except Exception as e:
            logger.warning(f"Failed to deserialize session dict, using raw dict: {e}")
            session_to_send = session_dict

        try:
            create_session_response = api_client.create_session(
                CreateSessionRequestContent(session=session_to_send)
            )
            break
        except HTTPError as e:
            if (
                e.response is not None
                and "InsufficientInstanceCapacity" in e.response.text
            ):
                logger.warning(
                    f"Insufficient capacity for {instance_type}, trying next instance type..."
                )
                last_error = e
                continue
            raise
    else:
        raise last_error  # type: ignore

    session = create_session_response.session  # type: ignore

    try:
        session = wait_for_launching_session(api_client, session)
    except Exception as e:
        delete_session(client, api_client, session)
        raise e

    # Update the schedule to make sure that the virtual desktop session can be active every day.
    no_schedule = {"schedule_type": "NO_SCHEDULE"}
    session_dict = json.loads(session.json())
    session_dict["schedule"] = {day.value: no_schedule for day in DayOfWeek}
    session_dict.pop("software_stack", None)
    session_obj = VirtualDesktopSession_.from_dict(session_dict)
    update_request = UpdateSessionRequestContent(session=session_obj)
    api_client.update_session(
        session_id=session.idea_session_id, request_content=update_request
    )
    return session


@pytest.fixture
def session(
    request: FixtureRequest,
    res_environment: ResEnvironment,
) -> Optional[VirtualDesktopSession]:
    """
    Fixture for setting up/tearing down the test project
    """
    session = request.param[0]
    project = request.getfixturevalue(request.param[1])
    software_stack = request.getfixturevalue(request.param[2])
    clientAuth = request.getfixturevalue(request.param[3])

    session.project = project
    session.software_stack = software_stack
    session.base_os = software_stack.base_os

    # Append stack name to session name for easier identification
    # Use original param name to avoid mutation across parametrized runs
    original_name = request.param[0].name
    base_os = getattr(software_stack.base_os, "value", software_stack.base_os)
    arch = getattr(software_stack.architecture, "value", software_stack.architecture)
    session.name = f"{original_name}-{base_os}-{arch}"[:24]

    api_invoker_type = request.config.getoption("--api-invoker-type")
    client = ResClient(res_environment, clientAuth, api_invoker_type)
    api_client = ApiClient(res_environment, clientAuth)

    session = create_session(session, software_stack, client, api_client)

    def tear_down() -> None:
        delete_session(client, api_client, session)

    request.addfinalizer(tear_down)

    return session
