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

while getopts o:s:e:b: opt
do
  case "${opt}" in
    o) BASE_OS=${OPTARG};;
    s) SCRIPT_DIR=${OPTARG};;
    e) ENVIRONMENT_NAME=${OPTARG};;
    b) STAGING_BUCKET=${OPTARG};;
    ?) echo "Invalid option for host_modules.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
source "${SCRIPT_DIR}/../common/linux/config_common.sh"

# Set directories based on the OS
case "$BASE_OS" in
  ubuntu2204|ubuntu2404)
    pam_lib_dir="/usr/lib/x86_64-linux-gnu/security"
    nss_lib_dir="/usr/lib/x86_64-linux-gnu"
    ;;
  amzn2|amzn2023|rhel8|rhel9|rocky9)
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
AWS_REGION=$(get_aws_region)

# Common function to install modules
function install_modules () {
  local MODULE_TYPE=$1
  local TARGET_DIR=$2
  modules=($(get_list "package_config.host_modules.${MODULE_TYPE}"))

  for module in "${modules[@]}"; do
    module_s3_uri=""

    # Priority 1: DynamoDB record (if ENVIRONMENT_NAME and table exist)
    if [[ -n "${ENVIRONMENT_NAME}" ]]; then
      module_s3_uri_key="cluster-manager.host_modules.${module}.${OS_ARCH}.s3_url"
      module_s3_uri=$(aws dynamodb get-item \
          --region "$AWS_REGION" \
          --table-name "$ENVIRONMENT_NAME.cluster-settings" \
          --key '{"key": {"S": "'$module_s3_uri_key'"}}' \
          --output text \
          2>/dev/null | awk '/VALUE/ {print $2}')
    fi

    # Priority 2: Staging bucket
    if [[ -z "$module_s3_uri" && -n "${STAGING_BUCKET}" ]]; then
      echo "DynamoDB record not found for module $module, falling back to staging bucket: ${STAGING_BUCKET}"
      module_s3_uri="s3://${STAGING_BUCKET}/host_modules/${module}/latest/${OS_ARCH}/${module}.so"
    fi

    # Priority 3: Default bucket
    if [[ -z "$module_s3_uri" ]]; then
      echo "DynamoDB record and staging bucket not available for module $module, falling back to default bucket"
      module_s3_uri="s3://research-engineering-studio-${AWS_REGION}/host_modules/${module}/latest/${OS_ARCH}/${module}.so"
    fi
    if [[ $MODULE_TYPE = "nss" ]]; then
      target_location="$TARGET_DIR/$module.so.2"
    else
      target_location="$TARGET_DIR/$module.so"
    fi

    echo "Downloading $module from $module_s3_uri..."
    aws s3 cp "$module_s3_uri" "$target_location" --region "$AWS_REGION"

    # Change permissions to 555 and set ownership to root
    chmod 555 "$target_location"
    chown root:root "$target_location"

    echo "$module has been successfully installed to $TARGET_DIR"
  done
}

install_modules "pam" "$pam_lib_dir"
install_modules "nss" "$nss_lib_dir"
# End: Install Host Modules
