#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import configparser
import copy
import json
import os
import subprocess
from logging import Logger
from pathlib import Path
from string import Template
from typing import Dict, Optional

from res.constants import MODULE_NAME_CLUSTER_MANAGER, MODULE_NAME_VIRTUAL_DESKTOP_APP
from res.resources import ad_automation, cluster_settings
from res.resources.dynamodb.dynamodb_stream_subscriber import IDynamoDBStreamSubscriber
from res.utils import logging_utils

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
ADDITIONAL_SSSD_CONFIGS_PARTIAL_KEY = "sssd.additional_sssd_configs"
ADDITIONAL_SSSD_CONFIGS_KEY = (
    f"{DIRECTORY_SERVICE_KEY_PREFIX}{ADDITIONAL_SSSD_CONFIGS_PARTIAL_KEY}"
)
DISABLE_AD_JOIN_KEY = f"{DIRECTORY_SERVICE_KEY_PREFIX}disable_ad_join"

SSSD_SETTING_KEY_MAPPINGS = {
    "domain_name": DOMAIN_NAME_KEY,
    "ldap_connection_uri": LDAP_CONNECTION_URI_KEY,
    "ldap_base": LDAP_BASE_KEY,
    "sssd_ldap_id_mapping": SSSD_LDAP_ID_MAPPING,
    "service_account_dn": SERVICE_ACCOUNT_DN_SECRET_KEY,
    "service_account_credentials": SERVICE_ACCOUNT_CREDENTIALS_KEY,
    "tls_certificate": TLS_CERTIFICATE_SECRET_KEY,
    "additional_sssd_configs": ADDITIONAL_SSSD_CONFIGS_KEY,
}

RESERVED_SSSD_KEYS = [
    "id_provider",
    "ldap_uri",
    "ldap_search_base",
    "ldap_default_bind_dn",
    "ldap_default_authtok",
]

LDAP_CONFIG_TEMPLATE = Template("""TLS_CACERTDIR $tls_ca_cert_dir

# Turning this off breaks GSSAPI used with krb5 when rdns = false
SASL_NOCANON	on

URI $ldap_connection_uri

BASE $ldap_base

TLS_CACERT $tls_ca_cert_file_path""")


SSSD_JOIN_AD_CONFIG_TEMPLATE = Template("""[sssd]
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
ad_domain = $domain_name

krb5_realm = $domain_name
realmd_tags = manages-system joined-with-adcli
cache_credentials = true
id_provider = ad
access_provider = ad
auth_provider = ad
chpass_provider = ad
krb5_store_password_if_offline = true
default_shell = /bin/bash

ldap_id_mapping = $sssd_ldap_id_mapping

use_fully_qualified_names = false
fallback_homedir = /home/%u

sudo_provider = none
ldap_sasl_authid = $ldap_sasl_authid""")

SSSD_CONFIG_TEMPLATE = Template("""[sssd]
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

ldap_id_mapping = $sssd_ldap_id_mapping

cache_credentials = true

default_shell = /bin/bash
fallback_homedir = /home/%u""")

OPEN_LDAP_DIR = (
    "/etc/ldap/"
    if os.getenv("RES_BASE_OS", "").startswith("ubuntu")
    else "/etc/openldap/"
)
TLS_CA_CERT_DIR = f"{OPEN_LDAP_DIR}cacerts/"
TLS_CA_CERT_FILE_PATH = f"{TLS_CA_CERT_DIR}openldap-server.pem"

SSSD_DIR = "/etc/sssd"
SSSD_FILE_PATH = f"{SSSD_DIR}/sssd.conf"

logger = logging_utils.get_logger("sssd")


def is_sssd_setting(key: str) -> bool:
    return (
        key.startswith(DIRECTORY_SERVICE_KEY_PREFIX)
        and key in SSSD_SETTING_KEY_MAPPINGS.values()
    )


def validate_additional_sssd_configs(additional_sssd_configs: Dict[str, str]) -> None:
    for key in additional_sssd_configs:
        if key in RESERVED_SSSD_KEYS:
            raise Exception(
                f"Additional SSSD configs cannot include RES reserved key {key}"
            )


def get_sssd_settings() -> Optional[Dict[str, str]]:
    sssd_settings = {}
    for k, v in SSSD_SETTING_KEY_MAPPINGS.items():
        try:
            if v in [
                SERVICE_ACCOUNT_DN_SECRET_KEY,
                SERVICE_ACCOUNT_CREDENTIALS_KEY,
                TLS_CERTIFICATE_SECRET_KEY,
            ]:
                sssd_settings[k] = cluster_settings.get_secret(v)
            else:
                sssd_settings[k] = cluster_settings.get_setting(v)

            if not sssd_settings[k] and v != TLS_CERTIFICATE_SECRET_KEY:
                # Required SSSD related settings are not available yet
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve SSSD related settings: {e}")
            return None

    return sssd_settings


def start_sssd(sssd_settings: Dict[str, str]) -> None:
    if not sssd_settings:
        # Required SSSD settings are not provided yet. There's no need to start the SSSD service.
        return
    _configure_sssd(sssd_settings)

    logger.info("Starting SSSD service")

    subprocess.check_call("/usr/sbin/sssd", shell=True, stdout=subprocess.PIPE)

    logger.info("Started SSSD service successfully")


def restart_sssd(sssd_settings: Dict[str, str] = None) -> None:
    if not sssd_settings:
        sssd_settings = get_sssd_settings()

    if not sssd_settings:
        # Required SSSD settings are not provided yet. There's no need to start the SSSD service.
        logger.info("Required SSSD settings are not configured")
        return

    _configure_sssd(sssd_settings)

    logger.info("Restarting SSSD service")

    subprocess.check_call(
        ["sudo", "systemctl", "restart", "sssd"], stdout=subprocess.PIPE
    )

    logger.info("Restarted SSSD service successfully")


def _configure_sssd(sssd_settings: Dict[str, str]) -> None:
    _configure_ldap(sssd_settings)

    logger.info("Updating SSSD config")

    _construct_sssd_configs(sssd_settings)

    logger.info("Updated SSSD config successfully")


def _construct_sssd_configs(
    sssd_settings: Dict[str, str],
) -> None:
    disable_ad_join = (
        cluster_settings.get_setting(DISABLE_AD_JOIN_KEY) == "true"
        or os.environ.get("IDEA_MODULE_NAME") != MODULE_NAME_VIRTUAL_DESKTOP_APP
    )
    domain_section = f'domain/{sssd_settings["domain_name"]}'

    sasl_authid_key = "ldap_sasl_authid"
    if not disable_ad_join:
        if is_in_active_directory() and os.path.exists(SSSD_FILE_PATH):
            # Keep the special dynamic field ldap_sasl_authid from the old SSSD config if current host is joining AD
            config_origin = configparser.ConfigParser(interpolation=None)
            config_origin.read(SSSD_FILE_PATH)
            sssd_settings[sasl_authid_key] = config_origin[domain_section].get(
                sasl_authid_key
            )
        if not sssd_settings.get(sasl_authid_key):
            sssd_settings[sasl_authid_key] = ad_automation.get_authorization().get(
                "hostname"
            )

        # Use join AD template if for join-AD VDI and disable_ad_join is false
        sssd_conf_content = SSSD_JOIN_AD_CONFIG_TEMPLATE.substitute(**sssd_settings)
    # Use connect AD template for VDI when disable_ad_join is true and other infra host
    else:
        sssd_conf_content = SSSD_CONFIG_TEMPLATE.substitute(**sssd_settings)

    config_override = configparser.ConfigParser(interpolation=None)
    config_override.read_string(sssd_conf_content)

    Path(SSSD_DIR).mkdir(parents=True, exist_ok=True)
    with open(SSSD_FILE_PATH, "w") as configfile:
        config_override.write(configfile)

    os.chmod(SSSD_FILE_PATH, 0o600)

    if disable_ad_join:
        service_account_credentials_secret = json.loads(
            sssd_settings["service_account_credentials"]
        )
        service_account_password = list(service_account_credentials_secret.values())[0]

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

    # Make sure to add additional SSSD configs are after running the sss_obfuscate command.
    # Otherwise the additional SSSD configs will be overridden.
    _add_additional_sssd_configs(sssd_settings)


def _add_additional_sssd_configs(sssd_settings: Dict[str, str]) -> None:
    domain_section = f'domain/{sssd_settings["domain_name"]}'
    additional_sssd_configs = json.loads(
        sssd_settings.get("additional_sssd_configs", "{}")
    )
    if not additional_sssd_configs:
        return

    logger.info(f"Adding additional SSSD configs")

    sssd_config = configparser.ConfigParser(interpolation=None)
    sssd_config.read(SSSD_FILE_PATH)

    # Additional SSSD configs will be merged to the AD domain specific section by default
    for key, value in additional_sssd_configs.items():
        sssd_config[domain_section][key] = value

    with open(SSSD_FILE_PATH, "w") as configfile:
        sssd_config.write(configfile)


def is_in_active_directory() -> bool:
    cmd = [
        "realm",
        "list",
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return len(result.stdout.rstrip()) > 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to check whether the VDI has joined AD: {e.stderr}")
        return False


def _configure_ldap(sssd_settings: Dict[str, str]) -> None:
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


class SSSDConfigEventSubscriber(IDynamoDBStreamSubscriber):
    def __init__(
        self,
        logger_: Logger = None,
        module_id: str = None,
    ) -> None:
        self.logger = logger_ if logger_ else logger
        self.module_id = module_id
        self.sssd_settings = None

    def on_create(self, entry: Dict):
        self.restart_sssd_service()

    def on_update(self, old_entry: Dict, new_entry: Dict):
        value = new_entry.get("value")
        if value != old_entry.get("value"):
            self.restart_sssd_service()

    def on_delete(self, entry: Dict):
        self.restart_sssd_service()

    def is_entry_monitored(self, entry: Dict) -> bool:
        return is_sssd_setting(entry.get("key"))

    @property
    def subscriber_name(self) -> Optional[str]:
        return "sssd"

    def restart_sssd_service(self) -> None:
        sssd_settings = get_sssd_settings()
        if sssd_settings == self.sssd_settings:
            # SSSD config isn't changed. No need to restart SSSD
            return

        self.sssd_settings = copy.deepcopy(sssd_settings)
        try:
            restart_sssd(sssd_settings)
        except Exception as e:
            # Avoid throwing exceptions in the long-running application.
            # The application should continue monitoring and trying to restart SSSD upon SSSD config updates.
            self.logger.error(f"Failed to restart SSSD: {e}")
