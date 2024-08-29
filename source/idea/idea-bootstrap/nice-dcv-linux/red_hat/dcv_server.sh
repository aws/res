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
  if [[ -z "$(rpm -qa nice-dcv-server)" ]]; then
    return 1
  else
    return 0
  fi
}

function install_prerequisites() {
  local AWS=$(command -v aws)
  local DCV_AMAZONLINUX_PKGS
  if [[ -z "$(rpm -qa gnome-terminal)" ]]; then
    case $BASE_OS in
      amzn2)
        IFS=$'\n'
        DCV_AMAZONLINUX_PKGS=($($AWS dynamodb get-item \
                                              --region "$AWS_REGION" \
                                              --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                              --key '{"key": {"S": "global-settings.package_config.linux_packages.dcv_amazonlinux"}}' \
                                              --output text \
                                              | awk '/L/ {print $2}'))
        yum install -y ${DCV_AMAZONLINUX_PKGS[*]}
        unset IFS
        ;;
      rhel8|rhel9)
        yum groups mark convert
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
  local machine=$(uname -m) #x86_64 or aarch64
  local DCV_SERVER_URL=""
  local DCV_SERVER_TGZ=""
  local DCV_SERVER_VERSION=""
  local DCV_SERVER_SHA256_URL=""
  case $BASE_OS in
    amzn2)
      DCV_SERVER_URL=$($AWS dynamodb get-item \
                                    --region "$AWS_REGION" \
                                    --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                    --key '{"key": {"S": "global-settings.package_config.dcv.host.'$machine'.linux.al2.url"}}' \
                                    --output text \
                                    | awk '/VALUE/ {print $2}')
      DCV_SERVER_SHA256_URL=$($AWS dynamodb get-item \
                                    --region "$AWS_REGION" \
                                    --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                    --key '{"key": {"S": "global-settings.package_config.dcv.host.'$machine'.linux.al2.sha256sum"}}' \
                                    --output text \
                                    | awk '/VALUE/ {print $2}')
      ;;
    rhel8|rhel9)
      DCV_SERVER_URL=$($AWS dynamodb get-item \
                                    --region "$AWS_REGION" \
                                    --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                    --key '{"key": {"S": "global-settings.package_config.dcv.host.'$machine'.linux.rhel_centos_rocky'${BASE_OS:4:1}'.url"}}' \
                                    --output text \
                                    | awk '/VALUE/ {print $2}')
      DCV_SERVER_SHA256_URL=$($AWS dynamodb get-item \
                                    --region "$AWS_REGION" \
                                    --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                    --key '{"key": {"S": "global-settings.package_config.dcv.host.'$machine'.linux.rhel_centos_rocky'${BASE_OS:4:1}'.sha256sum"}}' \
                                    --output text \
                                    | awk '/VALUE/ {print $2}')
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

  if [[ "$BASE_OS" == "rhel9" ]]; then
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
    amzn2)
      rpm -ivh nice-xdcv-*.${machine}.rpm
      rpm -ivh nice-dcv-server-*.${machine}.rpm
      rpm -ivh nice-dcv-web-viewer-*.${machine}.rpm
      ;;
    rhel8|rhel9)
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
    if [[ "$GPU_FAMILY" =~ "AMD" && $BASE_OS =~ ^(rhel8|rhel9)$ ]]; then
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

  if [[ "$BASE_OS" == "amzn2" ]]; then
    log_info "Base os is amzn2. No need for firewall disabling"
  else
    systemctl stop firewalld
    systemctl disable firewalld
  fi
}

function install_gpu_driver_prerequisites() {
  echo "No GPU driver prerequisites"
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
