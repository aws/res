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
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
    esac
done

if [[ -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

mkdir -p /root/bootstrap/gpu_drivers
pushd /root/bootstrap/gpu_drivers

AWS=$(command -v aws)
AMD_S3_BUCKET_URL=$($AWS dynamodb get-item \
                    --region "$AWS_REGION" \
                    --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                    --key '{"key": {"S": "global-settings.gpu_settings.amd.s3_bucket_url"}}' \
                    --output text \
                    | awk '/VALUE/ {print $2}')
DRIVER_BUCKET_REGION=$(curl -s --head $AMD_S3_BUCKET_URL | grep bucket-region | awk '{print $2}' | tr -d '\r\n')
AMD_S3_BUCKET_PATH=$($AWS dynamodb get-item \
                  --region "$AWS_REGION" \
                  --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                  --key '{"key": {"S": "global-settings.gpu_settings.amd.s3_bucket_path"}}' \
                  --output text \
                  | awk '/VALUE/ {print $2}')
$AWS --region ${DRIVER_BUCKET_REGION} s3 cp --quiet --recursive $AMD_S3_BUCKET_PATH .
tar -xf amdgpu-pro-*rhel*.tar.xz
rm -f amdgpu-pro-*.tar.xz
cd amdgpu-pro*
/bin/sh ./amdgpu-pro-install -y --opencl=pal,legacy

popd
