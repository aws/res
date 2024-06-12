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

machine=$(uname -m)
if [[ $machine == "x86_64" ]]; then
  echo "Detected GPU instance, configuring GL..."
  IDEA_SERVICES_PATH="/opt/idea/.services"
  IDEA_SERVICES_LOGS_PATH="${IDEA_SERVICES_PATH}/logs"
  mkdir -p "${IDEA_SERVICES_LOGS_PATH}"
  DCVGLADMIN=$(which dcvgladmin)

  echo """#!/bin/bash
echo \"GLADMIN START\" >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
echo \$(date) >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
${DCVGLADMIN} disable >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
${DCVGLADMIN} enable >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
echo \$(date) >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
echo \"GLADMIN END\" >> ${IDEA_SERVICES_LOGS_PATH}/idea-reboot-do-not-edit-or-delete-idea-gl.log 2>&1
""" > /etc/rc.local
  chmod +x /etc/rc.local

  echo """[Unit]
Description=Local Startup Script
ConditionPathExists=/etc/rc.local

[Service]
Type=forking
ExecStart=/etc/rc.local start
TimeoutSec=0
StandardOutput=tty
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
""" > /etc/systemd/system/rc-local.service
  chmod +x /etc/systemd/system/rc-local.service

  systemctl enable rc-local.service
fi
