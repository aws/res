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

while getopts o:r:n:g:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

if [[ $BASE_OS =~ ^(amazonlinux2)$ ]]; then
  echo "OS is $BASE_OS, no need for this configuration. NO-OP..."
else
  machine=$(uname -m)
  if [[ $machine == "x86_64" ]]; then
    echo "Detected GPU instance, configuring GL..."
    IDEA_SERVICES_PATH="/opt/idea/.services"
    IDEA_SERVICES_LOGS_PATH="${IDEA_SERVICES_PATH}/logs"
    mkdir -p "${IDEA_SERVICES_LOGS_PATH}"
    DCVGLADMIN=$(which dcvgladmin)

    echo """
echo \"GLADMIN START\" >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
echo \$(date) >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
${DCVGLADMIN} disable >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
${DCVGLADMIN} enable >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
echo \$(date) >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
echo \"GLADMIN END\" >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
""" >> /etc/rc.d/rc.local

    chmod +x /etc/rc.d/rc.local
    systemctl enable rc-local
  fi
fi
