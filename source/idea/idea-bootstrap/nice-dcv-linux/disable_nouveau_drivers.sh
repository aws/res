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

if [[ "$GPU_FAMILY" == "NVIDIA" ]]; then
  if [[ $BASE_OS =~ ^(centos7|rhel7|rhel8|rhel9)$ ]]; then
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
      grub2-mkconfig -o /boot/grub2/grub.cfg

      set_reboot_required "Disable NVIDIA Nouveau Drivers"
    fi
  elif [[ $BASE_OS =~ ^(amzn2)$ ]]; then
    log_info "Not required for Amazon Linux 2."
  else
    log_warning "Base OS not supported."
  fi
fi
# End: Disable NVIDIA Nouveau Drivers
