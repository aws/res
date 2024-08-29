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

# Begin: Install Python
while getopts r:n:a:i: opt
do
    case "${opt}" in
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        a) ALIAS_PREFIX=${OPTARG};;
        i) INSTALL_DIR=${OPTARG};;
        *) echo "Invalid option: -${OPTARG}" >&2; exit 1;;
    esac
done

if [[ -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" || -z "$ALIAS_PREFIX" || -z "$INSTALL_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

function install_python () {
  # - ALIAS_PREFIX: Will generate symlinks for python3 and pip3 for the alias:
  #   eg. if ALIAS_PREFIX == 'idea', idea_python and idea_pip will be available for use.
  # - INSTALL_DIR: the location where python will be installed.
  local AWS=$(command -v aws)
  local PYTHON_VERSION=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.python.version"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')

  local PYTHON_URL=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.python.url"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}')
  local PYTHON_HASH=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.python.checksum"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}' | tr '[:upper:]' '[:lower:]' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  local PYTHON_HASH_METHOD=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.python.checksum_method"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}' | tr '[:upper:]' '[:lower:]' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

local PYTHON_TGZ=$($AWS dynamodb get-item \
                                --region "$AWS_REGION" \
                                --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                                --key '{"key": {"S": "global-settings.package_config.python.url"}}' \
                                --output text \
                                | awk '/VALUE/ {print $2}' | xargs -n 1 basename)

  local PYTHON3_BIN="${INSTALL_DIR}/latest/bin/python3"
  local CURRENT_VERSION="$(${PYTHON3_BIN} --version | awk {'print $NF'})"
  if [[ "${CURRENT_VERSION}" == "${PYTHON_VERSION}" ]]; then
    log_info "Python already installed and at correct version."
  else

    log_info "Python not detected, installing"

    local TIMESTAMP=$(date +%s)
    local TMP_DIR="/root/bootstrap/python_installer/${ALIAS_PREFIX}-${TIMESTAMP}"
    mkdir -p "${TMP_DIR}"
    pushd ${TMP_DIR}

    wget ${PYTHON_URL}
    if [[ $(openssl ${PYTHON_HASH_METHOD} ${PYTHON_TGZ} | awk '{print $2}') != ${PYTHON_HASH} ]];  then
        echo -e "FATAL ERROR: ${PYTHON_HASH_METHOD} Checksum for Python failed. File may be compromised." > /etc/motd
        exit 1
    fi

    tar xvf ${PYTHON_TGZ}
    pushd "Python-${PYTHON_VERSION}"
    local PYTHON_DIR="${INSTALL_DIR}/${PYTHON_VERSION}"
    ./configure LDFLAGS="-L/usr/lib64/openssl" \
                CPPFLAGS="-I/usr/include/openssl" \
                -enable-loadable-sqlite-extensions \
                --prefix="${PYTHON_DIR}"

    local NUM_PROCS=`nproc --all`
    local MAKE_FLAGS="-j${NUM_PROCS}"
    make ${MAKE_FLAGS}
    make ${MAKE_FLAGS} install

    popd
    popd

    # create symlinks
    local PYTHON_LATEST="${INSTALL_DIR}/latest"
    ln -sf "${PYTHON_DIR}" "${PYTHON_LATEST}"
    ln -sf "${PYTHON_LATEST}/bin/python3" "${PYTHON_LATEST}/bin/${ALIAS_PREFIX}_python"
    ln -sf "${PYTHON_LATEST}/bin/pip3" "${PYTHON_LATEST}/bin/${ALIAS_PREFIX}_pip"
  fi
}
install_python
# End Install Python

