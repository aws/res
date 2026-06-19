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

while getopts s:e:b: opt
do
  case "${opt}" in
    s) SCRIPT_DIR=${OPTARG};;
    e) ENVIRONMENT_NAME=${OPTARG};;
    b) STAGING_BUCKET=${OPTARG};;
    ?) echo "Invalid option for cluster-manager install.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
BASE_OS=$(get_base_os)

# Begin: Install NFS Utils and dependency items
/bin/bash "${SCRIPT_DIR}/../common/linux/nfs_utils.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
# End: Install NFS Utils and dependency items

# Begin : Install SSSD packages
/bin/bash "${SCRIPT_DIR}/../common/linux/sssd.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
# End: Install SSSD packages

# Begin : Install Putty packages
/bin/bash "${SCRIPT_DIR}/../common/linux/putty.sh" -o $BASE_OS -s "${SCRIPT_DIR}"
# End: Install Putty packages

# Begin : Install Host Modules
/bin/bash "${SCRIPT_DIR}/../common/linux/host_modules.sh" -o $BASE_OS -s "${SCRIPT_DIR}" -e "${ENVIRONMENT_NAME}" -b "${STAGING_BUCKET}"
# End: Install Host Modules
