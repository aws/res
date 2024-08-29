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

# Begin: Disable NVIDIA Nouveau Drivers
set -x

while getopts o:g:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        g) GPU_FAMILY=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$GPU_FAMILY" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

if [[ "$GPU_FAMILY" =~ "AMD" && $BASE_OS =~ ^(rhel8|rhel9)$ ]]; then
  log_warning "The latest AMD driver hasn't supported the current Linux version yet"
  exit 0
fi

SUB_DIR=""
if [[ $BASE_OS =~ ^(amzn2|rhel8|rhel9)$ ]]; then
  SUB_DIR="red_hat"
elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
  SUB_DIR="debian"
else
  log_warning "Base OS not supported."
  exit 1
fi
source "$SCRIPT_DIR/../nice-dcv-linux/$SUB_DIR/grub_configuration.sh"

grep -q "rdblacklist=nouveau" /etc/default/grub
if [[ "$?" != "0" ]]; then
  log_info "Disabling the nouveau open source driver for NVIDIA graphics cards"
  cat << EOF | tee --append /etc/modprobe.d/blacklist.conf
blacklist vga16fb
blacklist nouveau
blacklist rivafb
blacklist nvidiafb
blacklist rivatv
EOF
  echo GRUB_CMDLINE_LINUX="rdblacklist=nouveau" >> /etc/default/grub
  update_grub_configuration
  set_reboot_required "Disable NVIDIA Nouveau Drivers"
fi
# End: Disable NVIDIA Nouveau Drivers
