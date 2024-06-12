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

import time

import boto3
import pytest


def update_alb_invalid_header_drop_flag(session: pytest.Session, value: str) -> None:
    boto3_session = boto3.session.Session(
        region_name=session.config.getoption("--aws-region")
    )
    client = boto3_session.client("elbv2")
    env_name = session.config.getoption("--environment-name")

    describe_load_balancers_response = client.describe_load_balancers(
        Names=[f"{env_name}-external-alb"]
    )
    load_balancer_arn: str = (
        describe_load_balancers_response["LoadBalancers"][0].get("LoadBalancerArn", "")
        if len(describe_load_balancers_response.get("LoadBalancers", [])) == 1
        else ""
    )

    if not load_balancer_arn:
        raise Exception(f"Could not find ALB {env_name}-external-alb")

    client.modify_load_balancer_attributes(
        LoadBalancerArn=load_balancer_arn,
        Attributes=[
            {
                "Key": "routing.http.drop_invalid_header_fields.enabled",
                "Value": value,
            }
        ],
    )

    time.sleep(3)  # Needed for eventual consistency
