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

IFS=$'\n'
AWS=$(command -v aws)
SYSTEM_PKGS_JSON=$($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.package_config.linux_packages.system"}}' \
                        --output json)
APPLICATION_PKGS=($($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.package_config.linux_packages.application"}}' \
                        --output text \
                        | awk '/L/ {print $2}'))
SSSD_PKGS=($($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.package_config.linux_packages.sssd"}}' \
                        --output text \
                        | awk '/L/ {print $2}'))
OPENLDAP_CLIENT_PKGS=($($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.package_config.linux_packages.openldap_client"}}' \
                        --output text \
                        | awk '/L/ {print $2}'))

# Extract package names using jq and accumulate them into an array
mapfile -t SYSTEM_PKGS < <(echo "$SYSTEM_PKGS_JSON" | jq -r '.Item["value"]["L"][]["S"]')

# Evaluate embedded commands
EVALUATED_SYSTEM_PKGS=()
for pkg in "${SYSTEM_PKGS[@]}"; do
    EVALUATED_SYSTEM_PKGS+=("$(eval echo "$pkg")")
done

case $BASE_OS in
  amzn2)
    yum install -y ${EVALUATED_SYSTEM_PKGS[*]} ${APPLICATION_PKGS[*]} ${SSSD_PKGS[*]} ${OPENLDAP_CLIENT_PKGS[*]} --skip-broken
    ;;
  rhel8)
    dnf install -y dnf-plugins-core
    dnf config-manager --set-enabled codeready-builder-for-rhel-8-rhui-rpms
    sss_cache -E
    dnf install -y ${EVALUATED_SYSTEM_PKGS[*]} ${APPLICATION_PKGS[*]} ${SSSD_PKGS[*]} ${OPENLDAP_CLIENT_PKGS[*]} --enablerepo codeready-builder-for-rhel-8-rhui-rpms --skip-broken
    ;;
  rhel9)
    dnf install -y dnf-plugins-core
    dnf config-manager --set-enabled codeready-builder-for-rhel-9-rhui-rpms
    sss_cache -E
    dnf install -y ${EVALUATED_SYSTEM_PKGS[*]} --enablerepo codeready-builder-for-rhel-9-rhui-rpms --skip-broken
    dnf install -y ${APPLICATION_PKGS[*]} --enablerepo codeready-builder-for-rhel-9-rhui-rpms --skip-broken
    dnf install -y ${SSSD_PKGS[*]} --enablerepo codeready-builder-for-rhel-9-rhui-rpms --skip-broken
    dnf install -y ${OPENLDAP_CLIENT_PKGS[*]} --enablerepo codeready-builder-for-rhel-9-rhui-rpms --skip-broken
    ;;
  *)
    log_warning "Base OS not supported."
    ;;
esac
unset IFS
