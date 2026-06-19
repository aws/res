#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -e
set -o pipefail

# Variables
X86_64_DIR=$1
ARM64_DIR=$2
OS_ARCHITECTURES=("x86_64" "arm64")

# When S3_BUCKET_NAME is provided, publish only to that bucket in the current region.
# Otherwise, publish to the staging bucket in the current region AND all regional buckets.
if [ -z "$S3_BUCKET_NAME" ]; then
  IFS=',' read -r -a REGIONS <<< "$ONBOARDED_REGIONS"
  # Also publish to the staging bucket in the current region
  STAGING_BUCKET="res-staging-${AWS_DEFAULT_REGION}-${ACCOUNT_ID}"
fi

publish_latest_to_bucket() {
  local bucket=$1
  local region=$2
  local latest_path=$3
  local module_path=$4
  local module_name=$5
  local os_arch=$6

  local bucket_latest_path="s3://$bucket/$latest_path"

  # Remove previous "latest" module
  aws s3 rm "$bucket_latest_path" --region "$region" --endpoint-url "https://s3.$region.amazonaws.com" || exit 1

  # Publish new "latest" module
  aws s3 cp "$module_path" "$bucket_latest_path" --region "$region" --endpoint-url "https://s3.$region.amazonaws.com" || exit 1

  echo "Shared library file for $module_name ($os_arch) published to:"
  echo "$bucket_latest_path"
}

# Iterate over modules in the version file
jq -c '.modules[]' $VERSION_FILE | while read module; do
  MODULE_NAME=$(echo $module | jq -r '.name')

  for OS_ARCH in "${OS_ARCHITECTURES[@]}"; do
    # Determine the build directory based on architecture
    if [ "$OS_ARCH" == "x86_64" ]; then
      BUILD_DIR=$X86_64_DIR
    else
      BUILD_DIR=$ARM64_DIR
    fi

    # Define paths
    LATEST_PATH="host_modules/$MODULE_NAME/latest/$OS_ARCH/$MODULE_NAME.so"
    MODULE_PATH="$BUILD_DIR/out/$OS_ARCH/$MODULE_NAME.so"

    if [ -n "$S3_BUCKET_NAME" ]; then
      # Publish only to the specified bucket
      publish_latest_to_bucket "$S3_BUCKET_NAME" "$AWS_DEFAULT_REGION" "$LATEST_PATH" "$MODULE_PATH" "$MODULE_NAME" "$OS_ARCH"
    else
      # Publish to the staging bucket in the current region
      publish_latest_to_bucket "$STAGING_BUCKET" "$AWS_DEFAULT_REGION" "$LATEST_PATH" "$MODULE_PATH" "$MODULE_NAME" "$OS_ARCH"

      # Publish to all regional buckets
      for REGION in "${REGIONS[@]}"; do
        REGIONAL_BUCKET="$ARTIFACTS_BUCKET_PREFIX_NAME-$REGION"
        publish_latest_to_bucket "$REGIONAL_BUCKET" "$REGION" "$LATEST_PATH" "$MODULE_PATH" "$MODULE_NAME" "$OS_ARCH"
      done
    fi
  done
done
