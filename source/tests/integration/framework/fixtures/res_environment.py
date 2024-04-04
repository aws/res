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
    def region(self) -> str:
        return self._region

    @cached_property
    def web_app_domain_name(self) -> str:
        if self._custom_web_app_domain_name:
            return self._custom_web_app_domain_name

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
