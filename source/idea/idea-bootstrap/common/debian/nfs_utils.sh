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
  DEBIAN_FRONTEND=noninteractive apt install -y git binutils rustc cargo pkg-config libssl-dev
  git clone https://github.com/aws/efs-utils
  cd efs-utils
  ./build-deb.sh
  DEBIAN_FRONTEND=noninteractive apt install -y ./build/amazon-efs-utils*deb
  cd ..
}
