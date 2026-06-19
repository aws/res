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
from typing import Optional

import boto3
import pytest

logger = logging.getLogger(__name__)


class ResEnvironment:
    def __init__(
        self,
        environment_name: str,
        region: str,
        custom_web_app_domain_name: Optional[str] = None,
    ):
        self._environment_name = environment_name
        self._region = region
        self._custom_web_app_domain_name = custom_web_app_domain_name

    @property
    def environment_name(self) -> str:
        return self._environment_name

    @property
    def region(self) -> str:
        return self._region

    def _get_alb_dns_name(self, alb_name: str) -> str:
        session = boto3.session.Session(region_name=self._region)
        client = session.client("elbv2")
        response = client.describe_load_balancers(Names=[alb_name])
        load_balancers = response.get("LoadBalancers", [])
        if len(load_balancers) != 1:
            return ""
        return str(load_balancers[0].get("DNSName", ""))

    @cached_property
    def web_app_domain_name(self) -> str:
        if self._custom_web_app_domain_name:
            return self._custom_web_app_domain_name
        return self._get_alb_dns_name(f"{self._environment_name}-external-alb")

    @cached_property
    def internal_alb_endpoint(self) -> str:
        return self._get_alb_dns_name(f"{self._environment_name}-internal-alb")


@pytest.fixture
def res_environment(
    request: pytest.FixtureRequest,
    environment_name: str,
    region: str,
) -> ResEnvironment:
    """
    Fixture for the RES test environment
    """
    custom_web_app_domain_name = request.config.getoption(
        "--custom-web-app-domain-name"
    )

    res_environment = ResEnvironment(
        region=region,
        environment_name=environment_name,
        custom_web_app_domain_name=custom_web_app_domain_name,
    )

    return res_environment
