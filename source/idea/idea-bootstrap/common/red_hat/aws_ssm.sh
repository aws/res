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

while getopts o:r:n:s: opt
do
    case "${opt}" in
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
    esac
done

if [[ -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

systemctl status amazon-ssm-agent
if [[ "$?" != "0" ]]; then
  AWS=$(command -v aws)
  machine=$(uname -m)
  aws_ssm_link=$($AWS dynamodb get-item \
                              --region "$AWS_REGION" \
                              --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                              --key '{"key": {"S": "global-settings.package_config.aws_ssm.'$machine'"}}' \
                              --output text \
                              | awk '/VALUE/ {print $2}')
  yum install -y $aws_ssm_link
fi
