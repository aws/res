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
while getopts o:s: opt
do
  case "${opt}" in
    o) BASE_OS=${OPTARG};;
    s) SCRIPT_DIR=${OPTARG};;
    ?) echo "Invalid option for python.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
source "${SCRIPT_DIR}/../common/linux/config_common.sh"

function install_python () {
  # Install Python via pyenv https://github.com/pyenv/pyenv
  local ALIAS_PREFIX="idea"
  local INSTALL_DIR="/opt/idea/python"
  local PYTHON3_BIN="${INSTALL_DIR}/latest/bin/python3"
  local CURRENT_VERSION="$(${PYTHON3_BIN} --version | awk {'print $NF'})"
  local PYTHON_VERSION=$(get_string 'package_config.python.version')
  if [[ "${CURRENT_VERSION}" == "${PYTHON_VERSION}" ]]; then
    log_info "Python already installed and at correct version."
  else
    case $BASE_OS in
      amzn2)
        local PYTHON_BUILD_DEPENDENCY=($(get_list 'package_config.python.build_dependencies.red_hat.al2'))
        yum install -y ${PYTHON_BUILD_DEPENDENCY[*]} --skip-broken
        ;;
      amzn2023)
        local PYTHON_BUILD_DEPENDENCY=($(get_list 'package_config.python.build_dependencies.red_hat.amzn2023'))
        yum install -y ${PYTHON_BUILD_DEPENDENCY[*]} --skip-broken
        ;;
      rhel8|rhel9|rocky9)
        PYTHON_BUILD_DEPENDENCY=($(get_list 'package_config.python.build_dependencies.red_hat.rhel'))
        yum install -y ${PYTHON_BUILD_DEPENDENCY[*]} --skip-broken
        ;;
      ubuntu2204)
        PYTHON_BUILD_DEPENDENCY=($(get_list 'package_config.python.build_dependencies.debian.ubuntu2204'))
        apt install -y ${PYTHON_BUILD_DEPENDENCY[*]}
        ;;
      *)
        echo "Invalid OS for installing Python."
        exit 1;;
    esac

    export PYENV_ROOT="${INSTALL_DIR}"
    curl https://pyenv.run | bash

    echo "export PYENV_ROOT=\"${INSTALL_DIR}\"" >> ~/.bashrc
    echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo 'eval "$(pyenv init - bash)"' >> ~/.bashrc
    source ~/.bashrc

    if [ -e ~/.bash_profile ]; then
      echo "export PYENV_ROOT=\"${INSTALL_DIR}\"" >> ~/.bash_profile
      echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
      echo 'eval "$(pyenv init - bash)"' >> ~/.bash_profile
      source ~/.bash_profile
    elif [ -e ~/.bash_login ]; then
      echo "export PYENV_ROOT=\"${INSTALL_DIR}\"" >> ~/.bash_login
      echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_login
      echo 'eval "$(pyenv init - bash)"' >> ~/.bash_login
      source ~/.bash_login
    else
      echo "export PYENV_ROOT=\"${INSTALL_DIR}\"" >> ~/.profile
      echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.profile
      echo 'eval "$(pyenv init - bash)"' >> ~/.profile
      source ~/.profile
    fi

    pyenv install ${PYTHON_VERSION}

    local PYTHON_DIR="${INSTALL_DIR}/versions/${PYTHON_VERSION}"
    # create symlinks
    local PYTHON_LATEST="${INSTALL_DIR}/latest"
    ln -sf "${PYTHON_DIR}" "${PYTHON_LATEST}"
    ln -sf "${PYTHON_LATEST}/bin/python3" "/usr/local/bin/${ALIAS_PREFIX}_python"
    ln -sf "${PYTHON_LATEST}/bin/pip3" "/usr/local/bin/${ALIAS_PREFIX}_pip"
  fi
}
install_python
# End Install Python
