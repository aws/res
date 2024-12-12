#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import subprocess
from logging import Logger
from pathlib import Path
from string import Template
from typing import Dict

DIRECTORY_SERVICE_KEY_PREFIX = "directoryservice."
TLS_CERTIFICATE_SECRET_KEY = f"{DIRECTORY_SERVICE_KEY_PREFIX}tls_certificate_secret_arn"
LDAP_CONNECTION_URI_KEY = f"{DIRECTORY_SERVICE_KEY_PREFIX}ldap_connection_uri"
LDAP_BASE_KEY = f"{DIRECTORY_SERVICE_KEY_PREFIX}ldap_base"
DOMAIN_NAME_KEY = f"{DIRECTORY_SERVICE_KEY_PREFIX}name"
SSSD_LDAP_ID_MAPPING = f"{DIRECTORY_SERVICE_KEY_PREFIX}sssd.ldap_id_mapping"
SERVICE_ACCOUNT_DN_SECRET_KEY = f"{DIRECTORY_SERVICE_KEY_PREFIX}root_user_dn_secret_arn"
SERVICE_ACCOUNT_CREDENTIALS_KEY = (
    f"{DIRECTORY_SERVICE_KEY_PREFIX}service_account_credentials_secret_arn"
)

SSSD_SETTING_KEY_MAPPINGS = {
    "domain_name": DOMAIN_NAME_KEY,
    "ldap_connection_uri": LDAP_CONNECTION_URI_KEY,
    "ldap_base": LDAP_BASE_KEY,
    "sssd_ldap_id_mapping": SSSD_LDAP_ID_MAPPING,
    "service_account_dn": SERVICE_ACCOUNT_DN_SECRET_KEY,
    "service_account_credentials": SERVICE_ACCOUNT_CREDENTIALS_KEY,
    "tls_certificate": TLS_CERTIFICATE_SECRET_KEY,
}

LDAP_CONFIG_TEMPLATE = Template(
    """TLS_CACERTDIR $tls_ca_cert_dir

# Turning this off breaks GSSAPI used with krb5 when rdns = false
SASL_NOCANON	on

URI $ldap_connection_uri

BASE $ldap_base

TLS_CACERT $tls_ca_cert_file_path"""
)

SSSD_CONFIG_TEMPLATE = Template(
    """[sssd]
domains = $domain_name
config_file_version = 2
services = nss, pam

[nss]
homedir_substring = /home/

[pam]

[autofs]

[ssh]

[secrets]

[domain/$domain_name]
id_provider = ldap
auth_provider = ldap
sudo_provider = none

ldap_uri = $ldap_connection_uri

ldap_search_base = $ldap_base
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

ldap_default_bind_dn = $service_account_dn

enumerate = true
ldap_id_mapping = $sssd_ldap_id_mapping

cache_credentials = true

default_shell = /bin/bash
fallback_homedir = /home/%u"""
)

OPEN_LDAP_DIR = "/etc/openldap/"
TLS_CA_CERT_DIR = f"{OPEN_LDAP_DIR}cacerts/"
TLS_CA_CERT_FILE_PATH = f"{TLS_CA_CERT_DIR}openldap-server.pem"


def is_sssd_setting(key: str) -> bool:
    return (
        key.startswith(DIRECTORY_SERVICE_KEY_PREFIX)
        and key in SSSD_SETTING_KEY_MAPPINGS.values()
    )


def start_sssd(sssd_settings: Dict[str, str], logger: Logger) -> None:
    if not sssd_settings:
        # Required SSSD settings are not provided yet. There's no need to start the SSSD service.
        return
    _configure_sssd(sssd_settings, logger)

    logger.info("Starting SSSD service")

    subprocess.check_call("/usr/sbin/sssd", shell=True, stdout=subprocess.PIPE)

    logger.info("Started SSSD service successfully")


def restart_sssd(sssd_settings: Dict[str, str], logger: Logger) -> None:
    if not sssd_settings:
        # Required SSSD settings are not provided yet. There's no need to start the SSSD service.
        return
    _configure_sssd(sssd_settings, logger)

    logger.info("Restarting SSSD service")

    subprocess.check_call(
        "sudo systemctl restart sssd", shell=True, stdout=subprocess.PIPE
    )

    logger.info("Restarted SSSD service successfully")


def _configure_sssd(sssd_settings: Dict[str, str], logger: Logger) -> None:
    _configure_ldap(sssd_settings, logger)

    logger.info("Updating SSSD config")

    service_account_credentials_secret = json.loads(
        sssd_settings["service_account_credentials"]
    )
    service_account_password = list(service_account_credentials_secret.values())[0]

    sssd_conf_content = SSSD_CONFIG_TEMPLATE.substitute(**sssd_settings)

    sssd_dir = "/etc/sssd"
    Path(sssd_dir).mkdir(parents=True, exist_ok=True)
    with open(f"{sssd_dir}/sssd.conf", "w") as f:
        f.write(sssd_conf_content)

    os.chmod(f"{sssd_dir}/sssd.conf", 0o600)

    process = subprocess.run(
        ["sss_obfuscate", "--domain", sssd_settings["domain_name"], "-s"],
        stdout=subprocess.PIPE,
        input=service_account_password,
        encoding="ascii",
    )
    if process.returncode != 0:
        raise Exception(
            f"Failed to obfuscate service account password: stderr: {process.stderr}, stdout: {process.stdout}"
        )

    logger.info("Updated SSSD config successfully")


def _configure_ldap(sssd_settings: Dict[str, str], logger: Logger) -> None:
    logger.info("Updating ldap config")

    sssd_settings["tls_ca_cert_dir"] = TLS_CA_CERT_DIR
    sssd_settings["tls_ca_cert_file_path"] = TLS_CA_CERT_FILE_PATH

    ldap_conf_content = LDAP_CONFIG_TEMPLATE.substitute(**sssd_settings)

    Path(OPEN_LDAP_DIR).mkdir(parents=True, exist_ok=True)
    with open(f"{OPEN_LDAP_DIR}ldap.conf", "w") as f:
        f.write(ldap_conf_content)

    if sssd_settings.get("tls_certificate"):
        Path(TLS_CA_CERT_DIR).mkdir(parents=True, exist_ok=True)
        with open(TLS_CA_CERT_FILE_PATH, "w") as f:
            f.write(sssd_settings["tls_certificate"].rstrip())

    logger.info("Updated ldap config successfully")
