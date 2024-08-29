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

# Begin: DCV Server
set -x

while getopts o:r:n:g:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        g) GPU_FAMILY=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" || -z "$GPU_FAMILY" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

SUB_DIR=""
if [[ $BASE_OS =~ ^(amzn2|rhel8|rhel9)$ ]]; then
  SUB_DIR="red_hat"
elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
  SUB_DIR="debian"
else
  log_warning "Base OS not supported."
  exit 1
fi
source "$SCRIPT_DIR/../nice-dcv-linux/$SUB_DIR/dcv_server.sh"

function install_gpu_drivers() {
  install_gpu_driver_prerequisites

  /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/gpu_drivers.sh" -o $BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -g $GPU_FAMILY -s "${SCRIPT_DIR}"
}

install_prerequisites

if [[ $GPU_FAMILY =~ ^(NVIDIA|AMD)$ ]]; then
  log_info "Installing GPU drivers"
  install_gpu_drivers
else
  log_info "GPU InstanceType not detected. Skipping GPU driver installation."
fi

if ! pre_installed; then
  install_nice_dcv_server $BASE_OS $AWS_REGION $RES_ENVIRONMENT_NAME $GPU_FAMILY
  install_microphone_redirect
  install_usb_support
else
  log_info "Found nice-dcv-server pre-installed... skipping installation..."
fi
# End: DCV Server
