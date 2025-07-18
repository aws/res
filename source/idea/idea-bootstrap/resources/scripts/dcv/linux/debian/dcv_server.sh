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

source "$PLATFORM_SCRIPT_DIR/../../../common/linux/bootstrap_common.sh"
source "$PLATFORM_SCRIPT_DIR/../../../common/linux/config_common.sh"

function pre_installed() {
  if [[ -z "$(apt -qq list nice-dcv-server)" ]]; then
    return 1
  else
    return 0
  fi
}

function install_prerequisites() {
  case $BASE_OS in
    ubuntu2204|ubuntu2404)
      PREREQUISITES=($(get_list 'package_config.dcv.host.prerequisites.debian.ubuntu'))
      DEBIAN_FRONTEND=noninteractive apt install -y ${PREREQUISITES[*]}
      ;;
    *)
      log_warning "Base OS not supported."
      exit 1
      ;;
  esac
}

function install_nice_dcv_server () {
  local BASE_OS=$1
  local GPU_FAMILY=$2

  local DCV_GPG_KEY_DCV_SERVER=$(get_string "package_config.dcv.gpg_key")
  local machine=$(uname -m)
  local DCV_SERVER_URL=$(get_string "package_config.dcv.host.${machine}.debian.${BASE_OS}.url")
  local DCV_SERVER_SHA256_URL=$(get_string "package_config.dcv.host.${machine}.debian.${BASE_OS}.sha256sum")

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
  IFS=$'\n'
  GPU_DRIVER_PREREQUISITES=($(get_list 'package_config.gpu_driver.prerequisites.debian'))

  # Evaluate embedded commands
  EVALUATED_GPU_DRIVER_PREREQUISITES=()
  for pkg in "${GPU_DRIVER_PREREQUISITES[@]}"; do
      EVALUATED_GPU_DRIVER_PREREQUISITES+=("$(eval echo "$pkg")")
  done

  DEBIAN_FRONTEND=noninteractive apt install -y ${EVALUATED_GPU_DRIVER_PREREQUISITES[*]}
  if [[ $BASE_OS =~ ^(ubuntu2204|ubuntu2404)$ ]]; then
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 12
  fi
  unset IFS
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

function install_modified_x_server() {
  local GPU_FAMILY=$1
  if [[ ! $GPU_FAMILY =~ ^(NVIDIA|AMD)$ ]]; then
    echo 'Detected no GPU instance, configuring x windows server'
    echo 'Section "Device"
    Identifier "DummyDevice"
    Driver "dummy"
    Option "UseEDID" "false"
    VideoRam 512000
EndSection

Section "Monitor"
    Identifier "DummyMonitor"
    HorizSync   5.0 - 1000.0
    VertRefresh 5.0 - 200.0
    Option "ReducedBlanking"
EndSection

Section "Screen"
    Identifier "DummyScreen"
    Device "DummyDevice"
    Monitor "DummyMonitor"
    DefaultDepth 24
    SubSection "Display"
        Viewport 0 0
        Depth 24
        Virtual 4096 2160
    EndSubSection
EndSection
  ' > /etc/X11/xorg.conf
  DEBIAN_FRONTEND=noninteractive apt install -y xserver-xorg-video-dummy
  else
    echo "Detected GPU instance, no need for modified x configuration"
  fi
}
