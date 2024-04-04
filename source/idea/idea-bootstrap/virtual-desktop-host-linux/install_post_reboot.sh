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

CONFIGURE_FOR_RES_VDI=0
while getopts v: opt
do
    case "${opt}" in
        v) CONFIGURE_FOR_RES_VDI=${OPTARG};;
        ?) echo "Invalid option for install_post_reboot.sh script: -${opt}."
           exit 1;;
    esac
done

INSTALL_SCRIPT_EXEC=0
for INSTALL_LOG in /root/bootstrap/logs/install.log.*
do
  if [[ $INSTALL_LOG != '/root/bootstrap/logs/install.log.*' ]]; then
    INSTALL_SCRIPT_EXEC=1
    break
  fi
done

if [[ $INSTALL_SCRIPT_EXEC == 0 ]]; then
  echo "ERROR: install.sh must be executed first."
  exit 1
fi

if [[ ! $CONFIGURE_FOR_RES_VDI =~ ^(0|1)$ ]]; then
  echo "ERROR: -v argument must be either 0 or 1 (Configure for RES VDI)."
  exit 1
fi

timestamp=$(date +%s)
echo "Post Reboot Installation logged in /root/bootstrap/logs/install_post_reboot.log.${timestamp}"
echo "Installing...."
exec > /root/bootstrap/logs/install_post_reboot.log.${timestamp} 2>&1

source /etc/environment
if [[ -f /etc/profile.d/proxy.sh ]]; then
    source /etc/profile.d/proxy.sh
fi

for ARG in "$@"
do
  if [[ "$ARG" == "crontab" ]]; then
    # clean crontab, remove current file from reboot commands
    crontab -l | grep -v 'install_post_reboot.sh' | crontab -
    break
  fi
done

echo -n "no" > ${BOOTSTRAP_DIR}/reboot_required.txt

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "${SCRIPT_DIR}/../common/bootstrap_common.sh"

if [[ ! -f ${BOOTSTRAP_DIR}/res_installed_all_packages.log ]]; then

  # Begin: Install Nice DCV Server
  /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/dcv_server.sh" -o $RES_BASE_OS -r $AWS_REGION -n $IDEA_CLUSTER_NAME -g $GPU_FAMILY -s "${SCRIPT_DIR}"
  # End: Install Nice DCV Server

  # Begin: Install Nice DCV Session Manager Agent
  /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/dcv_session_manager_agent.sh" -o $RES_BASE_OS -r $AWS_REGION -n $IDEA_CLUSTER_NAME -s "${SCRIPT_DIR}"
  # End: Install Nice DCV Session Manager Agent
  
  function install_microphone_redirect() {
    if [[ -z "$(rpm -qa pulseaudio-utils)" ]]; then
      echo "Installing microphone redirect..."
      yum install -y pulseaudio-utils
    else
      log_info "Found pulseaudio-utils pre-installed... skipping installation..."
    fi
  }

  function install_usb_support() {
    if [[ -z "$(lsmod | grep eveusb)" ]]; then
      echo "Installing usb support..."
      DCV_USB_DRIVER_INSTALLER=$(which dcvusbdriverinstaller)
      $DCV_USB_DRIVER_INSTALLER --quiet
    else
      log_info "Found eveusb kernel module pre-installed... skipping installation..."
    fi

    echo "# disable x11 display power management system"
    echo -e '
  Section "Extensions"
      Option      "DPMS" "Disable"
  EndSection' > /etc/X11/xorg.conf.d/99-disable-dpms.conf
  }

  install_usb_support
  install_microphone_redirect

  echo "$(date)" >> /root/bootstrap/res_installed_all_packages.log
  set_reboot_required "DCV and any associated GPU drivers have been installed, reboot required for changes to take effect..."
else
   log_info "Found ${BOOTSTRAP_DIR}/res_installed_all_packages.log... skipping package installation..."
fi

if [[ $CONFIGURE_FOR_RES_VDI == 1 ]]; then 
  REBOOT_REQUIRED=$(cat /root/bootstrap/reboot_required.txt)
  if [[ "${REBOOT_REQUIRED}" == "yes" ]]; then
    log_info "Triggering 2nd Reboot Required for RES Configuration for VDI"
    crontab -l | grep -v "idea-reboot-do-not-edit-or-delete-idea-notif.sh" | crontab -
    (crontab -l; echo "@reboot /bin/bash /root/bootstrap/latest/virtual-desktop-host-linux/configure.sh crontab") | crontab -
    reboot
  else
    /bin/bash /root/bootstrap/latest/virtual-desktop-host-linux/configure.sh
  fi
fi
