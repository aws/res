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

# Begin: DCV Server
set -x

while getopts o:r:n:g:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        g) GPU_FAMILY=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" || -z "$GPU_FAMILY" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

function install_gpu_drivers() {
  if [[ $GPU_FAMILY =~ ^(NVIDIA|AMD)$ ]]; then
    log_info "Installing GPU drivers"
    sudo rm -rf /etc/X11/XF86Config*
    /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/gpu_drivers.sh" -o $RES_BASE_OS -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -g $GPU_FAMILY -s "${SCRIPT_DIR}"
  else
    log_info "GPU InstanceType not detected. Skipping GPU driver installation."
  fi
}

function install_gnome_terminal() {
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
      rhel7|rhel8|rhel9)
        yum groups mark convert
        yum groupinstall "Server with GUI" -y --skip-broken
        ;;
      centos7)
        yum groups mark convert
        yum groupinstall "GNOME Desktop" -y --skip-broken
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

function download_nice_dcv_server () {
  local AWS=$(command -v aws)
  local DCV_GPG_KEY_DCV_SERVER=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.gpg_key"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
  local machine=$(uname -m) #x86_64 or aarch64
  local DCV_SERVER_X86_64_URL
  local DCV_SERVER_X86_64_TGZ
  local DCV_SERVER_X86_64_VERSION
  local DCV_SERVER_X86_64_SHA256_HASH
  local DCV_SERVER_AARCH64_URL
  local DCV_SERVER_AARCH64_TGZ
  local DCV_SERVER_AARCH64_VERSION
  local DCV_SERVER_AARCH64_SHA256_HASH
  if [[ $machine == "x86_64" ]]; then
    case $BASE_OS in
      amzn2|centos7|rhel7)
        DCV_SERVER_X86_64_URL=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.x86_64.linux.al2_rhel_centos7.url"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_X86_64_TGZ=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.x86_64.linux.al2_rhel_centos7.tgz"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_X86_64_VERSION=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.x86_64.linux.al2_rhel_centos7.version"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_X86_64_SHA256_HASH=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.x86_64.linux.al2_rhel_centos7.sha256sum"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        ;;
      rhel8|rhel9)
        DCV_SERVER_X86_64_URL=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.x86_64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.url"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_X86_64_TGZ=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.x86_64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.tgz"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_X86_64_VERSION=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.x86_64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.version"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_X86_64_SHA256_HASH=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.x86_64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.sha256sum"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        ;;
      *)
        log_warning "Base OS not supported."
        exit 1
        ;;
    esac
  else
    case $BASE_OS in
      amzn2|centos7|rhel7)
        DCV_SERVER_AARCH64_URL=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.aarch64.linux.al2_rhel_centos7.url"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_AARCH64_TGZ=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.aarch64.linux.al2_rhel_centos7.tgz"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_AARCH64_VERSION=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.aarch64.linux.al2_rhel_centos7.version"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_AARCH64_SHA256_HASH=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.aarch64.linux.al2_rhel_centos7.sha256sum"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        ;;
      rhel8|rhel9)
        DCV_SERVER_AARCH64_URL=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.aarch64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.url"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_AARCH64_TGZ=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.aarch64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.tgz"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_AARCH64_VERSION=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.aarch64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.version"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        DCV_SERVER_AARCH64_SHA256_HASH=$($AWS dynamodb get-item \
                                      --region "$AWS_REGION" \
                                      --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                      --key '{"key": {"S": "global-settings.package_config.dcv.host.aarch64.linux.rhel_centos_rocky'${BASE_OS:4:1}'.sha256sum"}}' \
                                      --output text \
                                      | awk '/VALUE/ {print $2}')
        ;;
      *)
        log_warning "Base OS not supported."
        exit 1
        ;;
    esac
  fi

  rpm --import ${DCV_GPG_KEY_DCV_SERVER}
  DCV_SERVER_URL=""
  DCV_SERVER_TGZ=""
  DCV_SERVER_VERSION=""
  DCV_SERVER_SHA256_HASH=""
  if [[ $machine == "x86_64" ]]; then
    # x86_64
    DCV_SERVER_URL=${DCV_SERVER_X86_64_URL}
    DCV_SERVER_TGZ=${DCV_SERVER_X86_64_TGZ}
    DCV_SERVER_VERSION=${DCV_SERVER_X86_64_VERSION}
    DCV_SERVER_SHA256_HASH=${DCV_SERVER_X86_64_SHA256_HASH}
  else
    # aarch64
    DCV_SERVER_URL=${DCV_SERVER_AARCH64_URL}
    DCV_SERVER_TGZ=${DCV_SERVER_AARCH64_TGZ}
    DCV_SERVER_VERSION=${DCV_SERVER_AARCH64_VERSION}
    DCV_SERVER_SHA256_HASH=${DCV_SERVER_AARCH64_SHA256_HASH}
  fi

  wget ${DCV_SERVER_URL}
  if [[ $(sha256sum ${DCV_SERVER_TGZ} | awk '{print $1}') != ${DCV_SERVER_SHA256_HASH} ]];  then
    echo -e "FATAL ERROR: Checksum for DCV Server failed. File may be compromised." > /etc/motd
    exit 1
  fi
  tar zxvf ${DCV_SERVER_TGZ}

  if [[ "$BASE_OS" == "rhel9" ]]; then
    if [[ -z "$(rpm -qa pcsc-lite-libs)" ]]; then
      log_info "pcsc-lite-libs not found - installing"
      wget https://rpmfind.net/linux/fedora/linux/development/rawhide/Everything/x86_64/os/Packages/p/pcsc-lite-libs-2.0.0-2.fc39.x86_64.rpm
      rpm -ivh pcsc-lite-libs-2.0.0-2.fc39.x86_64.rpm
    else
      log_info "pcsc-lite-libs found - not installing"
    fi
  fi
}

function install_nice_dcv_server () {
  local machine=$(uname -m) #x86_64 or aarch64
  pushd nice-dcv-${DCV_SERVER_VERSION}

  case $BASE_OS in
    amzn2)
      rpm -ivh nice-xdcv-*.${machine}.rpm
      rpm -ivh nice-dcv-server-*.${machine}.rpm
      rpm -ivh nice-dcv-web-viewer-*.${machine}.rpm
      ;;
    centos7|rhel7|rhel8|rhel9)
      rpm -ivh nice-xdcv-*.${machine}.rpm --nodeps
      rpm -ivh nice-dcv-server-*.${machine}.rpm --nodeps
      rpm -ivh nice-dcv-web-viewer-*.${machine}.rpm --nodeps
      ;;
    *)
      log_warning "Base OS not supported."
      exit 1
      ;;
  esac

  if [[ $GPU_FAMILY =~ ^(NVIDIA|AMD)$ ]]; then
    if [[ $machine == "x86_64" ]]; then
      echo "Detected GPU instance, adding support for nice-dcv-gl"
      rpm -ivh nice-dcv-gl*.x86_64.rpm
    fi
  fi

  popd
  rm -rf nice-dcv-${DCV_SERVER_VERSION}
  rm -rf ${DCV_SERVER_TGZ}

  if [[ "$BASE_OS" == "amzn2" ]]; then
    log_info "Base os is amzn2. No need for firewall disabling"
  else
    systemctl stop firewalld
    systemctl disable firewalld
  fi
}


if [[ $BASE_OS =~ ^(amzn2|centos7|rhel7|rhel8|rhel9)$ ]]; then
  install_gpu_drivers
  install_gnome_terminal
  if [[ -z "$(rpm -qa nice-dcv-server)" ]]; then
    download_nice_dcv_server
    install_nice_dcv_server
  else
    log_info "Found nice-dcv-server pre-installed... skipping installation..."
  fi
else
  log_warning "Base OS not supported."
  exit 1
fi
# End: DCV Server
