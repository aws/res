#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import configparser
import os
import shutil
import subprocess
from datetime import datetime

from res.resources import cluster_settings
from res.utils import logging_utils

CONFIG_FILE = "/etc/dcv-connection-gateway/dcv-connection-gateway.conf"
DCV_WEB_VIEWER_INSTALL_LOCATION = "/usr/share/dcv/www"

logger = logging_utils.get_logger("bootstrap")


def _copy_static_resources():
    # Copy static resources for DCV web viewer
    logger.info("Copying static resources...")

    app_dir = f'{os.environ.get("IDEA_APP_DEPLOY_DIR", "")}/dcv-connection-gateway'
    shutil.copytree(
        f"{app_dir}/resources",
        DCV_WEB_VIEWER_INSTALL_LOCATION,
        dirs_exist_ok=True,
    )


def _get_cluster_internal_endpoint() -> str:
    internal_alb_dns = cluster_settings.get_setting(
        "cluster.load_balancers.internal_alb.certificates.custom_dns_name"
    )
    if not internal_alb_dns:
        # backward compat. custom_dns_name moved under certificates starting with 3.0.0-rc.2
        internal_alb_dns = cluster_settings.get_setting(
            "cluster.load_balancers.internal_alb.custom_dns_name"
        )

    if not internal_alb_dns:
        internal_alb_dns = cluster_settings.get_setting(
            "cluster.load_balancers.internal_alb.load_balancer_dns_name"
        )
    if not internal_alb_dns:
        raise Exception("cluster internal endpoint not found.")
    return f"https://{internal_alb_dns}"


def configure():
    _copy_static_resources()

    # Backup existing config if it exists
    if os.path.exists(CONFIG_FILE):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{CONFIG_FILE}.{timestamp}"
        shutil.move(CONFIG_FILE, backup_file)

    internal_alb_endpoint = _get_cluster_internal_endpoint()
    gateway_to_broker_port = cluster_settings.get_setting(
        "vdc.dcv_broker.gateway_communication_port"
    )

    logger.info("Creating DCV Connection Gateway config file...")

    config = configparser.ConfigParser()
    config["log"] = {"level": '"trace"'}

    config["gateway"] = {
        "quic-listen-endpoints": '["0.0.0.0:8443", "[::]:8443"]',
        "web-listen-endpoints": '["0.0.0.0:8443", "[::]:8443"]',
        "cert-file": '"/etc/dcv-connection-gateway/certs/default_cert.pem"',
        "cert-key-file": '"/etc/dcv-connection-gateway/certs/default_key_pkcs8.pem"',
    }

    config["health-check"] = {"bind-addr": '"::"', "port": "8989"}

    config["dcv"] = {"tls-strict": "false"}

    config["resolver"] = {
        "url": f'"{internal_alb_endpoint}:{gateway_to_broker_port}"',
        "tls-strict": "false",
    }

    config["web-resources"] = {
        "local-resources-path": '"/usr/share/dcv/www"',
        "tls-strict": "false",
    }

    with open(CONFIG_FILE, "w") as f:
        config.write(f)

    # Enable and start the service
    subprocess.run(["systemctl", "enable", "dcv-connection-gateway"], check=True)
    subprocess.run(["systemctl", "start", "dcv-connection-gateway"], check=True)

    logger.info("DCV Connection Gateway service has been started.")
