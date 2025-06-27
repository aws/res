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

# Install and enable ec2-hibinit-agent

function version { echo "$@" | awk -F'[.-]' '{ printf("%d%03d%03d%03d%03d\n", $1,$2,$3,$4,$5); }'; }

KERNAL_VERSION=$(uname -r | awk -F'.el' '{print $1}')
if [[ $(version $KERNAL_VERSION) -le $(version 4.18.0-305.7.1) ]]; then
    echo "Updating kernal version, current kernal version: ${KERNAL_VERSION}"
    yum update -y kernel-4.18.0-553.47.1.el8_10.x86_64
fi

echo "Installing hibernation agent and enabling hibernation service"
yum -y install ec2-hibinit-agent
systemctl enable hibinit-agent.service