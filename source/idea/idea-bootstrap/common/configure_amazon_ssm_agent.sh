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

while getopts o:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

log_info "Configure Amazon SSM agent"

if [[ $BASE_OS =~ ^(amzn2|rhel8|rhel9)$ ]]; then
  /bin/bash "${SCRIPT_DIR}/../common/red_hat/configure_amazon_ssm_agent.sh"
elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
  /bin/bash "${SCRIPT_DIR}/../common/debian/configure_amazon_ssm_agent.sh"
else
  log_warning "Base OS not supported."
fi
