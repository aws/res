#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

# Begin: Configure Cognito Modules

set -x

usage() {
  echo "Usage: $0 [-o base_os] [-s script_dir] [-r region]"
  exit 1
}

while getopts "o:s:u:r:i:a:g:d:p:c:x:" opt; do
  case "${opt}" in
    o) BASE_OS=${OPTARG} ;;
    s) SCRIPT_DIR=${OPTARG} ;;
    u) USERNAME=${OPTARG} ;;
    r) REGION=${OPTARG} ;;
    i) COGNITO_MIN_ID=${OPTARG} ;;
    a) COGNITO_MAX_ID=${OPTARG} ;;
    g) COGNITO_DEFAULT_USER_GROUP=${OPTARG} ;;
    d) COGNITO_UID_ATTRIBUTE=${OPTARG} ;;
    p) USER_POOL_ID=${OPTARG} ;;
    c) VDI_CLIENT_ID=${OPTARG} ;;
    x) HTTPS_PROXY=${OPTARG} ;;
    *) usage ;;
  esac
done

[[ -z "$BASE_OS" || -z "$SCRIPT_DIR" || -z "$REGION" || \
  -z "$COGNITO_MIN_ID" || -z "$COGNITO_MAX_ID" || -z "$COGNITO_UID_ATTRIBUTE" || \
  -z "$USER_POOL_ID" || -z "$VDI_CLIENT_ID" || -z "$COGNITO_DEFAULT_USER_GROUP" ]] && \
  { echo "Missing required parameters..."; exit 1; }

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

setup_pam_config_file_redhat_distros() {
  #Add the following lines at the top of their respective section in `/etc/pam.d/password-auth`. Add the lines if the line aren't already there
  #auth    sufficient    pam_cognito.so
  #account sufficient    pam_cognito.so
  grep -q "^account.*cognito" /etc/pam.d/password-auth || (awk '/^account.*/ && !done {print "account\tsufficient\tpam_cognito.so"; done=1; } 1' /etc/pam.d/password-auth > /tmp/tmp.txt && mv -f /tmp/tmp.txt /etc/pam.d/password-auth);
  grep -q "^auth.*cognito" /etc/pam.d/password-auth || (awk '/^auth.*/ && !done {print "auth\tsufficient\tpam_cognito.so"; done=1; } 1' /etc/pam.d/password-auth > /tmp/tmp.txt && mv -f /tmp/tmp.txt /etc/pam.d/password-auth);

  #Add the following lines at the top of their respective section in `/etc/pam.d/system-auth`. Add the lines if the line aren't already there
  #auth    sufficient    pam_cognito.so
  #account sufficient    pam_cognito.so
  grep -q "^account.*cognito" /etc/pam.d/system-auth || (awk '/^account.*/ && !done {print "account\tsufficient\tpam_cognito.so"; done=1; } 1' /etc/pam.d/system-auth > /tmp/tmp.txt && mv -f /tmp/tmp.txt /etc/pam.d/system-auth);
  grep -q "^auth.*cognito" /etc/pam.d/system-auth || (awk '/^auth.*/ && !done {print "auth\tsufficient\tpam_cognito.so"; done=1; } 1' /etc/pam.d/system-auth > /tmp/tmp.txt && mv -f /tmp/tmp.txt /etc/pam.d/system-auth);
}

setup_cognito_config_file() {
  CONFIG_FILE="/etc/cognito_auth.conf"
  cat << EOF > "$CONFIG_FILE"
# Cognito authorizer configuration file
user_pool_id = $USER_POOL_ID
client_id = $VDI_CLIENT_ID
aws_access_key_id =
aws_secret_access_key =
aws_region = $REGION

cognito_default_user_group = $COGNITO_DEFAULT_USER_GROUP
cognito_uid_attribute = custom:$COGNITO_UID_ATTRIBUTE
min_id = $COGNITO_MIN_ID
max_id = $COGNITO_MAX_ID
nss_cache_timeout_s = 60
nss_cache_path = /opt/cognito_auth/cache.json
EOF

  if [[ -n "$HTTPS_PROXY" ]]; then
    echo "https_proxy = $HTTPS_PROXY" >> "$CONFIG_FILE"
  fi

  # Allow root user to read/write the file. Allow group and public user to read the file
  chmod 644 "$CONFIG_FILE"
}

start_nscd() {
  # start nscd
  systemctl enable nscd
  systemctl start nscd
}

setup_pam_config_file_ubuntu() {
  #Add the following line at the top of `/etc/pam.d/common-auth`. Add the lines if the line isn't already there
  #auth    sufficient    pam_cognito.so
  grep -q "^auth.*cognito" /etc/pam.d/common-auth || (awk '/^auth.*/ && !done {print "auth\tsufficient\tpam_cognito.so"; done=1; } 1' /etc/pam.d/common-auth > /tmp/tmp.txt && mv -f /tmp/tmp.txt /etc/pam.d/common-auth);

  #Add the following line at the top of `/etc/pam.d/common-account`. Add the lines if the line isn't already there
  #account sufficient    pam_cognito.so
  grep -q "^account.*cognito" /etc/pam.d/common-account || (awk '/^account.*/ && !done {print "account\tsufficient\tpam_cognito.so"; done=1; } 1' /etc/pam.d/common-account > /tmp/tmp.txt && mv -f /tmp/tmp.txt /etc/pam.d/common-account);
}

setup_nss() {
  # Add `cognito` to `passwd` and `group` setting. `cognito` should appear after `sss`. Add the lines if the line isn't already there
  # Example of what the updated lines will look like is shown below
  #passwd:     files sss cognito
  #group:      files sss cognito
  grep -q "^passwd.*cognito" /etc/nsswitch.conf || sed -i 's/\(^passwd:.*sss\)/\1 cognito/' /etc/nsswitch.conf;
  grep -q "^group.*cognito" /etc/nsswitch.conf || sed -i 's/\(^group:.*sss\)/\1 cognito/' /etc/nsswitch.conf;

  # Create cache directory
  mkdir -p /opt/cognito_auth/
  #The folder has read/write/execute permission for `public`. However, when `nscd` write the cache the cache will only provide `read` permission for `group` and `public`
  chmod 777 /opt/cognito_auth
}

# Configure PAM based on the operating system
case "$BASE_OS" in
  ubuntu2204)
    setup_pam_config_file_ubuntu
    ;;
  amzn2|rhel7|rhel8|rhel9)
    setup_pam_config_file_redhat_distros
    ;;
  *)
    echo "Unsupported OS: $BASE_OS"
    exit 1
    ;;
esac

setup_cognito_config_file
setup_nss
start_nscd

# Trigger PAM module so home dir can be created with correct user permission
if [[ -n "$USERNAME" ]]; then
  su - "$USERNAME" -c "exit"
fi

set_reboot_required "Reboot required for DCV connection to Cognito"
# End: Configure Cognito Modules
