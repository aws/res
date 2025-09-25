#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import Any, Dict, List

import constructs

from idea.infrastructure.install.infra_utils.utils import InfraUtils

STATIC_SETTINGS: Dict[str, Any] = {
    "autoscaling": {
        # default autoscaling setting for all vdc stack infra hosts
        "public": False,
        "volume_size": 200,
        "min_capacity": 1,
        "max_capacity": 3,
        "cooldown_minutes": 5,
        "default_instance_warmup": 25,
        "grace_time_minutes": 25,
        "max_batch_size": 1,
        "min_instances_in_service": 1,
        "pause_time_minutes": 25,
        "target_utilization_percent": 80,
        "estimated_instance_warmup_minutes": 25,
        "enable_detailed_monitoring": False,
        "new_instances_protected_from_scale_in": False,
        "metadata_http_tokens": "required",
        # add corresponding key value pair to customize setting for specific infra host
        "controller": {},
        "dcv_broker": {},
        "dcv_connection_gateway": {},
    },
    "endpoints": {
        "external": {"path_patterns": ["/vdc/*"], "priority": 13},
        "internal": {"path_patterns": ["/vdc/*"], "priority": 13},
    },
    "dcv_session": {
        "quic_support": False,
    },
    "external_nlb": {"access_logs": True},
}


class VdcSettings:
    """
    Util class for retrieving virtual desktop controller stack specific cluster settings
    """

    def __init__(self, cluster_name: str, scope: constructs.Construct):
        self.cluster_name = cluster_name
        self.scope = scope
        self.static_settings = STATIC_SETTINGS

    @property
    @lru_cache
    def external_nlb_enable_access_log(self) -> Any:
        return self.static_settings.get("external_nlb", {}).get("access_logs", True)

    @property
    def quic_support(self) -> Any:
        return self.static_settings.get("dcv_session", {}).get("quic_support", False)

    @staticmethod
    def autoscaling_setting(component: str, key: str) -> Any:
        customized = STATIC_SETTINGS.get("autoscaling", {}).get(component, {}).get(key)
        if customized is not None:
            return customized
        return STATIC_SETTINGS.get("autoscaling", {}).get(key)

    @staticmethod
    def endpoints_path_patterns(facing: str) -> Any:
        return (
            STATIC_SETTINGS.get("endpoints", {})
            .get(facing, {})
            .get("path_patterns", [])
        )

    @staticmethod
    def endpoints_priority(facing: str) -> Any:
        return STATIC_SETTINGS.get("endpoints", {}).get(facing, {}).get("priority", 13)

    @lru_cache
    def autoscaling_instance_type(self, component: str) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            f"vdc.{component}.autoscaling.instance_type",
            self.cluster_name,
        )

    @lru_cache
    def autoscaling_instance_ami(self, component: str) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            f"vdc.{component}.autoscaling.instance_ami",
            self.cluster_name,
        )
