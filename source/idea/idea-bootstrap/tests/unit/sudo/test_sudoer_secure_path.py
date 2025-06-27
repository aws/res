#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile

import pytest
from ideabootstrap.sudo import constants, sudoer_secure_path
from tests.unit.cognito.test_cognito_modules import mock_exists, mock_isfile
import sys
import os
from unittest.mock import mock_open, Mock
from string import Template

def generate_os_release_file(base_os, heading):
    return F"""
{heading}
NAME="Amazon Linux"
VERSION="2"
ID="{base_os}"
ID_LIKE="centos rhel fedora"
PRETTY_NAME="Amazon Linux 2"
ANSI_COLOR="0;33"
CPE_NAME="cpe:2.3:o:amazon:amazon_linux:2"
HOME_URL="https://amazonlinux.com/"
SUPPORT_END="2026-06-30"
"""


@pytest.mark.parametrize(
    "base_os, expected_content",
    [("rhel8", "Defaults secure_path"), 
    ("ubuntu", "")
    ],
)
def test_set_sudoer_secure_path(monkeypatch, base_os, expected_content) -> None:
    monkeypatch.setattr(sys, 'exit', lambda x: None)
    monkeypatch.setattr(os.path, 'isfile', mock_isfile)
    monkeypatch.setattr(os.path, 'exists', mock_exists)

    monkeypatch.setattr(sudoer_secure_path, 'get_base_os', lambda: base_os)

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file_name = temp_file.name

    def mock_overwrite_file(content, file_path, *args, **kwargs):
        with open(file_path, 'w') as f:
            f.write(content)

    monkeypatch.setattr(constants, "SUDOER_SECURE_PATH_FILE", temp_file_name)
    monkeypatch.setattr(sudoer_secure_path, 'overwrite_file', mock_overwrite_file)

    try:
        sudoer_secure_path.configure()

        with open(temp_file_name, "r") as f:
            content = f.read()

            if base_os in ("amzn2", "rhel8", "rhel9", "rocky9"):
                expected_line = f'Defaults secure_path="{constants.PATH}"'
                assert expected_line in content
            else:
                assert content == ""
    finally:
        if os.path.exists(temp_file_name):
            os.unlink(temp_file_name)


def test_set_sudoer_secure_custom_path(monkeypatch) -> None:
    monkeypatch.setattr(sys, 'exit', lambda x: None)
    monkeypatch.setattr(os.path, 'isfile', mock_isfile)
    monkeypatch.setattr(os.path, 'exists', mock_exists)

    monkeypatch.setattr(sudoer_secure_path, 'get_base_os', lambda: "rhel8")

    def mock_overwrite_file(content, file_path, *args, **kwargs):
        with open(file_path, 'w') as f:
            f.write(content)
    
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        test_path = "/test/path"
        monkeypatch.setattr(constants, "SUDOER_SECURE_PATH_FILE", temp_file_name)

        sudoer_secure_path.configure(test_path)

        with open(temp_file_name, "r") as f:
            content = f.read()
            assert "Defaults secure_path" in content
            assert test_path in content
            