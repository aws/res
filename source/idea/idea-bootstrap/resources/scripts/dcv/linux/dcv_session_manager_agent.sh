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

# Begin: DCV Session Manager Agent
set -x

while getopts o:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/linux/bootstrap_common.sh"

SUB_DIR=""
if [[ $BASE_OS =~ ^(amzn2|amzn2023|rhel8|rhel9|rocky9)$ ]]; then
  SUB_DIR="red_hat"
elif [[ $BASE_OS =~ ^(ubuntu2204|ubuntu2404)$ ]]; then
  SUB_DIR="debian"
else
  log_warning "Base OS not supported."
  exit 1
fi
source "$SCRIPT_DIR/../dcv/linux/$SUB_DIR/dcv_session_manager_agent.sh"

if ! pre_installed; then
  install_nice_dcv_session_manager_agent $BASE_OS
else
  log_info "Found nice-dcv-session-manager-agent pre-installed... skipping installation..."
fi

# END: DCV Session Manager Agent
