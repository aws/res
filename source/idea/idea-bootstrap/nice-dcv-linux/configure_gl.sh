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
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

if [[ $BASE_OS =~ ^(amzn2|rhel8|rhel9)$ ]]; then
  /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/red_hat/configure_gl.sh" -o $BASE_OS
elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
  /bin/bash "${SCRIPT_DIR}/../nice-dcv-linux/debian/configure_gl.sh"
else
  log_warning "Base OS not supported."
  exit 1
fi
