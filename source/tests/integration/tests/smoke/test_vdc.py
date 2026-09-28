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
import os
import zoneinfo
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import boto3
import pytest
from res.resources import cluster_settings, schedules  # type: ignore
from res.utils import table_utils  # type: ignore

# Project still goes through the not-yet-migrated cluster-manager API, so it
# stays ideadatamodel.
from ideadatamodel import (  # type: ignore
    GetModuleSettingsRequest,
    Project,
    UpdateModuleSettingsRequest,
)
from tests.integration.framework.client.api_client import ApiClient
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.fixture_request import FixtureRequest
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session import session
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.fixtures.users.non_admin import non_admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.session_utils import (
    force_idle_session,
    force_idle_session_terminate,
    wait_for_deleted_idle_session,
    wait_for_session_state,
    wait_for_stopped_idle_session,
)
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

# Backend data-model classes (source/idea/data-model). The session APIs consume
# and return these.
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)

VDC_SOFTWARE_STACKS = [
    AL2023_SOFTWARE_STACK,
]

logger = logging.getLogger(__name__)


@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestsVDC(object):
    @pytest.mark.nightly
    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize(
        "admin_username",
        [
            "admin1",
        ],
    )
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize(
        "non_admin_username",
        [
            "user1",
        ],
    )
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-vdc-integ-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-vdc-integ-test"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES vdc integ test project",
                    enable_budgets=False,
                ),
                [],
                ["RESAdministrators", "group_1", "group_2"],
                [],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [
            (
                software_stack,
                "project",
                "admin",
            )
            for software_stack in VDC_SOFTWARE_STACKS
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="VirtualDesktop-vdc-integ-"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES vdc integ test VDI session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_vdi_auto_stop(
        self,
        request: FixtureRequest,
        region: str,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        res_environment: ResEnvironment,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Deterministic end to end test for VDI Auto Stop feature:
        1. Create a project, software stack and virtual desktop session.
        2. Set the session to idle.
        3. Wait for the session to be stopped.
        3. Clean up the test project, software stack and virtual desktop session.
        """
        if not session:
            # VDI is not supported with the current configuration
            return

        logger.info(f"Starting stop idle integ test for {session.name}...")
        api_client = ApiClient(res_environment, admin)

        # Force idle (writes instance-level config only, no global DDB changes)
        force_idle_session(session)
        wait_for_stopped_idle_session(api_client, session)

    @pytest.mark.nightly
    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-vdc-term-idle"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-vdc-term-idle"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES terminate-on-idle test project",
                    enable_budgets=False,
                ),
                [],
                ["RESAdministrators", "group_1", "group_2"],
                [],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(AL2023_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="vdi-term-idle-" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES terminate-on-idle test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_vdi_terminate_on_idle(
        self,
        request: FixtureRequest,
        region: str,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        res_environment: ResEnvironment,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        End-to-end test for VDI terminate-on-idle:
        1. Force idle detection with Terminate transition (instance-level config).
        2. Verify session reaches DELETED (not just STOPPED).
        """
        if not session:
            return

        logger.info(f"Starting terminate-on-idle integ test for {session.name}...")

        api_client = ApiClient(res_environment, admin)

        # Force idle with Terminate transition (writes to instance-level config only,
        # no global DDB settings change needed)
        force_idle_session_terminate(session)

        # Wait for session to be deleted
        wait_for_deleted_idle_session(api_client, session)
        logger.info(f"Session {session.name} successfully terminated on idle.")

    @pytest.mark.nightly
    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.usefixtures("non_admin")
    @pytest.mark.parametrize("non_admin_username", ["user1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-vdc-enforce-sched"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-vdc-enforce-sched"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES enforce-schedule test project",
                    enable_budgets=False,
                ),
                [],
                ["RESAdministrators", "group_1", "group_2"],
                [],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(AL2023_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="vdi-enforce-sched-"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES enforce-schedule test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_vdi_enforce_schedule(
        self,
        request: FixtureRequest,
        region: str,
        admin: ClientAuth,
        admin_username: str,
        non_admin: ClientAuth,
        non_admin_username: str,
        res_environment: ResEnvironment,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        End-to-end test for enforce-schedule resuming an idle-stopped session:
        1. Force session to idle → wait for STOPPED_IDLE.
        2. Enable enforce_schedule.
        3. Create a schedule entry for this session with start_up_time = now.
        4. Invoke the scheduled event Lambda to trigger resume.
        5. Verify session resumes to READY.
        6. Cleanup: remove schedule, restore settings.
        """
        if not session:
            return

        logger.info(f"Starting enforce-schedule integ test for {session.name}...")

        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, admin, api_invoker_type)
        api_client = ApiClient(res_environment, admin)

        # Save original enforce_schedule setting
        original_settings = admin_client.get_module_settings(
            request=GetModuleSettingsRequest(module_id="vdc")
        )
        original_enforce_schedule = original_settings.settings.get(
            "dcv_session", {}
        ).get("enforce_schedule", True)

        schedule_id = None
        try:
            # Step 1: Disable enforce_schedule to ensure session stays STOPPED_IDLE
            admin_client.update_module_settings(
                request=UpdateModuleSettingsRequest(
                    module_id="vdc",
                    settings={"dcv_session": {"enforce_schedule": False}},
                )
            )

            # Step 2: Force idle → STOPPED_IDLE
            force_idle_session(session)
            wait_for_stopped_idle_session(api_client, session)
            logger.info(f"Session {session.name} is now STOPPED_IDLE.")

            # Step 3: Enable enforce_schedule (this allows the scheduler to resume idle sessions)
            admin_client.update_module_settings(
                request=UpdateModuleSettingsRequest(
                    module_id="vdc",
                    settings={"dcv_session": {"enforce_schedule": True}},
                )
            )

            # Step 4: Create a schedule with start_up_time = now in cluster timezone.
            # The scheduled event Lambda converts event time to the cluster timezone
            # before looking up schedules, so day_of_week and times must match that TZ.

            cluster_tz_name = (
                cluster_settings.get_setting("cluster.timezone")
                or "America/Los_Angeles"
            )
            cluster_tz = zoneinfo.ZoneInfo(cluster_tz_name)
            now = datetime.now(cluster_tz)
            # Compute shut_down_time capped to end of day, strictly > start_up_time.
            end_of_day = now.replace(hour=23, minute=59)
            shut_down_dt = min(now + timedelta(hours=6), end_of_day)
            # If start == shut_down (23:59 edge case), shift start back 1 minute.
            # The event time we send to the Lambda also shifts so all three align.
            event_dt = now
            if now >= shut_down_dt:
                event_dt = now - timedelta(minutes=1)
            start_up_time = f"{event_dt.hour:02d}:{event_dt.minute:02d}"
            shut_down_time = f"{shut_down_dt.hour:02d}:{shut_down_dt.minute:02d}"
            day_of_week = [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ][now.weekday()]

            schedule_entry = schedules.create_schedule(
                {
                    "idea_session_id": session.idea_session_id,
                    "idea_session_owner": session.owner,
                    "day_of_week": day_of_week,
                    "start_up_time": start_up_time,
                    "shut_down_time": shut_down_time,
                    "schedule_type": "CUSTOM_SCHEDULE",
                }
            )
            schedule_id = schedule_entry.get("schedule_id")
            logger.info(
                f"Created schedule {schedule_id} with start_up_time={start_up_time}"
            )

            # Step 5: Invoke the scheduled event Lambda
            lambda_client = boto3.client("lambda", region_name=region)
            env_name = res_environment._environment_name
            # Event time must be in UTC (as EventBridge sends it). The Lambda
            # converts this to cluster timezone internally. Use the same `event_dt`
            # we used for the schedule so they're guaranteed to align.
            event_time_utc = event_dt.astimezone(timezone.utc)
            event_payload = json.dumps(
                {
                    "detail-type": "Scheduled Event",
                    "time": event_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )
            response = lambda_client.invoke(
                FunctionName=f"{env_name}-vdc-scheduled-event-handler",
                InvocationType="RequestResponse",
                Payload=event_payload,
            )
            if "FunctionError" in response:
                payload = response["Payload"].read().decode()
                logger.error(f"Lambda error: {payload}")
            logger.info("Scheduled event Lambda invoked.")

            # Step 6: Wait for session to resume to READY
            VirtualDesktopSessionState = get_backend_model_class(
                "virtual_desktop_session_state", "VirtualDesktopSessionState"
            )
            wait_for_session_state(
                api_client, session, VirtualDesktopSessionState.READY
            )
            logger.info(
                f"Session {session.name} successfully resumed via enforce-schedule."
            )
        finally:
            # Cleanup: remove schedule entry
            if schedule_id:
                table_utils.delete_item(
                    "vdc.controller.schedules",
                    key={
                        "day_of_week": day_of_week,
                        "schedule_id": schedule_id,
                    },
                )

            # Restore original enforce_schedule
            admin_client.update_module_settings(
                request=UpdateModuleSettingsRequest(
                    module_id="vdc",
                    settings={
                        "dcv_session": {"enforce_schedule": original_enforce_schedule}
                    },
                )
            )
