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

import pytest

from ideadatamodel import UpdateModuleSettingsRequest  # type: ignore
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.ad_sync import ad_sync
from tests.integration.framework.utils.alb_utils import (
    update_alb_invalid_header_drop_flag,
)
from tests.integration.framework.utils.ec2_utils import (
    cluster_manager_instances,
    vdc_instances,
)
from tests.integration.framework.utils.test_mode import set_test_mode_for_all_servers
from tests.integration.tests.config import TEST_SOFTWARE_STACKS

logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--environment-name",
        action="store",
        required=True,
        help="Name of the RES environment",
    )
    parser.addoption(
        "--aws-region",
        action="store",
        default="us-east-1",
        help="Region of the RES environment",
    )
    parser.addoption(
        "--custom-web-app-domain-name",
        action="store",
        help="Custom web app domain name",
    )
    parser.addoption(
        "--api-invoker-type",
        action="store",
        default="http",
        help="Type of the API invoker",
        choices="http",
    )
    parser.addoption(
        "--ssm-output-bucket",
        action="store",
        help="S3 bucket for storing SSM command output",
    )


@pytest.fixture
def environment_name(request: pytest.FixtureRequest) -> str:
    environment_name: str = request.config.getoption("--environment-name")
    return environment_name


@pytest.fixture
def region(request: pytest.FixtureRequest) -> str:
    region: str = request.config.getoption("--aws-region")
    return region


@pytest.fixture
def ssm_output_bucket(request: pytest.FixtureRequest) -> str:
    ssm_output_bucket: str = request.config.getoption("--ssm-output-bucket")
    return ssm_output_bucket


def pytest_sessionstart(session: pytest.Session) -> None:
    if getattr(session.config, "workerinput", None) is not None:
        # Master process will set up the test environment before any worker session starts
        # No action is needed on worker processes
        return

    region: str = session.config.getoption("--aws-region")
    cluster_managers = cluster_manager_instances(session)
    vdcs = vdc_instances(session)

    logger.info("relaunch servers in test mode")
    set_test_mode_for_all_servers(region, cluster_managers + vdcs, True)

    # Sync users and groups from AD so that integ tests can run with these users and groups
    logger.info("sync users and groups from AD")
    ad_sync(region, cluster_managers[0])

    # Disable ALB attribute for dropping invalid headers
    logger.info(
        "disable ALB attribute for dropping invalid headers; needed for integration testing"
    )
    update_alb_invalid_header_drop_flag(session, value="false")

    logger.info("update allowed sessions per user")
    res_client(session).update_module_settings(
        UpdateModuleSettingsRequest(
            module_id="vdc",
            settings={
                "dcv_session": {
                    "allowed_sessions_per_user": str(len(TEST_SOFTWARE_STACKS))
                }
            },
        )
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if getattr(session.config, "workerinput", None) is not None:
        # Master process will clean up the test environment after all the worker sessions complete
        # No action is needed on worker process
        return
    region: str = session.config.getoption("--aws-region")

    logger.info("update allowed sessions per user")
    res_client(session).update_module_settings(
        UpdateModuleSettingsRequest(
            module_id="vdc",
            settings={"dcv_session": {"allowed_sessions_per_user": "5"}},
        )
    )

    # Enable ALB attribute for dropping invalid headers
    logger.info(
        "enable ALB attribute for dropping invalid headers; integration test finished"
    )
    update_alb_invalid_header_drop_flag(session, value="true")

    logger.info("disable server test mode")
    set_test_mode_for_all_servers(
        region, cluster_manager_instances(session) + vdc_instances(session), False
    )


def res_client(session: pytest.Session) -> ResClient:
    region = session.config.getoption("--aws-region")
    environment_name = session.config.getoption("--environment-name")
    custom_web_app_domain_name = session.config.getoption(
        "--custom-web-app-domain-name"
    )
    api_invoker_type = session.config.getoption("--api-invoker-type")

    res_environment = ResEnvironment(
        region=region,
        environment_name=environment_name,
        custom_web_app_domain_name=custom_web_app_domain_name,
    )

    return ResClient(
        res_environment, ClientAuth(username="clusteradmin"), api_invoker_type
    )
