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
    o) BASE_OS=${OPTARG};;
    s) SCRIPT_DIR=${OPTARG};;
    ?) echo "Invalid option for fsx_lustre_client.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
source "${SCRIPT_DIR}/../common/linux/config_common.sh"

# Begin: Install FSx Lustre Client
# Follow instructions at https://docs.aws.amazon.com/fsx/latest/LustreGuide/install-lustre-client.html
if [[ $BASE_OS == "amzn2" ]]; then
  if [[ -z "$(rpm -qa lustre-client)" ]]; then
    LUSTRE_PKGS=($(get_list 'package_config.fsx_lustre_client.red_hat.al2'))
    amazon-linux-extras install -y ${LUSTRE_PKGS[*]}
  fi
elif [[ $BASE_OS == "amzn2023" ]]; then
  if [[ -z "$(rpm -qa lustre-client)" ]]; then
    LUSTRE_PKGS=($(get_list 'package_config.fsx_lustre_client.red_hat.al2023'))
    dnf install -y ${LUSTRE_PKGS[*]}
  fi
elif [[ $BASE_OS == "rhel8" ]]; then
  if [[ -z "$(rpm -qa lustre-client)" ]]; then
    kernel=$(uname -r)
    machine=$(uname -m)
    unmatch=true
    log_info "Found kernel version: $kernel running on: $machine"

    declare -A kernel_versions=(
      ["4.18.0-553"]=""
      ["4.18.0-513"]="8.9"
      ["4.18.0-477"]="8.8"
      ["4.18.0-425"]="8.7"
      ["4.18.0-372"]="8.6"
      ["4.18.0-348"]="8.5"
      ["4.18.0-305"]="8.4"
      ["4.18.0-240"]="8.3"
      ["4.18.0-193"]="8.2"
    )

    for kernel_base in "${!kernel_versions[@]}"; do
      if [[ $kernel == *"$kernel_base"*"$machine" ]]; then
        unmatch=false
        PUBLIC_KEY=($(get_string 'package_config.fsx_lustre_client.prerequisites.red_hat.public_key'))
        REPO=($(get_string 'package_config.fsx_lustre_client.prerequisites.red_hat.repo.rhel8'))
        LUSTRE_PKGS=($(get_list 'package_config.fsx_lustre_client.red_hat.rhel'))

        curl  ${PUBLIC_KEY} -o /tmp/fsx-rpm-public-key.asc
        sudo rpm --import /tmp/fsx-rpm-public-key.asc
        sudo curl ${REPO} -o /etc/yum.repos.d/aws-fsx.repo

        if [[ -n "${kernel_versions[$kernel_base]}" ]]; then
          sudo sed -i "s#8#${kernel_versions[$kernel_base]}#" /etc/yum.repos.d/aws-fsx.repo
        fi

        sudo yum clean all
        sudo yum install -y ${LUSTRE_PKGS[*]}
      fi
    done

    if [[ "$unmatch" == true ]]; then
      log_error "Can't install FSx for Lustre client as kernel version $kernel isn't matching expected versions: (x86_64: 4.18.0-193, -240, -305, -348, -372, -425, -477, -513)!"
    fi
  fi
elif [[ $BASE_OS == "rhel9" ]] || [[ $BASE_OS == "rocky9" ]]; then
  if [[ -z "$(rpm -qa lustre-client)" ]]; then
    kernel=$(uname -r)
    machine=$(uname -m)
    unmatch=true
    log_info "Found kernel version: $kernel running on: $machine"

    declare -A kernel_versions=(
      ["5.14.0-503"]=""
      ["5.14.0-427"]="9.4"
      ["5.14.0-362"]="9.3"
      ["5.14.0-70"]="9.0"
    )

    for kernel_base in "${!kernel_versions[@]}"; do
      if [[ $kernel == *"$kernel_base"*"$machine" ]]; then
        unmatch=false
        PUBLIC_KEY=($(get_string 'package_config.fsx_lustre_client.prerequisites.red_hat.public_key'))
        REPO=($(get_string 'package_config.fsx_lustre_client.prerequisites.red_hat.repo.rhel9'))
        LUSTRE_PKGS=($(get_list 'package_config.fsx_lustre_client.red_hat.rhel'))

        curl ${PUBLIC_KEY} -o /tmp/fsx-rpm-public-key.asc
        sudo rpm --import /tmp/fsx-rpm-public-key.asc
        sudo curl ${REPO} -o /etc/yum.repos.d/aws-fsx.repo

        if [[ -n "${kernel_versions[$kernel_base]}" ]]; then
          sudo sed -i "s#9#${kernel_versions[$kernel_base]}#" /etc/yum.repos.d/aws-fsx.repo
        fi

        sudo yum clean all
        sudo yum install -y ${LUSTRE_PKGS[*]}
      fi
    done

    if [[ "$unmatch" == true ]]; then
      log_error "Can't install FSx for Lustre client as kernel version $kernel isn't matching expected versions: (x86_64: 5.14.0-362, -70)!"
    fi
  fi
elif [[ $BASE_OS =~ ^(ubuntu2204|ubuntu2404)$ ]]; then
  PUBLIC_KEY=($(get_string 'package_config.fsx_lustre_client.prerequisites.debian.public_key'))
  REPO=($(get_string 'package_config.fsx_lustre_client.prerequisites.debian.repo'))
  IFS=$'\n'
  LUSTRE_PKGS=($(get_list 'package_config.fsx_lustre_client.debian.ubuntu'))
  wget -O - ${PUBLIC_KEY} | gpg --dearmor | sudo tee /usr/share/keyrings/fsx-ubuntu-public-key.gpg >/dev/null
  bash -c 'echo "deb [signed-by=/usr/share/keyrings/fsx-ubuntu-public-key.gpg] '"${REPO}"' jammy main" > /etc/apt/sources.list.d/fsxlustreclientrepo.list && apt-get update'

  # Evaluate embedded commands
  EVALUATED_LUSTRE_PKGS=()
  for pkg in "${LUSTRE_PKGS[@]}"; do
    EVALUATED_LUSTRE_PKGS+=("$(eval echo "$pkg")")
  done
  DEBIAN_FRONTEND=noninteractive apt install -y ${EVALUATED_LUSTRE_PKGS[*]}
  unset IFS
fi
# End: Install FSx Lustre Client
