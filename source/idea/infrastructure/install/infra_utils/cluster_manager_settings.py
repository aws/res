#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import Any, Dict, List

import constructs

from idea.infrastructure.install.infra_utils.utils import InfraUtils

STATIC_SETTINGS: Dict[str, Any] = {
    "oauth2_client": {"refresh_token_validity_hours": 24},
    "endpoints": {
        "external": {"priority": 12, "path_patterns": ["/cluster-manager/*"]},
        "internal": {"priority": 12, "path_patterns": ["/cluster-manager/*"]},
    },
    "ec2": {
        "autoscaling": {
            "public": False,
            "instance_type": "m5.large",
            "volume_size": 200,
            "enable_detailed_monitoring": False,
            "min_capacity": 1,
            "max_capacity": 3,
            "cooldown_minutes": 5,
            "default_instance_warmup": 25,
            "new_instances_protected_from_scale_in": False,
            "elb_healthcheck": {"grace_time_minutes": 25},
            "cpu_utilization_scaling_policy": {
                "target_utilization_percent": 80,
                "estimated_instance_warmup_minutes": 25,
            },
            "rolling_update_policy": {
                "max_batch_size": 1,
                "min_instances_in_service": 1,
                "pause_time_minutes": 15,
            },
            "metadata_http_tokens": "required",
        }
    },
}


class ClusterManagerSettings:
    """
    Util class for retrieving virtual desktop controller stack specific cluster settings
    """

    def __init__(self, cluster_name: str, scope: constructs.Construct):
        self.cluster_name = cluster_name
        self.scope = scope
        self.static_settings = STATIC_SETTINGS

    @property
    def external_endpoints_settings(self) -> Any:
        return self.static_settings.get("endpoints", {}).get("external", {})

    @property
    def internal_endpoints_settings(self) -> Any:
        return self.static_settings.get("endpoints", {}).get("internal", {})

    @property
    def refresh_token_validity_hours(self) -> Any:
        return self.static_settings.get("oauth2_client", {}).get(
            "refresh_token_validity_hours", 12
        )

    @property
    @lru_cache
    def autoscaling_settings(self) -> Any:
        return self.static_settings.get("ec2", {}).get("autoscaling", {})
