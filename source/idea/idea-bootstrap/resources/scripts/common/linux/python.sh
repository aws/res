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
  # Add RES Python to PATH
  current_path=$(grep "^PATH=" /etc/environment | cut -d'"' -f2)
  if [ -z "$current_path" ]; then
      # If no PATH line exists, create new one
      echo 'PATH="/opt/idea/python/latest/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin"' >> /etc/environment
  else
      # Add new path to existing PATH
      new_path="/opt/idea/python/latest/bin:$current_path"
      sed -i 's|^PATH=.*|PATH="'"$new_path"'"|' /etc/environment
  fi

  source /etc/environment

  local ALIAS_PREFIX="idea"
  local INSTALL_DIR="/opt/idea/python"
  local PYTHON_LATEST="${INSTALL_DIR}/latest"

  if command -v python3 &> /dev/null; then
    # Use the system Python if exists and meets the minimum version requirement
    local PYTHON3_BIN=$(which python3)
    local CURRENT_VERSION="$(${PYTHON3_BIN} --version | awk {'print $NF'})"
    local MINIMUM_VERSION="3.12.0"
    local PYTHON_VERSION=$(get_string 'package_config.python.version')
    if [ "$(printf '%s\n' "$MINIMUM_VERSION" "$CURRENT_VERSION" | sort -V | head -n1)" = "$MINIMUM_VERSION" ]; then
      log_info "Python ${CURRENT_VERSION} is already installed and meets the requirement."

      # Create a virtual environment to avoid modifying the system Python
      python3 -m venv ${PYTHON_LATEST}

      # Create symlinks that point to the Python virtual environment
      ln -sf ${PYTHON_LATEST}/bin/python "${PYTHON_LATEST}/bin/${ALIAS_PREFIX}_python"
      ln -sf ${PYTHON_LATEST}/bin/pip "${PYTHON_LATEST}/bin/${ALIAS_PREFIX}_pip"

      exit 0
    fi
  fi

  # Install Python via pyenv https://github.com/pyenv/pyenv
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
    ubuntu2204|ubuntu2404)
      PYTHON_BUILD_DEPENDENCY=($(get_list 'package_config.python.build_dependencies.debian.ubuntu'))
      apt install -y ${PYTHON_BUILD_DEPENDENCY[*]}
      ;;
    *)
      echo "Invalid OS for installing Python."
      exit 1;;
  esac

  export PYENV_ROOT="${INSTALL_DIR}"
  curl https://pyenv.run | bash
  [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init - bash)"

  pyenv install ${PYTHON_VERSION}

  local PYTHON_DIR="${INSTALL_DIR}/versions/${PYTHON_VERSION}"

  # Create a virtual environment to avoid modifying the system Python
  ${PYTHON_DIR}/bin/python3 -m venv ${PYTHON_LATEST}

  # Create symlinks that point to the Python virtual environment
  ln -sf "${PYTHON_LATEST}/bin/python3" "${PYTHON_LATEST}/bin/${ALIAS_PREFIX}_python"
  ln -sf "${PYTHON_LATEST}/bin/pip3" "${PYTHON_LATEST}/bin/${ALIAS_PREFIX}_pip"
}
install_python
# End Install Python
