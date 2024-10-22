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

# Begin: Install Host Modules

set -x

while getopts o:r:n:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
        \?)
          echo "Usage: $0 [-o base_os] [-r aws_region] [-n res_environment_name] [-s script_dir]"
          exit 1
          ;;
    esac
done

if [[ -z "$BASE_OS" || -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

# Set directories based on the OS
case "$BASE_OS" in
  ubuntu2204)
    pam_lib_dir="/usr/lib/x86_64-linux-gnu/security"
    nss_lib_dir="/usr/lib/x86_64-linux-gnu/"
    ;;
  amzn2|rhel7|rhel8|rhel9)
    pam_lib_dir="/usr/lib64/security"
    nss_lib_dir="/lib64"
    ;;
  *)
    echo "Unknown OS: $BASE_OS"
    exit 1
    ;;
esac

# Set OS_ARCH based on machine architecture
case "$(uname -m)" in
  x86_64) OS_ARCH="x86_64";;
  aarch64) OS_ARCH="arm64";;
  *) echo "Unsupported architecture: $(uname -m)"; exit 1;;
esac

# Common function to install modules
function install_modules () {
  local MODULE_TYPE=$1
  local TARGET_DIR=$2
  local HOST_MODULES_LIST_KEY="global-settings.package_config.host_modules.$MODULE_TYPE"

  if [[ ! -f "/root/.convert_from_dynamodb_object.jq" ]]; then
    create_jq_ddb_filter
  fi

  AWS=$(command -v aws)
  response=$($AWS dynamodb get-item \
                      --region "$AWS_REGION" \
                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                      --key '{"key": {"S": "'${HOST_MODULES_LIST_KEY}'"}}' \
                      --output json \
                      | jq -f /root/.convert_from_dynamodb_object.jq | jq '.Item')

  modules=$(echo "$response" | jq -r '.value' | jq -r '.[]')

  echo "$modules" | while read -r module; do
    module_s3_uri=$($AWS dynamodb get-item \
                          --region "$AWS_REGION" \
                          --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                          --key '{"key": {"S": "vdc.host_modules.'${module}'.'${OS_ARCH}'.s3_url"}}' \
                          --output text \
                          | awk '/VALUE/ {print $2}')
    target_location="$TARGET_DIR/$module.so"

    echo "Downloading $module from $module_s3_uri..."
    aws s3 cp "$module_s3_uri" "$target_location"

    # Change permissions to 555 and set ownership to root
    chmod 555 "$target_location"
    chown root:root "$target_location"

    echo "$module has been successfully installed to $TARGET_DIR"
  done
}

install_modules "pam" "$pam_lib_dir"
install_modules "nss" "$nss_lib_dir"
# End: Install Host Modules
