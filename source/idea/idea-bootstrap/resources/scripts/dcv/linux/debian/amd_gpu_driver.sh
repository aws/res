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

set -x

while getopts s: opt
do
    case "${opt}" in
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
source "${SCRIPT_DIR}/../common/linux/config_common.sh"

apt install -y linux-modules-extra-$(uname -r)
apt install -y linux-firmware

DOWNLOAD_URL=$(get_string "package_config.gpu_driver.amd.debian.download_link")
FILE_NAME=$(basename ${DOWNLOAD_URL})
wget ${DOWNLOAD_URL}
DEBIAN_FRONTEND=noninteractive apt install -y ./${FILE_NAME}

amdgpu-install --usecase=workstation --vulkan=pro --opencl=rocr --no-32 -y --accept-eula
