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

# This file merges the already existing existing_environment_file with the res_environment_file 
# and puts everything in /etc/environment.
# It makes sure that the content of the res_environment_file is added at the very end (overwriting any existing variable).
# It also makes sure that the variables are not duplicated.

set -x

while getopts r:o: opt
do
    case "${opt}" in
        r) curr_environment=${OPTARG};;
        o) output_file=${OPTARG};;
    esac
done

existing_environment_file=$(mktemp)

#copy existing environment to a temp file
if [[ -f ${output_file} ]]; then
  cp -f ${output_file} ${existing_environment_file}
else
  echo "" > ${existing_environment_file}
fi

echo "Existing environment file"
cat ${existing_environment_file}

#create an empty environment file to add contents to
echo "" > ${output_file}

#conditionally add contents from existing_environment_file to /etc/environment
while IFS= read -r line; do
    var=$(echo "${line}" | grep "=" | cut -d'=' -f1 )
    if [[ ! -z "${var}" ]]; then
        if ! grep -q "${var}=" <<< "${curr_environment}" ; then
            #add varible declaration if not present in current_environment 
            echo ${line} >> ${output_file}
        fi
    fi
done < ${existing_environment_file}

#add contents from current_environment to /etc/environment
echo "${curr_environment}" >> ${output_file}

#remove temp files
rm -f ${existing_environment_file}
