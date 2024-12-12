#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from unittest.mock import call, patch

from res.utils import sssd_utils


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
    ):
        mock_run.return_value = MockProcess()
        sssd_utils._configure_sssd(sssd_settings, logging.getLogger("test"))

    mock_open.assert_has_calls(
        [
            call("/etc/sssd/sssd.conf", "w"),
            call().__enter__(),
            call()
            .__enter__()
            .write(
                """[sssd]
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
            ),
            call().__exit__(None, None, None),
        ]
    )

    mock_chmod.assert_has_calls(
        [
            call("/etc/sssd/sssd.conf", 0o600),
        ]
    )
