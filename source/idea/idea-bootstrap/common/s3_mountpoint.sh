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

# Begin: S3 Mountpoint
set -x

while getopts o:r:n:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

function install_s3_mountpoint () {
  mount-s3 --version
  if [[ "$?" != "0" ]]; then
    local AWS=$(command -v aws)
    machine=$(uname -m)
    if [[ $machine =~ ^(x86_64|aarch64)$ ]]; then
      local s3_mountpoint_link=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.s3_mountpoint.'${machine}'"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
      yum install -y $s3_mountpoint_link
    else
      log_warning "Base architecture not supported."
    fi
  fi
}
if [[ $BASE_OS =~ ^(amzn2|centos7|rhel7|rhel8|rhel9)$ ]]; then 
  install_s3_mountpoint
fi
# End: S3 Mountpoint
