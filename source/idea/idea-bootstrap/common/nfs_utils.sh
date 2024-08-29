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

# Begin: NFS Utils and dependency items

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
if [[ $BASE_OS =~ ^(amzn2|rhel8|rhel9)$ ]]; then
  SUB_DIR="red_hat"
elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
  SUB_DIR="debian"
else
  log_warning "Base OS not supported."
  exit 1
fi
source "$SCRIPT_DIR/../common/$SUB_DIR/nfs_utils.sh"

function install_stunnel () {
  STUNNEL_CMD=$(get_stunnel_package_name $BASE_OS)
  which ${STUNNEL_CMD} > /dev/null 2>&1
  if [[ "$?" != "0" ]]; then
    log_info "Installing stunnel"
    install_stunnel_impl
  else
    log_info "Found existing stunnel on system"
  fi
  # If needed - fixup configuration for older stunnel 4 packages that lack support for cert hostname enforcement
  STUNNEL_VERSION=$(${STUNNEL_CMD} -version 2>&1 | egrep '^stunnel' | awk '{print $2}' | cut -f1 -d.)
  log_info "Detected stunnel version ${STUNNEL_VERSION}"
  if [[ "${STUNNEL_VERSION}" == '4' ]]; then
    log_info "Stunnel 4 detected - Disabling stunnel_check_cert_hostname in /etc/amazon/efs/efs-utils.conf "
    sed -i.backup 's/stunnel_check_cert_hostname = true/stunnel_check_cert_hostname = false/g' /etc/amazon/efs/efs-utils.conf
    log_info "Configuration now:"
    log_info "$(grep stunnel_check_cert_hostname /etc/amazon/efs/efs-utils.conf)"
  fi
}

function install_efs_mount_helper() {
    which amazon-efs-mount-watchdog > /dev/null 2>&1
    if [[ "$?" != "0" ]]; then
      log_info "Installing Amazon EFS Mount Helper"
      install_efs_mount_helper_impl ${BASE_OS}
  else
    log_info "Found existing Amazon EFS Mount Helper on system"
  fi
}

install_nfs_utils
install_stunnel
install_efs_mount_helper
# End: NFS Utils
