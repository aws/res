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

BOOTSTRAP_DIR="/root/bootstrap"

function log_info() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S,%3N")] [INFO] ${1}"
}

function log_warning() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S,%3N")] [WARNING] ${1}"
}

function log_error() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S,%3N")] [ERROR] ${1}"
}

function log_debug() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S,%3N")] [DEBUG] ${1}"
}

function set_reboot_required () {
  log_info "Reboot Required: ${1}"
  echo -n "yes" > ${BOOTSTRAP_DIR}/reboot_required.txt
}

function get_reboot_required () {
  if [[ -f ${BOOTSTRAP_DIR}/reboot_required.txt ]]; then
    cat ${BOOTSTRAP_DIR}/reboot_required.txt
  fi
  echo -n "no"
}

function get_base_os () {
  if [[ -f /etc/os-release ]]; then
    OS_RELEASE_ID=$(grep -E '^(ID)=' /etc/os-release | awk -F'"' '{print $2}')
    OS_RELEASE_VERSION_ID=$(grep -E '^(VERSION_ID)=' /etc/os-release | awk -F'"' '{print $2}')
    BASE_OS=$(echo $OS_RELEASE_ID${OS_RELEASE_VERSION_ID%%.*})
    if [[ -z "${OS_RELEASE_ID}" ]]; then
      # Base OS is Ubuntu
      OS_RELEASE_ID=$(grep -E '^(ID)=' /etc/os-release | awk -F'=' '{print $2}')
      BASE_OS=$(echo $OS_RELEASE_ID$OS_RELEASE_VERSION_ID | sed -e 's/\.//g')
    fi
  elif [[ -f /usr/lib/os-release ]]; then
    OS_RELEASE_ID=$(grep -E '^(ID)=' /usr/lib/os-release | awk -F'"' '{print $2}')
    OS_RELEASE_VERSION_ID=$(grep -E '^(VERSION_ID)=' /usr/lib/os-release | awk -F'"' '{print $2}')
    BASE_OS=$(echo $OS_RELEASE_ID${OS_RELEASE_VERSION_ID%%.*})
  else
    echo "Base OS information on Linux instance cannot be found."
    exit 1
  fi

  echo -n "${BASE_OS}"
}

function imds_get () {
  local SLASH=''
  local IMDS_HOST="http://169.254.169.254"
  local IMDS_TTL="300"
  # prepend a slash if needed
  if [[ "${1:0:1}" == '/' ]]; then
    SLASH=''
  else
    SLASH='/'
  fi
  local URL="${IMDS_HOST}${SLASH}${1}"

  # Get an Auth token
  local TOKEN=$(curl --silent -X PUT "${IMDS_HOST}/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: ${IMDS_TTL}")

  # Get the requested value and echo it back
  local OUTPUT=$(curl --silent -H "X-aws-ec2-metadata-token: ${TOKEN}" "${URL}")
  echo -n "${OUTPUT}"
}

function instance_type () {
  local INSTANCE_TYPE=$(imds_get /latest/meta-data/instance-type)
  echo -n "${INSTANCE_TYPE}"
}

function instance_family () {
  local INSTANCE_FAMILY=$(imds_get /latest/meta-data/instance-type | cut -d. -f1)
  echo -n "${INSTANCE_FAMILY}"
}

function get_aws_region() {
  local AWS_REGION=$(imds_get /latest/dynamic/instance-identity/document | jq .region -r)
  echo -n "${AWS_REGION}"
}

function request_and_export_aws_credentials() {
  if [ -z "$1" ]; then
    echo "Error: AWS_REGION not provided. Usage: request_and_export_aws_credentials <AWS_REGION>"
  fi

  if [ -z "$2" ]; then
    echo "Error: CUSTOM_BROKER_URL not provided. Usage: request_and_export_aws_credentials <CUSTOM_BROKER_URL>"
  fi

  AWS_REGION="$1"
  CUSTOM_BROKER_URL="$2"

  mkdir -p ~/.aws
  echo -e "[default]\nregion = $AWS_REGION" > ~/.aws/config
  CUSTOM_BROKER_PATH="/root/bootstrap/latest/scripts/vdi-helper/custom_credential_broker.py"

  if [ ! -f "${CUSTOM_BROKER_PATH}" ]; then
    echo "Error: Custom credential broker script not found at ${CUSTOM_BROKER_PATH}"
  fi

  local BROKER_DEST="/opt/idea/scripts/custom_credential_broker.py"

  PROFILE_NAME="bootstrap_profile"

  JWT_TOKEN=$(cat /root/bootstrap/broker_token | tr -d '\n')

  aws configure set output json
  aws configure set region $AWS_REGION
  aws configure set credential_process "/opt/idea/python/latest/bin/idea_python ${BROKER_DEST} --bootstrap-token ${JWT_TOKEN} --api-url ${CUSTOM_BROKER_URL} --region ${AWS_REGION}" --profile "${PROFILE_NAME}"
  aws configure set --profile $PROFILE_NAME output json
  aws configure set --profile $PROFILE_NAME region $AWS_REGION

  # Grant nscd and dbus-daemon traverse access to /root/.aws/config for credential_process.
  setfacl -m u:nscd:x /root 2>/dev/null
  setfacl -m u:nscd:x /root/.aws 2>/dev/null
  setfacl -m u:nscd:r /root/.aws/config 2>/dev/null
  # dbus user is 'dbus' on RHEL/AL and 'messagebus' on Ubuntu.
  local BASE_OS=$(get_base_os)
  if [[ "$BASE_OS" =~ ^(ubuntu) ]]; then
    DBUS_USER="messagebus"
  else
    DBUS_USER="dbus"
  fi
  setfacl -m u:${DBUS_USER}:x /root 2>/dev/null
  setfacl -m u:${DBUS_USER}:x /root/.aws 2>/dev/null
  setfacl -m u:${DBUS_USER}:r /root/.aws/config 2>/dev/null
}

function install_efs_with_rustup() {
  local build_cmd="$1"
  local install_cmd="$2"

  export HOME="${HOME:-$(getent passwd "$(whoami)" | cut -d: -f6)}"
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable \
    || { log_error "Failed to install Rust via rustup"; return 1; }
  local _old_path="$PATH"
  source "$HOME/.cargo/env"
  trap 'rustup self uninstall -y 2>/dev/null || true; PATH="$_old_path"' RETURN
  command -v rustc >/dev/null 2>&1 \
    || { log_error "rustc not found after rustup installation"; return 1; }
  log_info "Using Rust $(rustc --version)"

  local EFS_MOUNT_HELPER_REPO=$(get_string 'package_config.efs_mount_helper.repo')
  git clone --depth 1 ${EFS_MOUNT_HELPER_REPO} \
    || { log_error "Failed to clone efs-utils repo"; return 1; }
  cd efs-utils
  eval "$build_cmd" \
    || { log_error "Failed to build efs-utils package"; cd ..; return 1; }
  eval "$install_cmd"
  local build_rc=$?
  cd ..
  return $build_rc
}
