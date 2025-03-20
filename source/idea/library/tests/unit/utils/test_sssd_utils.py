#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from unittest.mock import ANY, call, patch

import pytest
from res.constants import MODULE_ID_CLUSTER_MANAGER, MODULE_ID_VIRTUAL_DESKTOP_APP
from res.utils import sssd_utils

SSSD_SETTINGS_WITH_ADDITIONAL_CONFIG = {
    "domain_name": "domain_name",
    "ldap_connection_uri": "ldap_connection_uri",
    "ldap_base": "ldap_base",
    "sssd_ldap_id_mapping": "true",
    "service_account_dn": "service_account_dn",
    "service_account_credentials": """{"username": "password"}""",
    "additional_sssd_configs": '{"debug_level":"0xFFF0"}',
}

SSSD_DOMAIN_SECTION = "domain/domain_name"

CONNECT_AD_SSSD_CONFIG = """[sssd]
domains = domain_name
config_file_version = 2
services = nss, pam

[nss]
homedir_substring = /home/

[pam]

[autofs]

[ssh]

[secrets]

[domain/domain_name]
id_provider = ldap
auth_provider = ldap
sudo_provider = none

ldap_uri = ldap_connection_uri

ldap_search_base = ldap_base
ldap_schema = ad
use_fully_qualified_names = false
case_sensitive = False

ldap_user_object_class = user
ldap_user_name = sAMAccountName
ldap_user_uid_number = uidNumber
ldap_user_gid_number = gidNumber
ldap_user_home_directory = unixHomeDirectory
ldap_user_shell = loginShell
ldap_user_uuid = objectGUID

ldap_group_object_class = group
ldap_group_name = sAMAccountName
ldap_group_gid_number = gidNumber
ldap_group_member = member
ldap_group_uuid = objectGUID

ldap_default_bind_dn = service_account_dn

enumerate = true
ldap_id_mapping = true

cache_credentials = true

default_shell = /bin/bash
fallback_homedir = /home/%u"""

JOIN_AD_SSSSD_CONFIG = """[sssd]
domains = domain_name
config_file_version = 2
services = nss, pam

[nss]
homedir_substring = /home/

[pam]

[autofs]

[ssh]

[secrets]

[domain/domain_name]
ad_domain = domain_name

krb5_realm = domain_name
realmd_tags = manages-system joined-with-adcli
cache_credentials = true
id_provider = ad
access_provider = ad
auth_provider = ad
chpass_provider = ad
krb5_store_password_if_offline = true
default_shell = /bin/bash

ldap_id_mapping = true

use_fully_qualified_names = false
fallback_homedir = /home/%u

enumerate = true

sudo_provider = none
ldap_sasl_authid = ldap_sasl_authid"""


class MockProcess:
    returncode: int = 0


def test_is_sssd_setting_non_directoryservice_key_returns_false():
    assert not sssd_utils.is_sssd_setting("test")


def test_is_sssd_setting_non_sssd_related_key_returns_false():
    assert not sssd_utils.is_sssd_setting(
        f"{sssd_utils.DIRECTORY_SERVICE_KEY_PREFIX}.test"
    )


def test_is_sssd_setting_sssd_related_key_returns_true():
    assert sssd_utils.is_sssd_setting(sssd_utils.DOMAIN_NAME_KEY)


def test_validate_additional_sssd_configs_includes_reserved_key_throw_exception():
    configs = {"id_provider": "test"}
    with pytest.raises(Exception) as exc_info:
        sssd_utils.validate_additional_sssd_configs(configs)
    assert (
        "Additional SSSD configs cannot include RES reserved key id_provider"
        in exc_info.value.args[0]
    )


def test_validate_additional_sssd_configs_valid_configs_pass():
    configs = {"debug_level": "0"}
    sssd_utils.validate_additional_sssd_configs(configs)


def test_configure_ldap_write_ldap_config():
    sssd_settings = {
        "ldap_connection_uri": "ldap_connection_uri",
        "ldap_base": "ldap_base",
    }

    with patch("pathlib.Path.mkdir"), patch("builtins.open") as mock_open:
        sssd_utils._configure_ldap(sssd_settings, logging.getLogger("test"))

    mock_open.assert_has_calls(
        [
            call("/etc/openldap/ldap.conf", "w"),
            call().__enter__(),
            call()
            .__enter__()
            .write(
                """TLS_CACERTDIR /etc/openldap/cacerts/

# Turning this off breaks GSSAPI used with krb5 when rdns = false
SASL_NOCANON	on

URI ldap_connection_uri

BASE ldap_base

TLS_CACERT /etc/openldap/cacerts/openldap-server.pem"""
            ),
            call().__exit__(None, None, None),
        ]
    )


def test_configure_ldap_with_tls_cert_write_ldap_config():
    sssd_settings = {
        "ldap_connection_uri": "ldap_connection_uri",
        "ldap_base": "ldap_base",
        "tls_certificate": "test",
    }

    with patch("pathlib.Path.mkdir"), patch("builtins.open") as mock_open:
        sssd_utils._configure_ldap(sssd_settings, logging.getLogger("test"))

    mock_open.assert_has_calls(
        [
            call("/etc/openldap/ldap.conf", "w"),
            call().__enter__(),
            call()
            .__enter__()
            .write(
                """TLS_CACERTDIR /etc/openldap/cacerts/

# Turning this off breaks GSSAPI used with krb5 when rdns = false
SASL_NOCANON	on

URI ldap_connection_uri

BASE ldap_base

TLS_CACERT /etc/openldap/cacerts/openldap-server.pem"""
            ),
            call().__exit__(None, None, None),
        ]
    )

    mock_open.assert_has_calls(
        [
            call("/etc/openldap/cacerts/openldap-server.pem", "w"),
            call().__enter__(),
            call().__enter__().write("test"),
            call().__exit__(None, None, None),
        ]
    )


def test_configure_sssd_write_sssd_config():
    sssd_settings = {
        "domain_name": "domain_name",
        "ldap_connection_uri": "ldap_connection_uri",
        "ldap_base": "ldap_base",
        "sssd_ldap_id_mapping": "true",
        "service_account_dn": "service_account_dn",
        "service_account_credentials": """{"username": "password"}""",
    }

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open") as mock_open,
        patch("os.chmod") as mock_chmod,
        patch("subprocess.run") as mock_run,
        patch("configparser.ConfigParser") as mock_config_parser,
        patch("res.resources.cluster_settings.get_setting") as mock_get_cluster_setting,
    ):
        mock_run.return_value = MockProcess()
        mock_get_cluster_setting.return_value = "true"
        sssd_utils._configure_sssd(
            sssd_settings, logging.getLogger("test"), MODULE_ID_CLUSTER_MANAGER
        )

    mock_open.assert_has_calls(
        [
            call("/etc/sssd/sssd.conf", "w"),
        ]
    )

    mock_config_parser.assert_has_calls(
        [
            call(),
            call().read("/etc/sssd/sssd.conf"),
            call().sections(),
            call().sections().__iter__(),
            call(),
            call().read_string(CONNECT_AD_SSSD_CONFIG),
            call().write(ANY),
        ]
    )

    mock_chmod.assert_has_calls(
        [
            call("/etc/sssd/sssd.conf", 0o600),
        ]
    )


def test_configure_sssd_write_sssd_config_with_additional_sssd_configs():

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open") as mock_open,
        patch("os.chmod") as mock_chmod,
        patch("subprocess.run") as mock_run,
        patch("configparser.ConfigParser") as mock_config_parser,
        patch("res.resources.cluster_settings.get_setting") as mock_get_cluster_setting,
    ):
        mock_run.return_value = MockProcess()
        mock_get_cluster_setting.return_value = "false"
        sssd_utils._configure_sssd(
            SSSD_SETTINGS_WITH_ADDITIONAL_CONFIG,
            logging.getLogger("test"),
            MODULE_ID_CLUSTER_MANAGER,
        )

    mock_config_parser.assert_has_calls(
        [
            call()
            .__getitem__(SSSD_DOMAIN_SECTION)
            .__setitem__("debug_level", "0xFFF0"),
        ]
    )


def test_configure_sssd_for_connect_ad_vdi_while_disable_ad_join_is_false():

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open") as mock_open,
        patch("os.chmod") as mock_chmod,
        patch("subprocess.run") as mock_run,
        patch("configparser.ConfigParser") as mock_config_parser,
        patch("res.resources.cluster_settings.get_setting") as mock_get_cluster_setting,
    ):
        mock_run.return_value = MockProcess()
        mock_config_parser_instance = mock_config_parser.return_value
        mock_config_parser_instance.sections.return_value = [SSSD_DOMAIN_SECTION]
        mock_config_parser_instance.__getitem__.return_value = {
            "id_provider": "ldap",
        }
        mock_get_cluster_setting.return_value = "false"
        with pytest.raises(Exception) as exc_info:
            sssd_utils._configure_sssd(
                SSSD_SETTINGS_WITH_ADDITIONAL_CONFIG,
                logging.getLogger("test"),
                MODULE_ID_VIRTUAL_DESKTOP_APP,
            )
        assert (
            "SSSD config cannot be updated for connect AD VDI while disable_ad_join is false"
            in exc_info.value.args[0]
        )

    mock_config_parser.assert_has_calls(
        [
            call(),
            call().read("/etc/sssd/sssd.conf"),
            call().sections(),
            call().__getitem__(SSSD_DOMAIN_SECTION),
        ]
    )


def test_configure_sssd_for_join_ad_vdi_while_disable_ad_join_is_true():

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open") as mock_open,
        patch("os.chmod") as mock_chmod,
        patch("subprocess.run") as mock_run,
        patch("configparser.ConfigParser") as mock_config_parser,
        patch("res.resources.cluster_settings.get_setting") as mock_get_cluster_setting,
    ):
        mock_run.return_value = MockProcess()
        mock_config_parser_instance = mock_config_parser.return_value
        mock_config_parser_instance.sections.return_value = [SSSD_DOMAIN_SECTION]
        mock_config_parser_instance.__getitem__.return_value = {
            "id_provider": "ad",
            "ldap_sasl_authid": "ldap_sasl_authid",
        }
        mock_get_cluster_setting.return_value = "true"
        # with pytest.raises(Exception) as exc_info:
        sssd_utils._configure_sssd(
            SSSD_SETTINGS_WITH_ADDITIONAL_CONFIG,
            logging.getLogger("test"),
            MODULE_ID_VIRTUAL_DESKTOP_APP,
        )

    mock_config_parser.assert_has_calls(
        [
            call(),
            call().read("/etc/sssd/sssd.conf"),
            call().sections(),
            call().__getitem__(SSSD_DOMAIN_SECTION),
            call().__getitem__(SSSD_DOMAIN_SECTION),
            call(),
            call().read_string(CONNECT_AD_SSSD_CONFIG),
            call().__getitem__(SSSD_DOMAIN_SECTION),
            call().write(ANY),
        ]
    )


def test_configure_sssd_for_join_ad_vdi_while_disable_ad_join_is_false():

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open") as mock_open,
        patch("os.chmod") as mock_chmod,
        patch("subprocess.run") as mock_run,
        patch("configparser.ConfigParser") as mock_config_parser,
        patch("res.resources.cluster_settings.get_setting") as mock_get_cluster_setting,
    ):
        mock_run.return_value = MockProcess()
        mock_config_parser_instance = mock_config_parser.return_value
        mock_config_parser_instance.sections.return_value = [SSSD_DOMAIN_SECTION]
        mock_config_parser_instance.__getitem__.return_value = {
            "id_provider": "ad",
            "ldap_sasl_authid": "ldap_sasl_authid",
        }
        mock_get_cluster_setting.return_value = "false"
        sssd_utils._configure_sssd(
            SSSD_SETTINGS_WITH_ADDITIONAL_CONFIG,
            logging.getLogger("test"),
            MODULE_ID_VIRTUAL_DESKTOP_APP,
        )

    mock_config_parser.assert_has_calls(
        [
            call(),
            call().read("/etc/sssd/sssd.conf"),
            call().sections(),
            call().__getitem__(SSSD_DOMAIN_SECTION),
            call().__getitem__(SSSD_DOMAIN_SECTION),
            call(),
            call().read_string(JOIN_AD_SSSSD_CONFIG),
            call().__getitem__(SSSD_DOMAIN_SECTION),
            call().write(ANY),
        ]
    )


def test_configure_sssd_for_cognito_vdi_while_disable_ad_join_is_false():

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open") as mock_open,
        patch("os.chmod") as mock_chmod,
        patch("subprocess.run") as mock_run,
        patch("configparser.ConfigParser") as mock_config_parser,
        patch("res.resources.cluster_settings.get_setting") as mock_get_cluster_setting,
    ):
        mock_run.return_value = MockProcess()
        mock_config_parser_instance = mock_config_parser.return_value
        mock_config_parser_instance.sections.return_value = []
        mock_get_cluster_setting.return_value = "false"
        with pytest.raises(Exception) as exc_info:
            sssd_utils._configure_sssd(
                SSSD_SETTINGS_WITH_ADDITIONAL_CONFIG,
                logging.getLogger("test"),
                MODULE_ID_VIRTUAL_DESKTOP_APP,
            )
        assert (
            "SSSD Config cannot be updated for Congito user launched VDI while disable_ad_join is false"
            in exc_info.value.args[0]
        )

    mock_config_parser.assert_has_calls(
        [
            call(),
            call().read("/etc/sssd/sssd.conf"),
            call().sections(),
        ]
    )
