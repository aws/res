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

while getopts s: opt
do
  case "${opt}" in
    s) SCRIPT_DIR=${OPTARG};;
    ?) echo "Invalid option for dcv-connection-gateway install.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
source "${SCRIPT_DIR}/../common/linux/config_common.sh"

BASE_OS=$(get_base_os)

PLATFORM=""
case $BASE_OS in
  amzn2|amzn2023)
    PLATFORM="al2"
    ;;
  rhel8)
    PLATFORM="rhel_centos_rocky8"
    ;;
  rhel9|rocky9)
    PLATFORM="rhel_centos_rocky9"
    ;;
  *)
    echo -e "Invalid OS for DCV connection gateway: ${BASE_OS}" > /etc/motd
    exit 1
    ;;
esac

DCV_GPG_KEY=$(get_string "package_config.dcv.gpg_key")

DCV_CONNECTION_GATEWAY_URL=$(get_string "package_config.dcv.connection_gateway.x86_64.linux.${PLATFORM}.url")
DCV_CONNECTION_GATEWAY_SHA256_URL=$(get_string "package_config.dcv.connection_gateway.x86_64.linux.${PLATFORM}.sha256sum")

DCV_SERVER_X86_64_URL=$(get_string "package_config.dcv.host.x86_64.linux.${PLATFORM}.url")
DCV_SERVER_X86_64_SHA256_URL=$(get_string "package_config.dcv.host.x86_64.linux.${PLATFORM}.sha256sum")

DCV_SERVER_AARCH64_URL=$(get_string "package_config.dcv.host.aarch64.linux.${PLATFORM}.url")
DCV_SERVER_AARCH64_SHA256_URL=$(get_string "package_config.dcv.host.aarch64.linux.${PLATFORM}.sha256sum")

DCV_WEB_VIEWER_INSTALL_LOCATION="/usr/share/dcv/www"

function install_dcv_connection_gateway() {
  rpm -q nice-dcv-connection-gateway
  if [[ "$?" != "0"  ]]; then
    yum install -y nc
    rpm --import ${DCV_GPG_KEY}
    wget ${DCV_CONNECTION_GATEWAY_URL}
    fileName=$(basename ${DCV_CONNECTION_GATEWAY_URL})
    urlSha256Sum=$(wget -O - ${DCV_CONNECTION_GATEWAY_SHA256_URL})
    if [[ $(sha256sum ${fileName} | awk '{print $1}') != ${urlSha256Sum} ]];  then
      echo -e "FATAL ERROR: Checksum for DCV Connection Gateway failed. File may be compromised." > /etc/motd
      exit 1
    fi
    yum install -y ${fileName}
    rm -f ${fileName}
  fi
}

function install_dcv_web_viewer() {
  echo "# installing dcv web viewer ..."

  local machine=$(uname -m) #x86_64 or aarch64
  local DCV_SERVER_URL=""
  local DCV_SERVER_SHA256_URL=""
  if [[ $machine == "x86_64" ]]; then
    # x86_64
    DCV_SERVER_URL=${DCV_SERVER_X86_64_URL}
    DCV_SERVER_SHA256_URL=${DCV_SERVER_X86_64_SHA256_URL}
  else
    # aarch64
    DCV_SERVER_URL=${DCV_SERVER_AARCH64_URL}
    DCV_SERVER_SHA256_URL=${DCV_SERVER_AARCH64_SHA256_URL}
  fi

  rpm -q nice-dcv-web-viewer
  if [[ "$?" != "0"  ]]; then
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

    pushd ${extractDir}
    if [[ $BASE_OS == "amzn2" ]] || [[ $BASE_OS == "amzn2023" ]]; then
      rpm -ivh nice-dcv-web-viewer-*.${machine}.rpm
    elif [[ $BASE_OS =~ ^(rhel8|rhel9|rocky9)$ ]]; then
      rpm -ivh nice-dcv-web-viewer-*.${machine}.rpm --nodeps
    fi
    popd
    rm -rf ${extractDir}
    rm -rf ${fileName}
  fi
}

install_dcv_connection_gateway
install_dcv_web_viewer
