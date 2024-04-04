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

# Begin: System Packages Install
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

function install_system_packages () {
  IFS=$'\n'
  local AWS=$(command -v aws)
  local SYSTEM_PKGS=($($AWS dynamodb get-item \
                          --region "$AWS_REGION" \
                          --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                          --key '{"key": {"S": "global-settings.package_config.linux_packages.system"}}' \
                          --output text \
                          | awk '/L/ {print $2}'))
  local APPLICATION_PKGS=($($AWS dynamodb get-item \
                          --region "$AWS_REGION" \
                          --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                          --key '{"key": {"S": "global-settings.package_config.linux_packages.application"}}' \
                          --output text \
                          | awk '/L/ {print $2}'))
  local SSSD_PKGS=($($AWS dynamodb get-item \
                          --region "$AWS_REGION" \
                          --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                          --key '{"key": {"S": "global-settings.package_config.linux_packages.sssd"}}' \
                          --output text \
                          | awk '/L/ {print $2}'))
  local OPENLDAP_CLIENT_PKGS=($($AWS dynamodb get-item \
                          --region "$AWS_REGION" \
                          --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                          --key '{"key": {"S": "global-settings.package_config.linux_packages.openldap_client"}}' \
                          --output text \
                          | awk '/L/ {print $2}'))

  local SYSTEM_PKGS_7=()
  local SSSD_PKGS_7=()

  if [[ "$BASE_OS" == "rhel7" ]]; then 
    SYSTEM_PKGS_7=($($AWS dynamodb get-item \
                            --region "$AWS_REGION" \
                            --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                            --key '{"key": {"S": "global-settings.package_config.linux_packages.system_rhel7"}}' \
                            --output text \
                            | awk '/L/ {print $2}'))
    SSSD_PKGS_7=($($AWS dynamodb get-item \
                            --region "$AWS_REGION" \
                            --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                            --key '{"key": {"S": "global-settings.package_config.linux_packages.sssd_rhel7"}}' \
                            --output text \
                            | awk '/L/ {print $2}'))
  fi

  case $BASE_OS in
    amzn2|centos7)
      yum install -y ${SYSTEM_PKGS[*]} ${APPLICATION_PKGS[*]} ${SSSD_PKGS[*]} ${OPENLDAP_CLIENT_PKGS[*]}
      ;;
    rhel7)
      yum install -y ${SYSTEM_PKGS[*]} ${SYSTEM_PKGS_7[*]} ${APPLICATION_PKGS[*]} ${SSSD_PKGS[*]} ${SSSD_PKGS_7[*]} ${OPENLDAP_CLIENT_PKGS[*]} --enablerepo rhel-7-server-rhui-optional-rpms
      yum install -y ${SYSTEM_PKGS[*]} ${APPLICATION_PKGS[*]} ${SSSD_PKGS[*]} ${OPENLDAP_CLIENT_PKGS[*]}
      ;;
    rhel8)
      dnf install -y dnf-plugins-core
      dnf config-manager --set-enabled codeready-builder-for-rhel-8-rhui-rpms
      sss_cache -E
      dnf install -y ${SYSTEM_PKGS[*]} ${APPLICATION_PKGS[*]} ${SSSD_PKGS[*]} ${OPENLDAP_CLIENT_PKGS[*]} --enablerepo codeready-builder-for-rhel-8-rhui-rpms
      ;;
    rhel9)
      dnf install -y dnf-plugins-core
      dnf config-manager --set-enabled codeready-builder-for-rhel-9-rhui-rpms
      sss_cache -E
      dnf install -y ${SYSTEM_PKGS[*]} ${APPLICATION_PKGS[*]} ${SSSD_PKGS[*]} ${OPENLDAP_CLIENT_PKGS[*]} --enablerepo codeready-builder-for-rhel-9-rhui-rpms
      ;;
    *)
      log_warning "Base OS not supported."
      ;;
  esac
  unset IFS
}
install_system_packages
# End: System Packages Install
