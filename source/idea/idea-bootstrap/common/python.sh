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
set -x

while getopts o:r:n:s:a:i: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
        a) ALIAS_PREFIX=${OPTARG};;
        i) INSTALL_DIR=${OPTARG};;
        *) echo "Invalid option: -${OPTARG}" >&2; exit 1;;
    esac
done

if [[ -z "$BASE_OS" || -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" || -z "$SCRIPT_DIR" || -z "$ALIAS_PREFIX" || -z "$INSTALL_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

if [[ $BASE_OS =~ ^(amzn2|rhel8|rhel9)$ ]]; then
  /bin/bash "${SCRIPT_DIR}/../common/red_hat/python.sh" -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -a "res" -i "/opt/idea/python"
elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
  /bin/bash "${SCRIPT_DIR}/../common/debian/python.sh" -r $AWS_REGION -n $RES_ENVIRONMENT_NAME -a "res" -i "/opt/idea/python"
else
  log_warning "Base OS not supported."
  exit 1
fi
# End Install Python
