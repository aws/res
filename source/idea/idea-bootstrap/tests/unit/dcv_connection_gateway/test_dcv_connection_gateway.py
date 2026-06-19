#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import configparser
import subprocess
import tempfile

from ideabootstrap.dcv_connection_gateway import dcv_connection_gateway
from res.resources import cluster_settings


def test_dcv_connection_gateway_configure_succeed(monkeypatch):
    def mock_get(key: str):
        if key == "cluster.load_balancers.internal_alb.certificates.custom_dns_name":
            return "internal_alb_endpoint"

    monkeypatch.setattr(cluster_settings, "get_setting", mock_get)

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(dcv_connection_gateway, "_copy_static_resources", lambda: None)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(dcv_connection_gateway, "CONFIG_FILE", temp_file_name)

        dcv_connection_gateway.configure()

        config = configparser.ConfigParser()
        config.read(temp_file_name)

        assert config["log"]["level"] == '"trace"'

        assert (
            config["gateway"]["quic-listen-endpoints"]
            == '["0.0.0.0:8443", "[::]:8443"]'
        )
        assert (
            config["gateway"]["web-listen-endpoints"] == '["0.0.0.0:8443", "[::]:8443"]'
        )
        assert (
            config["gateway"]["cert-file"]
            == '"/etc/dcv-connection-gateway/certs/default_cert.pem"'
        )
        assert (
            config["gateway"]["cert-key-file"]
            == '"/etc/dcv-connection-gateway/certs/default_key_pkcs8.pem"'
        )

        assert config["health-check"]["bind-addr"] == '"::"'
        assert config["health-check"]["port"] == "8989"

        assert config["dcv"]["tls-strict"] == "false"

        assert (
            config["resolver"]["url"]
            == '"https://internal_alb_endpoint"'
        )
        assert config["resolver"]["tls-strict"] == "false"

        assert config["web-resources"]["local-resources-path"] == '"/usr/share/dcv/www"'
        assert config["web-resources"]["tls-strict"] == "false"
