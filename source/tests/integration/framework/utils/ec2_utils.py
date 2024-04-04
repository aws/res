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

from typing import Any, Dict

import boto3
import pytest


def cluster_manager_instances(session: pytest.Session) -> list[Dict[str, Any]]:
    environment_name = session.config.getoption("--environment-name")
    region: str = session.config.getoption("--aws-region")

    instances = _all_in_service_instances_from_asgs(
        [f"{environment_name}-cluster-manager-asg"],
        region,
    )
    return instances


def vdc_instances(session: pytest.Session) -> list[Dict[str, Any]]:
    environment_name = session.config.getoption("--environment-name")
    region: str = session.config.getoption("--aws-region")

    instances = _all_in_service_instances_from_asgs(
        [f"{environment_name}-vdc-controller-asg"],
        region,
    )
    return instances


def _all_in_service_instances_from_asgs(
    auto_scaling_group_names: list[str],
    region: str,
) -> list[Dict[str, Any]]:
    session = boto3.session.Session(region_name=region)
    auto_scaling_client = session.client("autoscaling")
    response = auto_scaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=auto_scaling_group_names
    )

    instances: list[Dict[str, Any]] = []
    for group in response.get("AutoScalingGroups", []):
        instances = instances + [
            instance
            for instance in group.get("Instances", [])
            if instance.get("LifecycleState") == "InService"
        ]

    return instances
