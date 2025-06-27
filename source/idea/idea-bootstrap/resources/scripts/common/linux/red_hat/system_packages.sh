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

while getopts o:s: opt
do
  case "${opt}" in
    o) BASE_OS=${OPTARG};;
    s) SCRIPT_DIR=${OPTARG};;
    ?) echo "Invalid option for system_packages.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
source "${SCRIPT_DIR}/../common/linux/config_common.sh"

IFS=$'\n'
SYSTEM_PKGS=($(get_list 'package_config.system.red_hat'))

# Evaluate embedded commands
EVALUATED_SYSTEM_PKGS=()
for pkg in "${SYSTEM_PKGS[@]}"; do
    EVALUATED_SYSTEM_PKGS+=("$(eval echo "$pkg")")
done

case $BASE_OS in
  amzn2|amzn2023)
    yum install -y ${EVALUATED_SYSTEM_PKGS[*]} --skip-broken
    ;;
  rhel8)
    dnf config-manager --set-enabled codeready-builder-for-rhel-8-rhui-rpms
    sss_cache -E
    dnf install -y ${EVALUATED_SYSTEM_PKGS[*]} --enablerepo codeready-builder-for-rhel-8-rhui-rpms --skip-broken
    ;;
  rhel9|rocky9)
    dnf config-manager --set-enabled codeready-builder-for-rhel-9-rhui-rpms
    sss_cache -E
    dnf install -y ${EVALUATED_SYSTEM_PKGS[*]} --enablerepo codeready-builder-for-rhel-9-rhui-rpms --skip-broken
    ;;
  *)
    log_warning "Base OS not supported."
    ;;
esac
unset IFS
