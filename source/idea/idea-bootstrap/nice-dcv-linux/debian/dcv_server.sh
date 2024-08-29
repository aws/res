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

PLATFORM_SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

source "$PLATFORM_SCRIPT_DIR/../../common/bootstrap_common.sh"

function pre_installed() {
  if [[ -z "$(apt -qq list nice-dcv-server)" ]]; then
    return 1
  else
    return 0
  fi
}

function install_prerequisites() {
  DEBIAN_FRONTEND=noninteractive apt install -y ubuntu-desktop
  DEBIAN_FRONTEND=noninteractive apt install -y gdm3
}

function install_nice_dcv_server () {
  local BASE_OS=$1
  local AWS_REGION=$2
  local RES_ENVIRONMENT_NAME=$3
  local GPU_FAMILY=$4

  local AWS=$(command -v aws)
  local DCV_GPG_KEY_DCV_SERVER=$($AWS dynamodb get-item \
                              --region "$AWS_REGION" \
                              --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                              --key '{"key": {"S": "global-settings.package_config.dcv.gpg_key"}}' \
                              --output text \
                              | awk '/VALUE/ {print $2}')
  local machine=$(uname -m)
  local DCV_SERVER_URL=$($AWS dynamodb get-item \
                              --region "$AWS_REGION" \
                              --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                              --key '{"key": {"S": "global-settings.package_config.dcv.host.'$machine'.ubuntu.'$BASE_OS'.url"}}' \
                              --output text \
                              | awk '/VALUE/ {print $2}')
  local DCV_SERVER_SHA256_URL=$($AWS dynamodb get-item \
                              --region "$AWS_REGION" \
                              --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                              --key '{"key": {"S": "global-settings.package_config.dcv.host.'$machine'.ubuntu.'$BASE_OS'.sha256sum"}}' \
                              --output text \
                              | awk '/VALUE/ {print $2}')

  wget ${DCV_GPG_KEY_DCV_SERVER}
  gpg --import NICE-GPG-KEY

  wget ${DCV_SERVER_URL}
  fileName=$(basename ${DCV_SERVER_URL})
  urlSha256Sum=$(wget -O - ${DCV_SERVER_SHA256_URL})
  if [[ $(sha256sum ${fileName} | awk '{print $1}') != ${urlSha256Sum} ]];  then
    echo -e "FATAL ERROR: Checksum for DCV Server failed. File may be compromised." > /etc/motd
    exit 1
  fi
  extractDir=$(echo ${fileName} |  sed 's/\.tgz$//')
  mkdir -p ${extractDir}
  tar zxvf ${fileName} -C ${extractDir} --strip-components 1
  
  local machine=$(uname -m)
  pushd ${extractDir}

  if [[ "$machine" == "x86_64" ]]; then
    DEBIAN_FRONTEND=noninteractive apt install -y ./nice-dcv-server_*_amd64.$BASE_OS.deb
    DEBIAN_FRONTEND=noninteractive apt install -y ./nice-dcv-web-viewer_*_amd64.$BASE_OS.deb
    usermod -aG video dcv

    DEBIAN_FRONTEND=noninteractive apt install -y ./nice-xdcv_*_amd64.$BASE_OS.deb
  fi

  if [[ $GPU_FAMILY =~ ^(NVIDIA|AMD)$ ]]; then
    if [[ $machine == "x86_64" ]]; then
      echo "Detected GPU instance, adding support for nice-dcv-gl"
      DEBIAN_FRONTEND=noninteractive apt install -y ./nice-dcv-gl*_amd64.$BASE_OS.deb
    fi
  fi

  popd
  rm -rf ${extractDir}
  rm -rf ${fileName}
}

function install_gpu_driver_prerequisites() {
  DEBIAN_FRONTEND=noninteractive apt install -y mesa-utils gcc make linux-headers-$(uname -r)
}

function install_microphone_redirect() {
  if [[ -z "$(apt -qq list pulseaudio-utils)" ]]; then
    echo "Installing microphone redirect..."
    apt install -y pulseaudio-utils
  else
    log_info "Found pulseaudio-utils pre-installed... skipping installation..."
  fi
}

function install_usb_support() {
  if [[ -z "$(lsmod | grep eveusb)" ]]; then
    echo "Installing usb support..."
    DEBIAN_FRONTEND=noninteractive apt install -y dkms
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
