#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import grp
import os
import pwd
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock

from ideabootstrap.dcv_connection_gateway import certificates
from OpenSSL import crypto
from pydantic import BaseModel
from res.resources import cluster_settings


class User(BaseModel):
    pw_uid: int


class Group(BaseModel):
    gr_gid: int


def test_configure_certificates_succeed(monkeypatch):
    def mock_get(key: str):
        if key == "vdc.dcv_connection_gateway.certificate.certificate_secret_arn":
            return "certificate"
        elif key == "vdc.dcv_connection_gateway.certificate.private_key_secret_arn":
            return "pkcs1_private_key"

    monkeypatch.setattr(cluster_settings, "get_secret", mock_get)
    monkeypatch.setattr(crypto, "load_privatekey", lambda x, y: "")
    monkeypatch.setattr(crypto, "dump_privatekey", lambda x, y: b"pkcs8_private_key")
    monkeypatch.setattr(pwd, "getpwnam", lambda x: User(pw_uid=0))
    monkeypatch.setattr(grp, "getgrnam", lambda x: Group(gr_gid=1))
    monkeypatch.setattr(os, "chown", lambda x, y, z: None)

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        monkeypatch.setattr(
            certificates, "DCV_CONNECTION_GATEWAY_CERT_DIR", tmp_dir_name
        )

        certificates.configure_certificates()

        cert_dir = Path(tmp_dir_name)
        cert_path = cert_dir / "default_cert.pem"
        key_pkcs1_path = cert_dir / "default_key_pkcs1.pem"
        key_pkcs8_path = cert_dir / "default_key_pkcs8.pem"

        assert cert_path.is_file()
        assert key_pkcs1_path.is_file()
        assert key_pkcs8_path.is_file()

        cert_content = cert_path.read_text().strip()
        key_pkcs1_content = key_pkcs1_path.read_text().strip()
        key_pkcs8_content = key_pkcs8_path.read_text().strip()

        assert cert_content == "certificate"
        assert key_pkcs1_content == "pkcs1_private_key"
        assert key_pkcs8_content == "pkcs8_private_key"


def test_refresh_certificates_no_cert_update_ignore(monkeypatch):
    def mock_get(key: str):
        if key == "vdc.dcv_connection_gateway.certificate.certificate_secret_arn":
            return "certificate"
        elif key == "vdc.dcv_connection_gateway.certificate.private_key_secret_arn":
            return "pkcs1_private_key"

    monkeypatch.setattr(cluster_settings, "get_secret", mock_get)

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        monkeypatch.setattr(
            certificates, "DCV_CONNECTION_GATEWAY_CERT_DIR", tmp_dir_name
        )

        cert_dir = Path(tmp_dir_name)
        cert_path = cert_dir / "default_cert.pem"
        key_path = cert_dir / "default_key_pkcs1.pem"

        cert_path.write_text("certificate")
        key_path.write_text("pkcs1_private_key")

        configure_certificates_mock = Mock()
        monkeypatch.setattr(
            certificates, "configure_certificates", configure_certificates_mock
        )

        certificates._refresh_certificates()

        configure_certificates_mock.assert_not_called()


def test_refresh_certificates_certs_changed_update_certs(monkeypatch):
    def mock_get(key: str):
        if key == "vdc.dcv_connection_gateway.certificate.certificate_secret_arn":
            return "certificate"
        elif key == "vdc.dcv_connection_gateway.certificate.private_key_secret_arn":
            return "pkcs1_private_key"

    monkeypatch.setattr(cluster_settings, "get_secret", mock_get)

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        monkeypatch.setattr(
            certificates, "DCV_CONNECTION_GATEWAY_CERT_DIR", tmp_dir_name
        )

        cert_dir = Path(tmp_dir_name)
        cert_path = cert_dir / "default_cert.pem"
        key_path = cert_dir / "default_key_pkcs1.pem"

        cert_path.write_text("old_certificate")
        key_path.write_text("old_pkcs1_private_key")

        configure_certificates_mock = Mock()
        monkeypatch.setattr(
            certificates, "configure_certificates", configure_certificates_mock
        )

        certificates._refresh_certificates()

        configure_certificates_mock.assert_called_once()
