#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import configparser
import grp
import os
import pwd
import subprocess
import tempfile
import pytest
import requests

from ideabootstrap.dcv_broker import dcv_broker
from pydantic import BaseModel
from res.resources import cluster_settings
from res.utils import instance_metadata_utils


class User(BaseModel):
    pw_uid: int


class Group(BaseModel):
    gr_gid: int


class Response:
    def __init__(self, message: str):
        self.message = message

    def json(self):
        return {"error": self.message}


def test_configure_proxy_networking_properties_configuration_succeed(monkeypatch):
    monkeypatch.setattr(
        instance_metadata_utils, "get_instance_region", lambda: "us-east-1"
    )
    monkeypatch.setenv("https_proxy", "https://localhost:22")

    networking_properties_configuration = "http.nonProxyHosts=localhost|127.*|[::1]\n# https.proxyHost=\n# https.proxyPort=443\n"
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        with open(temp_file_name, "w") as file:
            file.write(networking_properties_configuration)
        monkeypatch.setattr(dcv_broker, "NET_PROPERTIES_PATH", temp_file_name)

        dcv_broker._configure_proxy()
        with open(temp_file_name, "r") as file:
            lines = file.readlines()
            assert len(lines) == 3
            assert (
                lines[0]
                == "http.nonProxyHosts=localhost|127.*|[::1]|169.254.169.254|dynamodb.us-east-1.amazonaws.com\n"
            )
            assert lines[1] == "https.proxyHost=localhost\n"
            assert lines[2] == "https.proxyPort=22\n"


def test_configure_dcv_broker_properties_succeed(monkeypatch):
    def mock_get(key: str):
        if key == "vdc.dcv_broker.dynamodb_table.read_capacity.min_units":
            return 10
        elif key == "vdc.dcv_broker.dynamodb_table.write_capacity.min_units":
            return 10
        elif key == "vdc.dcv_broker.session_token_validity":
            return 60
        elif key == "vdc.dcv_broker.client_communication_port":
            return 8443
        elif key == "vdc.dcv_broker.agent_communication_port":
            return 8444
        elif key == "vdc.dcv_broker.gateway_communication_port":
            return 8445
        elif key == "vdc.dcv_broker.client_target_group_arn":
            return "client_target_group_arn"
        else:
            return None

    monkeypatch.setattr(cluster_settings, "get_setting", mock_get)
    monkeypatch.setattr(
        instance_metadata_utils, "get_instance_region", lambda: "us-east-1"
    )
    monkeypatch.setattr(pwd, "getpwnam", lambda x: User(pw_uid=0))
    monkeypatch.setattr(grp, "getgrnam", lambda x: Group(gr_gid=1))
    monkeypatch.setattr(os, "chown", lambda x, y, z: None)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setenv("environment_name", "res-test")

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(dcv_broker, "DCV_BROKER_PROPERTIES_FILE", temp_file_name)

        dcv_broker.configure_dcv_broker_properties()

        config = configparser.ConfigParser()
        with open(temp_file_name, "r") as f:
            config.read_string("[dcv_broker]\n" + f.read())

        assert config["dcv_broker"]["enable-authorization-server"] == "false"
        assert config["dcv_broker"]["enable-authorization"] == "true"
        assert config["dcv_broker"]["enable-agent-authorization"] == "false"

        assert config["dcv_broker"]["enable-persistence"] == "true"
        assert config["dcv_broker"]["persistence-db"] == "dynamodb"
        assert config["dcv_broker"]["dynamodb-region"] == "us-east-1"
        assert config["dcv_broker"]["dynamodb-table-rcu"] == "10"
        assert config["dcv_broker"]["dynamodb-table-wcu"] == "10"
        assert (
            config["dcv_broker"]["dynamodb-table-name-prefix"]
            == "res-test.vdc.dcv-broker."
        )

        assert config["dcv_broker"]["connect-session-token-duration-minutes"] == "60"
        assert config["dcv_broker"]["delete-session-duration-hours"] == "0"
        assert (
            config["dcv_broker"]["seconds-before-deleting-unreachable-dcv-server"]
            == "60"
        )

        assert config["dcv_broker"]["client-to-broker-connector-https-port"] == "8443"
        assert config["dcv_broker"]["client-to-broker-connector-bind-host"] == "0.0.0.0"
        assert config["dcv_broker"]["agent-to-broker-connector-https-port"] == "8444"
        assert config["dcv_broker"]["agent-to-broker-connector-bind-host"] == "0.0.0.0"

        assert config["dcv_broker"]["enable-gateway"] == "true"
        assert config["dcv_broker"]["gateway-to-broker-connector-https-port"] == "8445"
        assert (
            config["dcv_broker"]["gateway-to-broker-connector-bind-host"] == "0.0.0.0"
        )

        assert config["dcv_broker"]["broker-to-broker-port"] == "47100"
        assert config["dcv_broker"]["cli-to-broker-port"] == "47200"
        assert config["dcv_broker"]["broker-to-broker-bind-host"] == "0.0.0.0"
        assert config["dcv_broker"]["broker-to-broker-discovery-port"] == "47500"
        assert (
            config["dcv_broker"]["broker-to-broker-discovery-aws-region"] == "us-east-1"
        )
        assert config["dcv_broker"][
            "broker-to-broker-discovery-aws-alb-target-group-arn"
        ] == (cluster_settings.get_setting("vdc.dcv_broker.client_target_group_arn"))
        assert (
            config["dcv_broker"]["broker-to-broker-distributed-memory-max-size-mb"]
            == "4096"
        )
        assert config["dcv_broker"]["broker-to-broker-connection-login"] == "dcvsm-user"
        assert config["dcv_broker"]["broker-to-broker-connection-pass"] == "dcvsm-pass"

        assert config["dcv_broker"]["metrics-fleet-name-dimension"] == "res-test"
        assert config["dcv_broker"]["enable-cloud-watch-metrics"] == "true"
        assert (
            config["dcv_broker"]["session-manager-working-path"]
            == "/var/lib/dcvsmbroker"
        )

        assert config["dcv_broker"]["session-screenshot-max-height"] == "600"
        assert config["dcv_broker"]["session-screenshot-max-width"] == "800"


def test_configure_dcv_broker_succeed(monkeypatch):
    monkeypatch.setattr(dcv_broker, "MAX_RETRIES", 1)
    monkeypatch.setattr(dcv_broker, "SLEEP_SECONDS", 1)
    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: "provider_url")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        subprocess, "getoutput", lambda _: ["provider_url/.well-known/jwks.json"]
    )

    dcv_broker.configure_dcv_broker()


def test_configure_dcv_broker_fail_raise_exception(monkeypatch):
    monkeypatch.setattr(dcv_broker, "MAX_RETRIES", 1)
    monkeypatch.setattr(dcv_broker, "SLEEP_SECONDS", 1)
    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: "provider_url")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(subprocess, "getoutput", lambda _: [])

    with pytest.raises(Exception) as excinfo:
        dcv_broker.configure_dcv_broker()
    assert str(excinfo.value) == "DCV Broker configuration failed."


def test_verify_broker_installation_succeed(monkeypatch):
    monkeypatch.setattr(dcv_broker, "MAX_RETRIES", 1)
    monkeypatch.setattr(dcv_broker, "SLEEP_SECONDS", 1)
    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: 8443)
    monkeypatch.setattr(
        requests, "get", lambda *args, **kwargs: Response("No authorization header")
    )

    dcv_broker.verify_broker_installation()


def test_verify_broker_installation_fail_raise_exception(monkeypatch):
    monkeypatch.setattr(dcv_broker, "MAX_RETRIES", 1)
    monkeypatch.setattr(dcv_broker, "SLEEP_SECONDS", 1)
    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: 8443)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: Response(""))

    with pytest.raises(Exception) as excinfo:
        dcv_broker.verify_broker_installation()
    assert str(excinfo.value) == "Failed to validate DCV Broker installation."
