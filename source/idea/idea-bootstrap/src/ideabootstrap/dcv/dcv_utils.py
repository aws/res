#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

from res.resources import cluster_settings
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")


def get_cluster_internal_endpoint() -> str:
    internal_alb_dns = cluster_settings.get_setting(
        "cluster.load_balancers.internal_alb.certificates.custom_dns_name"
    )
    if not internal_alb_dns:
        internal_alb_dns = cluster_settings.get_setting(
            "cluster.load_balancers.internal_alb.load_balancer_dns_name"
        )
    if not internal_alb_dns:
        logger.error("cluster internal endpoint not found")
        return ""
    return f"https://{internal_alb_dns}"
