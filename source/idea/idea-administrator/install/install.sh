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

# RES Administrator Installation Script

IDEA_APP_DEPLOY_DIR="/root/.idea"
IDEA_CDK_VERSION="2.*"

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

IDEA_LIB_DIR="${IDEA_APP_DEPLOY_DIR}/lib"
IDEA_BIN_DIR="${IDEA_APP_DEPLOY_DIR}/bin"
IDEA_OLD_DIR="${IDEA_APP_DEPLOY_DIR}/old"
IDEA_DOWNLOADS_DIR="${IDEA_APP_DEPLOY_DIR}/downloads"
IDEA_CDK_DIR="${IDEA_LIB_DIR}/idea-cdk"

exit_fail () {
    echo -e "Installation Failed: $1"
    exit 1
}

setup_deploy_dir () {
  mkdir -p "${IDEA_APP_DEPLOY_DIR}"
  mkdir -p "${IDEA_LIB_DIR}"
  mkdir -p "${IDEA_BIN_DIR}"
  mkdir -p "${IDEA_DOWNLOADS_DIR}"
  mkdir -p "${IDEA_LIB_DIR}"
  mkdir -p "${IDEA_OLD_DIR}"
}

check_and_install_cdk () {
  echo "installing aws-cdk for RES ..."
  mkdir -p "${IDEA_CDK_DIR}"
  pushd "${IDEA_CDK_DIR}"
  npm init --force --yes
  npm install "aws-cdk@${IDEA_CDK_VERSION}" --save
  popd
}

function install () {
  setup_deploy_dir
  check_and_install_cdk
  pip install --default-timeout=100 -r ${SCRIPT_DIR}/requirements.txt
  pip install $(ls ${SCRIPT_DIR}/*-lib.tar.gz)
  local APP_DIR="${IDEA_APP_DEPLOY_DIR}/idea-administrator"
  mkdir -p "${APP_DIR}"
  mv ${SCRIPT_DIR}/resources ${APP_DIR}
}

install