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
  if [[ -z "$(rpm -qa nice-dcv-server)" ]]; then
    return 1
  else
    return 0
  fi
}

function install_prerequisites() {
  local DCV_AMAZONLINUX_PKGS
  if [[ -z "$(rpm -qa gnome-terminal)" ]]; then
    case $BASE_OS in
      amzn2)
        IFS=$'\n'
        DCV_AMAZONLINUX_PKGS=$(get_list "package_config.dcv.host.prerequisites.red_hat.al2")
        yum install -y ${DCV_AMAZONLINUX_PKGS[*]}
        unset IFS
        ;;
      amzn2023)
        dnf groupinstall "Desktop" -y
        ;;
      rhel8|rhel9|rocky9)
        yum groupinstall "Server with GUI" -y --skip-broken --exclude=kernel*
        ;;
      *)
        log_warning "Base OS not supported."
        exit 1
        ;;
    esac
  else
    log_info "Found gnome-terminal pre-installed... skipping dcv prereq installation..."
  fi
}

function install_nice_dcv_server () {
  local BASE_OS=$1
  local GPU_FAMILY=$2

  local DCV_GPG_KEY_DCV_SERVER=$(get_string "package_config.dcv.gpg_key")
  local machine=$(uname -m) #x86_64 or aarch64
  local DCV_SERVER_URL=""
  local DCV_SERVER_TGZ=""
  local DCV_SERVER_VERSION=""
  local DCV_SERVER_SHA256_URL=""
  case $BASE_OS in
    amzn2)
      DCV_SERVER_URL=$(get_string "package_config.dcv.host.${machine}.linux.al2.url")
      DCV_SERVER_SHA256_URL=$(get_string "package_config.dcv.host.${machine}.linux.al2.sha256sum")
      ;;
    amzn2023)
      DCV_SERVER_URL=$(get_string "package_config.dcv.host.${machine}.linux.al2023.url")
      DCV_SERVER_SHA256_URL=$(get_string "package_config.dcv.host.${machine}.linux.al2023.sha256sum")
      ;;
    rhel8)
      DCV_SERVER_URL=$(get_string "package_config.dcv.host.${machine}.linux.rhel_centos_rocky8.url")
      DCV_SERVER_SHA256_URL=$(get_string "package_config.dcv.host.${machine}.linux.rhel_centos_rocky8.sha256sum")
      ;;
    rhel9|rocky9)
      DCV_SERVER_URL=$(get_string "package_config.dcv.host.${machine}.linux.rhel_centos_rocky9.url")
      DCV_SERVER_SHA256_URL=$(get_string "package_config.dcv.host.${machine}.linux.rhel_centos_rocky9.sha256sum")
      ;;
    *)
      log_warning "Base OS not supported."
      exit 1
      ;;
  esac

  rpm --import ${DCV_GPG_KEY_DCV_SERVER}

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

  if [[ "$BASE_OS" == "rhel9" ]] || [[ "$BASE_OS" == "rocky9" ]]; then
    if [[ -z "$(rpm -qa pcsc-lite-libs)" ]]; then
      log_info "pcsc-lite-libs not found - installing"
      wget https://rpmfind.net/linux/fedora/linux/development/rawhide/Everything/x86_64/os/Packages/p/pcsc-lite-libs-2.0.0-2.fc39.x86_64.rpm
      rpm -ivh pcsc-lite-libs-2.0.0-2.fc39.x86_64.rpm
    else
      log_info "pcsc-lite-libs found - not installing"
    fi
  fi

  local machine=$(uname -m) #x86_64 or aarch64
  pushd ${extractDir}

  case $BASE_OS in
    amzn2|amzn2023)
      rpm -ivh nice-xdcv-*.${machine}.rpm
      rpm -ivh nice-dcv-server-*.${machine}.rpm
      rpm -ivh nice-dcv-web-viewer-*.${machine}.rpm
      ;;
    rhel8|rhel9|rocky9)
      rpm -ivh nice-xdcv-*.${machine}.rpm --nodeps
      rpm -ivh nice-dcv-server-*.${machine}.rpm --nodeps
      rpm -ivh nice-dcv-web-viewer-*.${machine}.rpm --nodeps
      ;;
    *)
      log_warning "Base OS not supported."
      exit 1
      ;;
  esac

  if [[ $GPU_FAMILY =~ ^(NVIDIA|AMD)$ && $machine == "x86_64" ]]; then
    if [[ "$GPU_FAMILY" =~ "AMD" && $BASE_OS =~ ^(rhel8|rhel9|rocky9)$ ]]; then
      echo "The latest AMD driver hasn't supported the current Linux version yet"
    else
      echo "Detected GPU instance, adding support for nice-dcv-gl"
      yum install -y libGLU
      rpm -ivh nice-dcv-gl*.x86_64.rpm
    fi
  fi

  popd
  rm -rf ${extractDir}
  rm -rf ${fileName}

  if [[ "$BASE_OS" == "amzn2" ]] || [[ "$BASE_OS" == "amzn2023" ]]; then
    log_info "Base os is amzn2/amzn2023. No need for firewall disabling"
  else
    systemctl stop firewalld
    systemctl disable firewalld
  fi
}

function install_gpu_driver_prerequisites() {
  IFS=$'\n'
  GPU_DRIVER_PREREQUISITES=($(get_list 'package_config.gpu_driver.prerequisites.red_hat'))

  # Evaluate embedded commands
  EVALUATED_GPU_DRIVER_PREREQUISITES=()
  for pkg in "${GPU_DRIVER_PREREQUISITES[@]}"; do
      EVALUATED_GPU_DRIVER_PREREQUISITES+=("$(eval echo "$pkg")")
  done

  sudo yum install -y ${EVALUATED_GPU_DRIVER_PREREQUISITES[*]}
  unset IFS
}

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
    yum install -y dkms
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
  dnf install -y xorg-x11-drv-dummy
  else
    echo "Detected GPU instance, no need for modified x configuration"
  fi
}
