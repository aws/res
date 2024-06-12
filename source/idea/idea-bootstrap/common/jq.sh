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

# Begin: Install jq
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

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

SUB_DIR=""
if [[ $BASE_OS =~ ^(amzn2|centos7|rhel7|rhel8|rhel9)$ ]]; then
  SUB_DIR="red_hat"
elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
  SUB_DIR="debian"
else
  log_warning "Base OS not supported."
  exit 1
fi
source "$SCRIPT_DIR/../common/$SUB_DIR/jq.sh"

which jq > /dev/null 2>&1
if [[ "$?" != "0" ]]; then
  log_info "installing jq"
  install_jq
fi
# End: Install jq
