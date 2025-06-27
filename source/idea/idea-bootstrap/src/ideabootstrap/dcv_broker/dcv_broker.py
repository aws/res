#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import configparser
import grp
import os
import pwd
import re
import shutil
import subprocess
import time
import urllib.parse
from datetime import datetime

import requests
from res.resources import cluster_settings
from res.utils import aws_utils, instance_metadata_utils, logging_utils

DCV_BROKER_PROPERTIES_FILE = (
    "/etc/dcv-session-manager-broker/session-manager-broker.properties"
)
NET_PROPERTIES_PATH = "/etc/alternatives/jre/conf/net.properties"
STAGING_AREA_RELATIVE_PATH = "staging_area"
MAX_RETRIES = 10
SLEEP_SECONDS = 30

logger = logging_utils.get_logger("bootstrap")


def _configure_proxy():
    https_proxy = os.environ.get("https_proxy")
    if not https_proxy:
        return

    logger.info(
        "Detected https_proxy.. starting java networking properties configuration updates."
    )

    # Check if file exists and create backup with timestamp
    if os.path.isfile(NET_PROPERTIES_PATH):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{NET_PROPERTIES_PATH}.{timestamp}"
        shutil.copy2(NET_PROPERTIES_PATH, backup_path)

    proxy_url = urllib.parse.urlparse(https_proxy)
    proxy_host = proxy_url.hostname
    proxy_port = proxy_url.port

    with open(NET_PROPERTIES_PATH, "r") as file:
        content = file.read()

    instance_region = instance_metadata_utils.get_instance_region()
    content = re.sub(
        r"http\.nonProxyHosts=localhost\|127\.\*\|\[::1]",
        f"http.nonProxyHosts=localhost|127.*|[::1]|169.254.169.254|dynamodb.{instance_region}.amazonaws.com",
        content,
    )

    content = re.sub(r"# https\.proxyHost=", f"https.proxyHost={proxy_host}", content)

    content = re.sub(
        r"# https\.proxyPort=443", f"https.proxyPort={proxy_port}", content
    )

    with open(NET_PROPERTIES_PATH, "w") as file:
        file.write(content)

    logger.info("java networking properties configuration completed.")


def clean_staging_area():
    if os.path.exists(STAGING_AREA_RELATIVE_PATH):
        shutil.rmtree(STAGING_AREA_RELATIVE_PATH)


def configure_dcv_broker_properties():
    logger.info("Configuring dcv session manager broker properties..")

    cluster_name = os.environ.get("environment_name", "")
    instance_region = instance_metadata_utils.get_instance_region()

    # Create DCV broker config file
    config = configparser.ConfigParser(allow_no_value=True)
    config.optionxform = str
    config.add_section("dcv_broker")

    config["dcv_broker"]["enable-authorization-server"] = "false"
    config["dcv_broker"]["enable-authorization"] = "true"
    config["dcv_broker"]["enable-agent-authorization"] = "false"

    config["dcv_broker"]["enable-persistence"] = "true"
    config["dcv_broker"]["persistence-db"] = "dynamodb"
    config["dcv_broker"]["dynamodb-region"] = instance_region
    config["dcv_broker"]["dynamodb-table-rcu"] = str(
        cluster_settings.get_setting(
            "vdc.dcv_broker.dynamodb_table.read_capacity.min_units"
        )
        or 5
    )
    config["dcv_broker"]["dynamodb-table-wcu"] = str(
        cluster_settings.get_setting(
            "vdc.dcv_broker.dynamodb_table.write_capacity.min_units"
        )
        or 5
    )
    config["dcv_broker"][
        "dynamodb-table-name-prefix"
    ] = f"{cluster_name}.vdc.dcv-broker."

    config["dcv_broker"]["connect-session-token-duration-minutes"] = str(
        cluster_settings.get_setting("vdc.dcv_broker.session_token_validity")
    )
    config["dcv_broker"]["delete-session-duration-hours"] = "0"
    config["dcv_broker"]["seconds-before-deleting-unreachable-dcv-server"] = "60"

    config["dcv_broker"]["client-to-broker-connector-https-port"] = str(
        cluster_settings.get_setting("vdc.dcv_broker.client_communication_port")
    )
    config["dcv_broker"]["client-to-broker-connector-bind-host"] = "0.0.0.0"
    config["dcv_broker"]["agent-to-broker-connector-https-port"] = str(
        cluster_settings.get_setting("vdc.dcv_broker.agent_communication_port")
    )
    config["dcv_broker"]["agent-to-broker-connector-bind-host"] = "0.0.0.0"

    config["dcv_broker"]["enable-gateway"] = "true"
    config["dcv_broker"]["gateway-to-broker-connector-https-port"] = str(
        cluster_settings.get_setting("vdc.dcv_broker.gateway_communication_port")
    )
    config["dcv_broker"]["gateway-to-broker-connector-bind-host"] = "0.0.0.0"

    config["dcv_broker"]["broker-to-broker-port"] = "47100"
    config["dcv_broker"]["cli-to-broker-port"] = "47200"
    config["dcv_broker"]["broker-to-broker-bind-host"] = "0.0.0.0"
    config["dcv_broker"]["broker-to-broker-discovery-port"] = "47500"
    config["dcv_broker"]["broker-to-broker-discovery-aws-region"] = instance_region
    config["dcv_broker"]["broker-to-broker-discovery-aws-alb-target-group-arn"] = (
        cluster_settings.get_setting("vdc.dcv_broker.client_target_group_arn")
    )
    config["dcv_broker"]["broker-to-broker-distributed-memory-max-size-mb"] = "4096"
    config["dcv_broker"]["broker-to-broker-connection-login"] = "dcvsm-user"
    config["dcv_broker"]["broker-to-broker-connection-pass"] = "dcvsm-pass"

    config["dcv_broker"]["metrics-fleet-name-dimension"] = cluster_name
    config["dcv_broker"]["enable-cloud-watch-metrics"] = "true"
    config["dcv_broker"]["session-manager-working-path"] = "/var/lib/dcvsmbroker"

    config["dcv_broker"]["session-screenshot-max-height"] = "600"
    config["dcv_broker"]["session-screenshot-max-width"] = "800"

    with open(DCV_BROKER_PROPERTIES_FILE, "w") as configfile:
        for key, value in config.items(config.sections()[0]):
            configfile.write(f"{key} = {value}\n")

    os.chown(
        DCV_BROKER_PROPERTIES_FILE,
        pwd.getpwnam("root").pw_uid,
        grp.getgrnam("dcvsmbroker").gr_gid,
    )
    os.chmod(DCV_BROKER_PROPERTIES_FILE, 0o640)

    subprocess.run(["systemctl", "enable", "dcv-session-manager-broker"], check=True)
    logger.info("dcv session manager broker properties configuration completed.")

    _configure_proxy()

    subprocess.run(["systemctl", "restart", "dcv-session-manager-broker"], check=True)
    logger.info("Restarted dcv session manager broker service.")


def configure_dcv_broker():
    logger.info("Configuring dcv broker..")
    provider_url = cluster_settings.get_setting(
        "identity-provider.cognito.provider_url"
    )
    subprocess.run(
        [
            "dcv-session-manager-broker",
            "register-auth-server",
            "--url",
            f"{provider_url}/.well-known/jwks.json",
        ],
        check=True,
    )

    retry_count = 0
    while retry_count < MAX_RETRIES:
        output = subprocess.getoutput("dcv-session-manager-broker list-auth-servers")
        if f"{provider_url}/.well-known/jwks.json" in output:
            break

        logger.info(
            f"DCV Broker configuration pending.. sleeping for {SLEEP_SECONDS} seconds."
        )
        time.sleep(SLEEP_SECONDS)
        retry_count += 1

    if retry_count == MAX_RETRIES:
        raise Exception("DCV Broker configuration failed.")

    logger.info("DCV broker configuration completed.")


def verify_broker_installation():
    client_port = cluster_settings.get_setting(
        "vdc.dcv_broker.client_communication_port"
    )

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = requests.get(
                f"https://localhost:{client_port}/sessionConnectionData/aSession/aOwner",
                verify=False,  # nosec
            )
            error = response.json().get("error")

            if error == "No authorization header":
                break
        except:
            pass

        logger.info(
            f"DCV Session Manager broker verification pending.. sleeping for {SLEEP_SECONDS} seconds."
        )
        time.sleep(SLEEP_SECONDS)
        retry_count += 1

    if retry_count == MAX_RETRIES:
        raise Exception("Failed to validate DCV Broker installation.")

    logger.info("DCV Session Manager broker verification succeeded.")


def notify_controller():
    message = {
        "event_group_id": "BROKER-USERDATA-COMPLETE",
        "event_type": "DCV_BROKER_USERDATA_EXECUTION_COMPLETE_EVENT",
    }

    aws_utils.sqs_send_message(
        message,
        cluster_settings.get_setting("vdc.events_sqs_queue_url"),
        "BROKER-USERDATA-COMPLETE",
    )
