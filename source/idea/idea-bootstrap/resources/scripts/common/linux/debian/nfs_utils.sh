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

source "$SCRIPT_DIR/../common/linux/bootstrap_common.sh"
source "$SCRIPT_DIR/../common/linux/config_common.sh"

function install_nfs_utils() {
  echo "Skip NFS utils installation on Ubuntu"
}

function get_stunnel_package_name() {
    echo stunnel
}

function install_stunnel_impl() {
  apt install -y "$(get_stunnel_package_name)"
}

function install_efs_mount_helper_impl() {
  local EFS_MOUNT_HELPER_BUILD_DEPENDENCIES=$(get_list 'package_config.efs_mount_helper.build_dependencies.debian.ubuntu')
  DEBIAN_FRONTEND=noninteractive apt install -y ${EFS_MOUNT_HELPER_BUILD_DEPENDENCIES[*]}

  local EFS_MOUNT_HELPER_REPO=$(get_string 'package_config.efs_mount_helper.repo')
  git clone ${EFS_MOUNT_HELPER_REPO}
  cd efs-utils
  ./build-deb.sh
  DEBIAN_FRONTEND=noninteractive apt install -y ./build/amazon-efs-utils*deb
  cd ..
}
