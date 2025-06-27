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

# Begin: Install Putty packages
set -x

while getopts o:s: opt
do
  case "${opt}" in
    o) BASE_OS=${OPTARG};;
    s) SCRIPT_DIR=${OPTARG};;
    ?) echo "Invalid option for putty.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"

SUB_DIR=""
if [[ $BASE_OS =~ ^(amzn2|amzn2023|rhel8|rhel9|rocky9)$ ]]; then
  SUB_DIR="red_hat"
else
  log_warning "Base OS not supported."
  exit 1
fi
source "${SCRIPT_DIR}/../common/linux/$SUB_DIR/putty.sh" -s "${SCRIPT_DIR}"
# End: Install Putty packages
