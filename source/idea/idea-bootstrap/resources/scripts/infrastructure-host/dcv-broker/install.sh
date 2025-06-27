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

while getopts o:s: opt
do
  case "${opt}" in
    s) SCRIPT_DIR=${OPTARG};;
    ?) echo "Invalid option for system_packages.sh script: -${opt}."
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
  amzn2)
    PLATFORM="al2"
    ;;
  amzn2023)
    PLATFORM="al2023"
    ;;
  rhel8)
    PLATFORM="rhel_centos_rocky8"
    ;;
  rhel9|rocky9)
    PLATFORM="rhel_centos_rocky9"
    ;;
  *)
    echo -e "Invalid OS for DCV broker: ${BASE_OS}" > /etc/motd
    exit 1
    ;;
esac

DCV_GPG_KEY=$(get_string "package_config.dcv.gpg_key")
DCV_SESSION_MANAGER_BROKER_URL=$(get_string "package_config.dcv.broker.linux.${PLATFORM}.url")
DCV_SESSION_MANAGER_BROKER_SHA256_URL=$(get_string "package_config.dcv.broker.linux.${PLATFORM}.sha256sum")

STAGING_AREA_RELATIVE_PATH='staging_area'
function setup_staging_area() {
  echo "setup staging area start"
  mkdir -p ${STAGING_AREA_RELATIVE_PATH}
  rm -rf '${STAGING_AREA_RELATIVE_PATH}/*'
  echo "setup staging area end"
}

function install_dcv_broker_package() {
  echo "dcv session manager broker package installation start."
  setup_staging_area


  which dcv-session-manager-broker
  if [[ "$?" != "0" ]]; then
    rpm --import ${DCV_GPG_KEY}
    pushd ${STAGING_AREA_RELATIVE_PATH}
    wget ${DCV_SESSION_MANAGER_BROKER_URL}
    fileName=$(basename ${DCV_SESSION_MANAGER_BROKER_URL})
    urlSha256Sum=$(wget -O - ${DCV_SESSION_MANAGER_BROKER_SHA256_URL})
    if [[ $(sha256sum ${fileName} | awk '{print $1}') != ${urlSha256Sum} ]];  then
      echo -e "FATAL ERROR: Checksum for DCV Broker failed. File may be compromised." > /etc/motd
      exit 1
    fi
    yum install -y ${fileName}
    popd
  fi
  echo "dcv session manager broker package installation complete."
}

install_dcv_broker_package
