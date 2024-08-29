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

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

function install_nfs_utils() {
  if [[ -z "$(rpm -qa nfs-utils)" ]]; then
    log_info "# installing nfs-utils"
    yum install -y nfs-utils
  fi
}

function get_stunnel_package_name() {
  local BASE_OS=$1

  if [[ $BASE_OS =~ ^(amzn2)$ ]]; then
    STUNNEL_CMD='stunnel5'
  else
    STUNNEL_CMD='stunnel'
  fi

  echo $STUNNEL_CMD
}

function install_stunnel_impl() {
  yum install -y "$(get_stunnel_package_name)"
}

function install_efs_mount_helper_impl() {
  local BASE_OS=$1

  if [[ $BASE_OS =~ ^(amzn2)$ ]]; then
    yum install -y amazon-efs-utils
  elif [[ $BASE_OS =~ ^(rhel8|rhel9)$ ]]; then
    git clone https://github.com/aws/efs-utils
    cd efs-utils
    make rpm
    yum -y install build/amazon-efs-utils*rpm
    cd ..
  fi
}
