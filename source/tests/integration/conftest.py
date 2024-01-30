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
        "--custom-vdi-domain-name", action="store", help="Custom vid domain name"
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
