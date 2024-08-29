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

# Begin: Install EPEL Repo
set -x

while getopts o:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

if [[ ! -f "/etc/yum.repos.d/epel.repo" ]]; then
  case $BASE_OS in
    amzn2)
      rpm -q epel-release
      if [[ "$?" != "0"  ]]; then
        amazon-linux-extras install -y epel
        yum update --security -y
      fi
      ;;
    rhel8)
      yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
      ;;
    rhel9)
      yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
      ;;
    *)
      log_warning "Base OS not supported."
      ;;
  esac
fi
# End: Install EPEL Repo
