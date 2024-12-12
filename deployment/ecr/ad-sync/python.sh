#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

function install_python () {
  local ALIAS_PREFIX="res"
  local INSTALL_DIR="/opt/res/python"
  local PYTHON_VERSION="3.9.16"
  local PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
  local PYTHON_HASH="87acee12323b63a2e0c368193c03fd57e008585c754b6bceec6d5ec4c0bc34b3bb1ff20f31b6f5aff6e02502e7f5b291"
  local PYTHON_HASH_METHOD=sha384
  local PYTHON_TGZ="Python-${PYTHON_VERSION}.tgz"

  local PYTHON3_BIN="${INSTALL_DIR}/latest/bin/python3"
  local CURRENT_VERSION="$(${PYTHON3_BIN} --version | awk {'print $NF'})"
  if [[ "${CURRENT_VERSION}" == "${PYTHON_VERSION}" ]]; then
    echo "Python already installed and at correct version."
  else

    echo "Python not detected, installing"

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

    local PYTHON_LATEST="${INSTALL_DIR}/latest"
    ln -sf "${PYTHON_DIR}" "${PYTHON_LATEST}"
    ln -sf "${PYTHON_LATEST}/bin/python3" "${PYTHON_LATEST}/bin/res_python"
    ln -sf "${PYTHON_LATEST}/bin/pip3" "${PYTHON_LATEST}/bin/res_pip"

    popd
  fi
}

install_python

