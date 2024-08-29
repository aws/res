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

# Begin: Disable SE Linux
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
if [[ $BASE_OS =~ ^(amzn2|rhel8|rhel9)$ ]]; then 
  sestatus | grep -q "disabled"
  if [[ "$?" != "0" ]]; then
    # disables selinux for current session
    sestatus 0
    # reboot is required to apply this change permanently. ensure reboot is the last line called from userdata.
    sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config
    set_reboot_required "Disable SE Linux"
  fi
fi
# End: Disable SE Linux
