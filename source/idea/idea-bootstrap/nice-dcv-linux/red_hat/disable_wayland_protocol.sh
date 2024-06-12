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
    esac
done

if [[ -z "$BASE_OS" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

if [[ $BASE_OS =~ ^(rhel9)$ ]]; then
  # disable the wayland protocol https://docs.aws.amazon.com/dcv/latest/adminguide/setting-up-installing-linux-prereq.html
  sed -i 's/^#WaylandEnable=false/WaylandEnable=false/' /etc/gdm/custom.conf
  # restart gdm
  systemctl restart gdm
else
  echo "OS is $BASE_OS, no need to disable the wayland protocol"
fi
