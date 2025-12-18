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

from ideadatamodel import (  # type: ignore
    CreateSessionRequest,
    DeleteProjectRequest,
    DeleteSessionRequest,
    ListAllowedInstanceTypesForSessionRequest,
    ListAllowedInstanceTypesRequest,
    Project,
    SocaMemory,
    SocaMemoryUnit,
    UpdateSessionRequest,
    VirtualDesktopSchedule,
    VirtualDesktopScheduleType,
    VirtualDesktopServer,
    VirtualDesktopSession,
    VirtualDesktopSoftwareStack,
    VirtualDesktopWeekSchedule,
)
from tests.integration.framework.client.api_client import ApiClient
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


def delete_session(client: ResClient, session: VirtualDesktopSession) -> None:
    session.force = True
    client.delete_sessions(DeleteSessionRequest(sessions=[session]))
    wait_for_deleting_session(client, session)


def create_session(
    session: VirtualDesktopSession,
    software_stack: VirtualDesktopSoftwareStack,
    client: ResClient,
    api_client: ApiClient,
) -> Optional[VirtualDesktopSession]:

    # Convert session to dict and recursively remove any fields with None values
    session_dict = remove_none_values(json.loads(session.json()))

    allowed_instance_types = api_client.list_allowed_instance_types_for_session(
        ListAllowedInstanceTypesForSessionRequestContent(
            session=VirtualDesktopSession_.from_dict(session_dict)
        )
    ).listing  # type: ignore

    if not allowed_instance_types:
        pytest.skip(
            f"No allowed instance types are available for software stack {software_stack.name}"
        )

    allowed_instance_types = sorted(
        allowed_instance_types, key=cmp_to_key(compare_instance_types)
    )
    session.server = VirtualDesktopServer(
        instance_type=allowed_instance_types[-1].get("InstanceType", ""),
        root_volume_size=software_stack.min_storage,
    )

    create_session_response = client.create_session(
        CreateSessionRequest(session=session)
    )
    session = create_session_response.session

    try:
        session = wait_for_launching_session(client, session)
    except Exception as e:
        delete_session(client, session)
        raise e

    # Update the schedule to make sure that the virtual desktop session can be active every day.
    session.schedule = VirtualDesktopWeekSchedule(
        monday=VirtualDesktopSchedule(
            schedule_type=VirtualDesktopScheduleType.NO_SCHEDULE
        ),
        tuesday=VirtualDesktopSchedule(
            schedule_type=VirtualDesktopScheduleType.NO_SCHEDULE
        ),
        wednesday=VirtualDesktopSchedule(
            schedule_type=VirtualDesktopScheduleType.NO_SCHEDULE
        ),
        thursday=VirtualDesktopSchedule(
            schedule_type=VirtualDesktopScheduleType.NO_SCHEDULE
        ),
        friday=VirtualDesktopSchedule(
            schedule_type=VirtualDesktopScheduleType.NO_SCHEDULE
        ),
        saturday=VirtualDesktopSchedule(
            schedule_type=VirtualDesktopScheduleType.NO_SCHEDULE
        ),
        sunday=VirtualDesktopSchedule(
            schedule_type=VirtualDesktopScheduleType.NO_SCHEDULE
        ),
    )
    update_session_request = UpdateSessionRequest(session=session)
    client.update_session(update_session_request)
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

    api_invoker_type = request.config.getoption("--api-invoker-type")
    client = ResClient(res_environment, clientAuth, api_invoker_type)
    api_client = ApiClient(res_environment, clientAuth)

    session = create_session(session, software_stack, client, api_client)

    def tear_down() -> None:
        delete_session(client, session)

    request.addfinalizer(tear_down)

    return session
