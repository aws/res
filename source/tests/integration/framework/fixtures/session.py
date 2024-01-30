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

import pytest

from ideadatamodel import (  # type: ignore
    CreateSessionRequest,
    DeleteProjectRequest,
    DeleteSessionRequest,
    UpdateSessionRequest,
    VirtualDesktopSchedule,
    VirtualDesktopScheduleType,
    VirtualDesktopSession,
    VirtualDesktopWeekSchedule,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.session_utils import (
    wait_for_deleting_session,
    wait_for_launching_session,
)


@pytest.fixture
def session(
    request: FixtureRequest, res_environment: ResEnvironment, non_admin: ClientAuth
) -> VirtualDesktopSession:
    """
    Fixture for setting up/tearing down the test project
    """
    session = request.param[0]
    project = request.getfixturevalue(request.param[1])
    software_stack = request.getfixturevalue(request.param[2])

    session.project = project
    session.software_stack = software_stack
    create_session_request = CreateSessionRequest(session=session)

    client = ResClient(request, res_environment, non_admin)
    create_session_response = client.create_session(create_session_request)

    session = wait_for_launching_session(client, create_session_response.session)

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

    def tear_down() -> None:
        session.force = True
        client.delete_sessions(DeleteSessionRequest(sessions=[session]))
        wait_for_deleting_session(client, session)

    request.addfinalizer(tear_down)

    return session
