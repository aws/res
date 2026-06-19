#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
import requests
from res.utils import instance_metadata_utils


def test_get_imds_auth_header_return_header(monkeypatch):
    monkeypatch.setattr(instance_metadata_utils, "get_imds_auth_token", lambda: "token")

    assert (
        instance_metadata_utils.get_imds_auth_header().get("X-aws-ec2-metadata-token")
        == "token"
    )


def test_get_imds_auth_token_error_status_code_raise_exception(monkeypatch):
    error_response = requests.Response()
    error_response.status_code = 500
    monkeypatch.setattr(requests, "put", lambda _, headers: error_response)

    with pytest.raises(Exception) as exc_info:
        instance_metadata_utils.get_imds_auth_token()
    assert (
        "Failed to retrieve EC2 instance IMDSv2 authentication token"
        in exc_info.value.args[0]
    )


def test_get_imds_auth_token_success_status_code_return_token(monkeypatch):
    success_response = requests.Response()
    success_response.status_code = 200
    success_response._content = b"token"

    monkeypatch.setattr(requests, "put", lambda _, headers: success_response)

    assert instance_metadata_utils.get_imds_auth_token() == "token"


def test_get_instance_id_error_status_code_raise_exception(monkeypatch):
    error_response = requests.Response()
    error_response.status_code = 500
    monkeypatch.setattr(requests, "get", lambda _, headers, timeout: error_response)
    monkeypatch.setattr(instance_metadata_utils, "get_imds_auth_header", lambda: None)

    with pytest.raises(Exception) as exc_info:
        instance_metadata_utils.get_instance_id()
    assert "Failed to get instance ID" in exc_info.value.args[0]


def test_get_instance_id_success_status_code_return_instance_id(monkeypatch):
    success_response = requests.Response()
    success_response.status_code = 200
    success_response._content = b"instance_id"

    monkeypatch.setattr(requests, "get", lambda _, headers, timeout: success_response)
    monkeypatch.setattr(instance_metadata_utils, "get_imds_auth_header", lambda: None)

    assert instance_metadata_utils.get_instance_id() == "instance_id"


def test_get_private_dns_name_error_status_code_raise_exception(monkeypatch):
    error_response = requests.Response()
    error_response.status_code = 500
    monkeypatch.setattr(requests, "get", lambda _, headers, timeout: error_response)
    monkeypatch.setattr(instance_metadata_utils, "get_imds_auth_header", lambda: None)

    with pytest.raises(Exception) as exc_info:
        instance_metadata_utils.get_private_dns_name()
    assert "Failed to get private DNS name" in exc_info.value.args[0]


def test_get_private_dns_name_success_status_code_return_dns_name(monkeypatch):
    success_response = requests.Response()
    success_response.status_code = 200
    success_response._content = b"ip-10-0-1-5.ec2.internal"

    monkeypatch.setattr(requests, "get", lambda _, headers, timeout: success_response)
    monkeypatch.setattr(instance_metadata_utils, "get_imds_auth_header", lambda: None)

    assert instance_metadata_utils.get_private_dns_name() == "ip-10-0-1-5.ec2.internal"
