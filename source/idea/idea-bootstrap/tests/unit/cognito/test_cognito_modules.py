#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideabootstrap.common.cognito_modules import (_modify_pam_file,
    _setup_cognito_config_file, _start_nscd, _setup_pam_config_file_ubuntu,
)
import pytest
import os
import sys
from unittest.mock import Mock, mock_open, call
import re

from typing import Any

from res.resources import cluster_settings
import res.constants as res_constants

def mock_isfile(path):
    mock_existing_paths = [
        '/etc/os-release',
        '/usr/lib/os-release',
        '/etc/cognito_auth.conf',
        '/etc/nsswitch.conf'
    ]

    return path in mock_existing_paths

def mock_exists(path):
    mock_existing_paths = [
        '/etc',
        '/etc/cognito_auth.conf',
        '/opt',
        '/opt/cognito_auth'
    ]
    return path in mock_existing_paths

def generate_cognito_conf_file():
    return """
    # Cognito authorizer configuration file
user_pool_id = us-east-2_A7XgmEdaI
client_id = 5gjni1g2sfqmch8alkg030f375
aws_access_key_id =
aws_secret_access_key =
aws_region = us-east-2

cognito_default_user_group = res
cognito_uid_attribute = custom:uid
min_id = 2000200001
max_id = 4294967294
nss_cache_timeout_s = 60
nss_cache_path = /opt/cognito_auth/cache.json
    """

@pytest.mark.parametrize(
    "base_os, setup_function",
    [
        ("ubuntu2204", "_setup_pam_config_file_ubuntu"),
        ("ubuntu2404", "_setup_pam_config_file_ubuntu"),
        ("rhel8", "_setup_pam_config_file_redhat_distros"),
        ("amzn2", "_setup_pam_config_file_redhat_distros"),
    ],
)
def test_cognito_modules_configure(monkeypatch, base_os, setup_function, tmp_path):
    from ideabootstrap.common.cognito_modules import configure

    monkeypatch.setattr(sys, 'exit', lambda x: None)
    monkeypatch.setattr(os.path, 'isfile', mock_isfile)
    monkeypatch.setattr(os.path, 'exists', mock_exists)

    monkeypatch.setenv('RES_BASE_OS', base_os)

    monkeypatch.setattr('os.chmod', Mock())
    monkeypatch.setattr(os, 'mkdir', Mock())

    mock_setup_ubuntu = Mock()
    mock_setup_redhat = Mock()
    mock_setup_config = Mock()
    mock_setup_nss = Mock()
    mock_start_nscd = Mock()
    mock_subprocess_run = Mock()
    mock_set_reboot = Mock()
    mock_logger = Mock()
    mock_datetime = Mock()
    mock_now = Mock()
    mock_set_reboot_required = Mock()
    mock_get_base_os = Mock(return_value=base_os)


     # Try all possible import paths to ensure we catch the right one
    monkeypatch.setattr("ideabootstrap.common.cognito_modules._setup_pam_config_file_ubuntu", mock_setup_ubuntu)
    monkeypatch.setattr("ideabootstrap.common.cognito_modules._setup_pam_config_file_redhat_distros", mock_setup_redhat)
    monkeypatch.setattr("ideabootstrap.common.cognito_modules._setup_cognito_config_file", mock_setup_config)
    monkeypatch.setattr("ideabootstrap.common.cognito_modules._setup_nss", mock_setup_nss)
    monkeypatch.setattr("ideabootstrap.common.cognito_modules._start_nscd", mock_start_nscd)
    monkeypatch.setattr("ideabootstrap.common.cognito_modules.logger", mock_logger)
    monkeypatch.setattr("ideabootstrap.common.cognito_modules.set_reboot_required", mock_set_reboot_required)
    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    def mock_get_setting(setting: str) -> Any:
        if setting == "identity-provider.cognito.enable_native_user_login":
            return True
        else:
            return ""
    monkeypatch.setattr(cluster_settings, "get_setting", mock_get_setting)

    configure()

    if base_os == "ubuntu2204" or base_os == "ubuntu2404" :
        mock_setup_ubuntu.assert_called_once()
        mock_setup_redhat.assert_not_called()
    elif base_os in ['amzn2', 'amzn2023', 'rhel8', 'rhel9', 'rocky9']:
        mock_setup_ubuntu.assert_not_called()
        mock_setup_redhat.assert_called_once()

    mock_setup_config.assert_called_once()
    mock_setup_nss.assert_called_once()
    mock_start_nscd.assert_called_once()


@pytest.mark.parametrize(
    "base_os, setup_function",
    [
        ("ubuntu2204", "_setup_pam_config_file_ubuntu"),
        ("amzn2", "_setup_pam_config_file_redhat_distros"),
    ],
)
def test_cognito_modules_native_user_login_disabled_skip_configure(monkeypatch, base_os, setup_function, tmp_path):
    from ideabootstrap.common.cognito_modules import configure

    monkeypatch.setenv('RES_BASE_OS', base_os)

    mock_setup_ubuntu = Mock()
    mock_setup_redhat = Mock()
    monkeypatch.setattr("ideabootstrap.common.cognito_modules._setup_pam_config_file_ubuntu", mock_setup_ubuntu)
    monkeypatch.setattr("ideabootstrap.common.cognito_modules._setup_pam_config_file_redhat_distros", mock_setup_redhat)

    def mock_get_setting(setting: str) -> Any:
        if setting == "identity-provider.cognito.enable_native_user_login":
            return False
        else:
            return ""
    monkeypatch.setattr(cluster_settings, "get_setting", mock_get_setting)

    configure()

    mock_setup_ubuntu.assert_not_called()
    mock_setup_redhat.assert_not_called()


def test_modify_pam_file_line_already_exists(monkeypatch) -> None:
    file_content = "auth    sufficient    pam_cognito.so\nauth    required    pam_unix.so\n"
    mock_file = mock_open(read_data=file_content)

    mock_search = Mock(return_value=True)

    mock_move = Mock()

    monkeypatch.setattr('builtins.open', mock_file)
    monkeypatch.setattr('re.search', mock_search)
    monkeypatch.setattr('shutil.move', mock_move)

    _modify_pam_file('/etc/pam.d/test-file', 'auth', 'auth\tsufficient\tpam_cognito.so')

    mock_file.assert_called_once_with('/etc/pam.d/test-file', 'r')

    mock_search.assert_called_once_with('^auth.*cognito',
                                       file_content,
                                       re.MULTILINE)

    mock_move.assert_not_called()
    handle = mock_file()
    handle.write.assert_not_called()

def test_modify_pam_file(monkeypatch, tmp_path):
    mock_logger = Mock()

    test_file = tmp_path / "test_pam.conf"
    original_content = "auth       required   pam_env.so\nauth       sufficient pam_unix.so\naccount    required   pam_unix.so\n"
    test_file.write_text(original_content)

    pattern = "auth"
    insert_line = "auth       sufficient pam_cognito.so"

    _modify_pam_file(str(test_file), 'account',  'account\tsufficient\tpam_cognito.so')
    _modify_pam_file(str(test_file), 'auth',  'auth\tsufficient\tpam_cognito.so')

    cognito_line_found = False
    modified_content = test_file.read_text()
    cognito_pattern = re.compile(r'^.*auth.*sufficient.*pam_cognito\.so.*$', re.MULTILINE)
    cognito_pattern_two = re.compile(r'^.*account.*sufficient.*pam_cognito\.so.*$', re.MULTILINE)

    assert cognito_pattern.search(modified_content), "Could not find a line with auth, sufficient, and pam_cognito.so"
    assert cognito_pattern_two.search(modified_content), "Could not find a line with auth, sufficient, and pam_cognito.so"


REQUIRED_ENV_VARS = {
    'USER': 'testuser',
    'AWS_REGION': 'us-west-2',
    'USER_POOL_ID': 'us-west-2_abcdef123',
    'VDI_CLIENT_ID': '1a2b3c4d5e6f7g8h9i0j',
}

def test_setup_cognito_config_file_basic(monkeypatch) -> None:
    for env_var in os.environ:
        monkeypatch.delenv(env_var, raising=False)

    for key, value in REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)

    mock_file = mock_open()
    mock_chmod = Mock()
    mock_logger = Mock()

    monkeypatch.setattr('builtins.open', mock_file)
    monkeypatch.setattr('os.chmod', mock_chmod)

    def mock_get_setting(setting: str) -> str:
        if setting == "identity-provider.cognito.user_pool_id":
            return os.environ.get("USER_POOL_ID")
        elif setting == "identity-provider.cognito.vdi_client_id":
            return os.environ.get("VDI_CLIENT_ID")
        else:
            return ""
    monkeypatch.setattr(cluster_settings, "get_setting", mock_get_setting)

    _setup_cognito_config_file()

    mock_file.assert_called_once_with('/etc/cognito_auth.conf', 'w')
    mock_chmod.assert_called_once_with('/etc/cognito_auth.conf', 0o644)

    handle = mock_file()
    written_content = ''.join([call.args[0] for call in handle.write.call_args_list])

    assert '# Cognito authorizer configuration file' in written_content
    assert f'user_pool_id = {os.environ.get("USER_POOL_ID")}' in written_content
    assert f'client_id = {os.environ.get("VDI_CLIENT_ID")}' in written_content
    assert 'aws_access_key_id =' in written_content
    assert 'aws_secret_access_key =' in written_content
    assert f'aws_region = {os.environ.get("AWS_REGION")}' in written_content
    assert f'cognito_default_user_group = {res_constants.COGNITO_DEFAULT_USER_GROUP}' in written_content
    assert f'cognito_uid_attribute = custom:{res_constants.COGNITO_UID_ATTRIBUTE}' in written_content
    assert f'min_id = {res_constants.COGNITO_MIN_ID_INCLUSIVE}' in written_content
    assert f'max_id = {res_constants.COGNITO_MAX_ID_INCLUSIVE}' in written_content
    assert 'nss_cache_timeout_s = 60' in written_content
    assert 'nss_cache_path = /opt/cognito_auth/cache.json' in written_content
    assert 'https_proxy' not in written_content

def test_start_nscd(monkeypatch):
    mock_run = Mock()
    monkeypatch.setattr('subprocess.run', mock_run)
    _start_nscd()
    expected_calls = [
        call(['systemctl', 'enable', 'nscd'], check=True),
        call(['systemctl', 'start', 'nscd'], check=True)
    ]
    assert mock_run.call_count == 2
    mock_run.assert_has_calls(expected_calls)

def test_setup_pam_config_file_ubuntu(monkeypatch):
    mock_modify_pam = Mock()
    monkeypatch.setattr('ideabootstrap.common.cognito_modules._modify_pam_file', mock_modify_pam)
    _setup_pam_config_file_ubuntu()

    expected_calls = [
        call('/etc/pam.d/common-auth', 'auth', 'auth\tsufficient\tpam_cognito.so'),
        call('/etc/pam.d/common-account', 'account', 'account\tsufficient\tpam_cognito.so')
    ]

    assert mock_modify_pam.call_count == 2
    mock_modify_pam.assert_has_calls(expected_calls)
