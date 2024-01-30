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
from functools import cached_property

import boto3
import pytest

from tests.integration.framework.utils.ad_sync import ad_sync
from tests.integration.framework.utils.ec2_utils import (
    all_in_service_instances_from_asgs,
)
from tests.integration.framework.utils.test_mode import set_test_mode_for_all_servers

logger = logging.getLogger(__name__)


class ResEnvironment:
    def __init__(self, environment_name: str, region: str):
        self._environment_name = environment_name
        self._region = region

    @property
    def region(self) -> str:
        return self._region

    @property
    def cluster_manager_asg(self) -> str:
        return f"{self._environment_name}-cluster-manager-asg"

    @property
    def vdc_controller_asg(self) -> str:
        return f"{self._environment_name}-vdc-controller-asg"

    @cached_property
    def default_web_app_domain_name(self) -> str:
        session = boto3.session.Session(region_name=self._region)
        client = session.client("elbv2")

        describe_load_balancers_response = client.describe_load_balancers(
            Names=[f"{self._environment_name}-external-alb"]
        )
        dns_name: str = (
            describe_load_balancers_response["LoadBalancers"][0].get("DNSName", "")
            if len(describe_load_balancers_response.get("LoadBalancers", [])) == 1
            else ""
        )

        return dns_name


@pytest.fixture
def res_environment(
    request: pytest.FixtureRequest,
    environment_name: str,
    region: str,
) -> ResEnvironment:
    """
    Fixture for setting up the RES test environment
    """
    # Initialize the Res Environment
    res_environment = ResEnvironment(region=region, environment_name=environment_name)

    cluster_manager_instances = all_in_service_instances_from_asgs(
        [res_environment.cluster_manager_asg],
        region,
    )
    assert len(cluster_manager_instances) > 0, "Cluster Manager doesn't exist"
    vdc_instances = all_in_service_instances_from_asgs(
        [res_environment.vdc_controller_asg],
        region,
    )
    assert len(vdc_instances) > 0, "Virtual Desktop Controller doesn't exist"

    logger.info("relaunch servers in test mode")
    server_instances = cluster_manager_instances + vdc_instances
    set_test_mode_for_all_servers(region, server_instances, True)

    # Sync users and groups from AD so that integ tests can run with these users and groups
    logger.info("sync users and groups from AD")
    ad_sync(region, cluster_manager_instances[0])

    def tear_down() -> None:
        logger.info("disable server test mode")
        set_test_mode_for_all_servers(region, server_instances, False)

    request.addfinalizer(tear_down)

    return res_environment
