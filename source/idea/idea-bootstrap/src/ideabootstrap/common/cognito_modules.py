#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import re
import subprocess
from res.utils import logging_utils
import res.constants as constants
from res.resources import cluster_settings
from ideabootstrap.bootstrap_common import set_reboot_required, get_base_os

logger = logging_utils.get_logger("bootstrap")

def _modify_pam_file(file_path, pattern, insert_line):
    with open(file_path, 'r') as f:
        content = f.read()

    if re.search(f"^{pattern}.*cognito", content, re.MULTILINE):
        logger.info("Line already exists")
        return  # Line already exists

    temp = ''
    with open(file_path, 'r') as original:
        done = False
        for line in original:
            if not done and line.startswith(pattern):
                temp += f"{insert_line}\n"
                done = True
            temp += line

    with open(file_path, 'w') as f:
        f.write(temp)

    logger.info(f"Updated to file: {file_path} was successfully")

def _setup_pam_config_file_redhat_distros():
    """Configure PAM for Red Hat based distributions."""
    # Configure /etc/pam.d/password-auth
    _modify_pam_file('/etc/pam.d/password-auth', 'account', 'account\tsufficient\tpam_cognito.so')
    _modify_pam_file('/etc/pam.d/password-auth', 'auth', 'auth\tsufficient\tpam_cognito.so')

    # Configure /etc/pam.d/system-auth
    _modify_pam_file('/etc/pam.d/system-auth', 'account', 'account\tsufficient\tpam_cognito.so')
    _modify_pam_file('/etc/pam.d/system-auth', 'auth', 'auth\tsufficient\tpam_cognito.so')

def _setup_cognito_config_file():

    """
    Create the Cognito configuration file.
    Using string instead configparser to avoid the header
    """

    config_file = "/etc/cognito_auth.conf"
    env = os.environ

    text = '' \
        + '# Cognito authorizer configuration file\n' \
        + f'user_pool_id = {cluster_settings.get_setting("identity-provider.cognito.user_pool_id")}\n' \
        + f'client_id = {cluster_settings.get_setting("identity-provider.cognito.vdi_client_id")}\n' \
        + 'aws_access_key_id =\n' \
        + 'aws_secret_access_key =\n' \
        + f'aws_region = {env.get("AWS_REGION", "")}\n' \
        + '\n' \
        + f'cognito_default_user_group = {constants.COGNITO_DEFAULT_USER_GROUP}\n' \
        + f'cognito_uid_attribute = custom:{constants.COGNITO_UID_ATTRIBUTE}\n' \
        + f'min_id = {constants.COGNITO_MIN_ID_INCLUSIVE}\n' \
        + f'max_id = {constants.COGNITO_MAX_ID_INCLUSIVE}\n' \
        + 'nss_cache_timeout_s = 60\n' \
        + 'nss_cache_path = /opt/cognito_auth/cache.json'

    if env.get("HTTPS_PROXY"):
            text += f'\nhttps_proxy = {env.get("HTTPS_PROXY", "")}\n'

    with open(config_file, 'w') as file:
        file.write(text)

    os.chmod(config_file, 0o644)
    logger.info(f"Setup to Cognito conf: {config_file} was successfully")

def _start_nscd():
    logger.info(f"Starting NSCD")
    subprocess.run(['systemctl', 'enable', 'nscd'], check=True)
    subprocess.run(['systemctl', 'start', 'nscd'], check=True)

def _setup_pam_config_file_ubuntu():
    """Configure PAM for Ubuntu."""
    # Configure /etc/pam.d/common-auth
    _modify_pam_file('/etc/pam.d/common-auth', 'auth', 'auth\tsufficient\tpam_cognito.so')

    # Configure /etc/pam.d/common-account
    _modify_pam_file('/etc/pam.d/common-account', 'account', 'account\tsufficient\tpam_cognito.so')

def _setup_nss():
    nsswitch_file = '/etc/nsswitch.conf'

    with open(nsswitch_file, 'r') as f:
        lines = f.readlines()

    """
    Modifying '/etc/nsswitch.conf' without configpaser
    in order to keep comments and instructions on the file
    """

    for i, line in enumerate(lines):
        if line.startswith('passwd:') and 'cognito' not in line:
            lines[i] = line.rstrip() + ' cognito\n'
        elif line.startswith('group:') and 'cognito' not in line:
            lines[i] = line.rstrip() + ' cognito\n'

    with open(nsswitch_file, 'w') as f:
        f.writelines(lines)

    os.makedirs('/opt/cognito_auth/', exist_ok=True)
    os.chmod('/opt/cognito_auth', 0o700) # nosec
    logger.info(f"Setup to NSS Switch file: {nsswitch_file} was successfully")

def configure():
    if not cluster_settings.get_setting("identity-provider.cognito.enable_native_user_login"):
        return

    logger.info("Starting Cognito Configuration")
    env = os.environ
    base_os = get_base_os()

    if base_os in ("ubuntu2204", "ubuntu2404"):
        _setup_pam_config_file_ubuntu()
    elif base_os in ['amzn2', "amzn2023", 'rhel8', 'rhel9', 'rocky9']:
        _setup_pam_config_file_redhat_distros()
    else:
        logger.error(f"Invalid OS: {base_os}")

    _setup_cognito_config_file()
    _setup_nss()
    _start_nscd()

    if env.get("IDEA_SESSION_OWNER"):
        subprocess.run(['su', '-', env.get("IDEA_SESSION_OWNER"), '-c', 'exit'])

    logger.info("Cognito setup was successfully")

    if env.get("IDEA_SESSION_OWNER"):
        set_reboot_required("Reboot required for DCV connection to Cognito")


