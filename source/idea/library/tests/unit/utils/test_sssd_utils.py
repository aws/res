#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest.mock import ANY, Mock, call, patch

import pytest
from res.constants import MODULE_NAME_VIRTUAL_DESKTOP_APP
from res.resources import cluster_settings
from res.utils import sssd_utils
from res.utils.sssd_utils import SSSDConfigEventSubscriber

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

sudo_provider = none
ldap_sasl_authid = ldap_sasl_authid"""

SSSD_CONFIG_EVENT_SUBSCRIBER = SSSDConfigEventSubscriber(Mock())

ENTRY_WITH_DOMAIN_NAME_KEY = {
    "key": "directoryservice.name",
    "value": "value",
}
ENTRY_WITH_ADDITIONAL_SSSD_CONFIGS_KEY = {
    "key": "directoryservice.sssd.additional_sssd_configs",
    "value": "value",
}
ENTRY_WITH_NON_SSSD_KEY = {
    "key": "test",
    "value": "value",
}
OLD_ENTRY_WITH_DOMAIN_NAME_KEY = {
    "key": "directoryservice.name",
    "value": "old_value",
}

CURRENT_SSSD_SETTINGS = {
    "domain_name": "value",
    "ldap_connection_uri": "value",
    "ldap_base": "value",
    "sssd_ldap_id_mapping": "value",
    "service_account_dn": "value",
    "service_account_credentials": "value",
    "tls_certificate": "value",
    "additional_sssd_configs": "value",
}


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
        sssd_utils._configure_ldap(sssd_settings)

    mock_open.assert_has_calls(
        [
            call("/etc/openldap/ldap.conf", "w"),
            call().__enter__(),
            call().__enter__().write("""TLS_CACERTDIR /etc/openldap/cacerts/

# Turning this off breaks GSSAPI used with krb5 when rdns = false
SASL_NOCANON	on

URI ldap_connection_uri

BASE ldap_base

TLS_CACERT /etc/openldap/cacerts/openldap-server.pem"""),
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
        sssd_utils._configure_ldap(sssd_settings)

    mock_open.assert_has_calls(
        [
            call("/etc/openldap/ldap.conf", "w"),
            call().__enter__(),
            call().__enter__().write("""TLS_CACERTDIR /etc/openldap/cacerts/

# Turning this off breaks GSSAPI used with krb5 when rdns = false
SASL_NOCANON	on

URI ldap_connection_uri

BASE ldap_base

TLS_CACERT /etc/openldap/cacerts/openldap-server.pem"""),
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
        sssd_utils._configure_sssd(sssd_settings)

    mock_open.assert_has_calls(
        [
            call("/etc/sssd/sssd.conf", "w"),
        ]
    )

    mock_config_parser.assert_has_calls(
        [
            call(interpolation=None),
            call().read_string(CONNECT_AD_SSSD_CONFIG),
            call().write(ANY),
        ]
    )

    mock_chmod.assert_has_calls(
        [
            call("/etc/sssd/sssd.conf", 0o600),
        ]
    )


def test_configure_sssd_while_disable_ad_join_is_true():

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open") as mock_open,
        patch("os.chmod") as mock_chmod,
        patch("subprocess.run") as mock_run,
        patch("configparser.ConfigParser") as mock_config_parser,
        patch("res.resources.cluster_settings.get_setting") as mock_get_cluster_setting,
        patch(
            "res.resources.ad_automation.get_authorization"
        ) as mock_get_authorization,
        patch.dict(os.environ, {"IDEA_MODULE_NAME": MODULE_NAME_VIRTUAL_DESKTOP_APP}),
    ):
        mock_run.return_value = MockProcess()
        mock_config_parser_instance = mock_config_parser.return_value
        mock_config_parser_instance.sections.return_value = [SSSD_DOMAIN_SECTION]
        mock_get_cluster_setting.return_value = "true"
        mock_get_authorization.return_value = {"hostname": "ldap_sasl_authid"}
        # with pytest.raises(Exception) as exc_info:
        sssd_utils._configure_sssd(
            SSSD_SETTINGS_WITH_ADDITIONAL_CONFIG,
        )

    mock_config_parser.assert_has_calls(
        [
            call(interpolation=None),
            call().read_string(CONNECT_AD_SSSD_CONFIG),
            call().write(ANY),
            call(interpolation=None),
            call().read("/etc/sssd/sssd.conf"),
            call().__getitem__(SSSD_DOMAIN_SECTION),
            call()
            .__getitem__(SSSD_DOMAIN_SECTION)
            .__setitem__("debug_level", "0xFFF0"),
            call().write(ANY),
        ]
    )


def test_configure_sssd_while_disable_ad_join_is_false():

    with (
        patch("pathlib.Path.mkdir"),
        patch("builtins.open") as mock_open,
        patch("os.chmod") as mock_chmod,
        patch("subprocess.run") as mock_run,
        patch("configparser.ConfigParser") as mock_config_parser,
        patch("res.resources.cluster_settings.get_setting") as mock_get_cluster_setting,
        patch(
            "res.resources.ad_automation.get_authorization"
        ) as mock_get_authorization,
        patch.dict(os.environ, {"IDEA_MODULE_NAME": MODULE_NAME_VIRTUAL_DESKTOP_APP}),
        patch(
            "res.utils.sssd_utils.is_in_active_directory"
        ) as mock_is_in_active_directory,
    ):
        mock_run.return_value = MockProcess()
        mock_config_parser_instance = mock_config_parser.return_value
        mock_config_parser_instance.sections.return_value = [SSSD_DOMAIN_SECTION]
        mock_get_cluster_setting.return_value = "false"
        mock_get_authorization.return_value = {"hostname": "ldap_sasl_authid"}
        mock_is_in_active_directory.return_value = False
        sssd_utils._configure_sssd(
            SSSD_SETTINGS_WITH_ADDITIONAL_CONFIG,
        )

    mock_config_parser.assert_has_calls(
        [
            call(interpolation=None),
            call().read_string(JOIN_AD_SSSSD_CONFIG),
            call().write(ANY),
            call(interpolation=None),
            call().read("/etc/sssd/sssd.conf"),
            call().__getitem__(SSSD_DOMAIN_SECTION),
            call()
            .__getitem__(SSSD_DOMAIN_SECTION)
            .__setitem__("debug_level", "0xFFF0"),
            call().write(ANY),
        ]
    )


def test_sssd_config_event_subscriber_required_ad_key_is_monitored(
    monkeypatch,
):
    assert SSSD_CONFIG_EVENT_SUBSCRIBER.is_entry_monitored(ENTRY_WITH_DOMAIN_NAME_KEY)


def test_sssd_config_event_subscriber_optional_ad_key_is_monitored(
    monkeypatch,
):
    assert SSSD_CONFIG_EVENT_SUBSCRIBER.is_entry_monitored(
        ENTRY_WITH_ADDITIONAL_SSSD_CONFIGS_KEY
    )


def test_sssd_config_event_subscriber_non_ad_key_skipped(
    monkeypatch,
):
    assert not SSSD_CONFIG_EVENT_SUBSCRIBER.is_entry_monitored(ENTRY_WITH_NON_SSSD_KEY)


def test_sssd_config_event_subscriber_on_create_restart_sssd(
    monkeypatch,
):
    restart_sssd_service_mock = Mock()
    monkeypatch.setattr(
        SSSD_CONFIG_EVENT_SUBSCRIBER, "restart_sssd_service", restart_sssd_service_mock
    )
    SSSD_CONFIG_EVENT_SUBSCRIBER.on_create(ENTRY_WITH_DOMAIN_NAME_KEY)
    restart_sssd_service_mock.assert_called_once()


def test_sssd_config_event_subscriber_on_update_restart_sssd(
    monkeypatch,
):
    restart_sssd_service_mock = Mock()
    monkeypatch.setattr(
        SSSD_CONFIG_EVENT_SUBSCRIBER, "restart_sssd_service", restart_sssd_service_mock
    )
    SSSD_CONFIG_EVENT_SUBSCRIBER.on_update(
        OLD_ENTRY_WITH_DOMAIN_NAME_KEY, ENTRY_WITH_DOMAIN_NAME_KEY
    )
    restart_sssd_service_mock.assert_called_once()


def test_sssd_config_event_subscriber_on_delete_skip(
    monkeypatch,
):
    restart_sssd_service_mock = Mock()
    monkeypatch.setattr(
        SSSD_CONFIG_EVENT_SUBSCRIBER, "restart_sssd_service", restart_sssd_service_mock
    )
    SSSD_CONFIG_EVENT_SUBSCRIBER.on_delete(ENTRY_WITH_DOMAIN_NAME_KEY)
    restart_sssd_service_mock.assert_called_once()


def test_restart_sssd_no_sssd_config_update_skip(
    monkeypatch,
):
    SSSD_CONFIG_EVENT_SUBSCRIBER.sssd_settings = CURRENT_SSSD_SETTINGS
    monkeypatch.setattr(cluster_settings, "get_setting", lambda x: "value")
    monkeypatch.setattr(cluster_settings, "get_secret", lambda x: "value")
    restart_sssd_mock = Mock()
    monkeypatch.setattr(sssd_utils, "restart_sssd", lambda: restart_sssd_mock)
    SSSD_CONFIG_EVENT_SUBSCRIBER.restart_sssd_service()
    restart_sssd_mock.assert_not_called()


def test_restart_sssd_sssd_config_updated_restart_sssd_service(
    monkeypatch,
):
    SSSD_CONFIG_EVENT_SUBSCRIBER.sssd_settings = None
    monkeypatch.setattr(cluster_settings, "get_setting", lambda x: "value")
    monkeypatch.setattr(cluster_settings, "get_secret", lambda x: "value")
    restart_sssd_mock = Mock()
    monkeypatch.setattr(sssd_utils, "restart_sssd", restart_sssd_mock)
    SSSD_CONFIG_EVENT_SUBSCRIBER.restart_sssd_service()
    restart_sssd_mock.assert_called_once()


def test_add_additional_sssd_configs_with_percent_in_value(tmp_path):
    """Verify that % characters in sssd.conf (e.g. fallback_homedir = /home/%u)
    do not cause configparser interpolation errors."""
    sssd_conf = tmp_path / "sssd.conf"
    sssd_conf.write_text(
        "[sssd]\n"
        "domains = test.com\n"
        "\n"
        "[domain/test.com]\n"
        "fallback_homedir = /home/%u\n"
    )

    sssd_settings = {
        "domain_name": "test.com",
        "additional_sssd_configs": '{"debug_level": "0xFFF0"}',
    }

    with patch.object(sssd_utils, "SSSD_FILE_PATH", str(sssd_conf)):
        sssd_utils._add_additional_sssd_configs(sssd_settings)

    content = sssd_conf.read_text()
    assert "fallback_homedir = /home/%u" in content
    assert "debug_level = 0xFFF0" in content


def test_add_additional_sssd_configs_with_percent_in_additional_value(tmp_path):
    """Verify that % characters in additional SSSD configs (e.g. fallback_homedir = /home/%d/%u)
    are preserved correctly."""
    sssd_conf = tmp_path / "sssd.conf"
    sssd_conf.write_text(
        "[sssd]\n"
        "domains = test.com\n"
        "\n"
        "[domain/test.com]\n"
        "id_provider = ad\n"
    )

    sssd_settings = {
        "domain_name": "test.com",
        "additional_sssd_configs": '{"fallback_homedir": "/home/%d/%u"}',
    }

    with patch.object(sssd_utils, "SSSD_FILE_PATH", str(sssd_conf)):
        sssd_utils._add_additional_sssd_configs(sssd_settings)

    content = sssd_conf.read_text()
    assert "fallback_homedir = /home/%d/%u" in content
