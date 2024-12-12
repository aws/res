#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Variables
X86_64_DIR=$1
ARM64_DIR=$2
OS_ARCHITECTURES=("x86_64" "arm64")

IFS=',' read -r -a REGIONS <<< "$ONBOARDED_REGIONS"

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

    # Publish to "latest"
    for REGION in "${REGIONS[@]}"; do
      REGIONAL_BUCKET="$ARTIFACTS_BUCKET_PREFIX_NAME-$REGION"
      REGIONAL_BUCKET_LATEST_PATH="s3://$REGIONAL_BUCKET/$LATEST_PATH"

      # Remove previous "latest" module
      aws s3 rm "$REGIONAL_BUCKET_LATEST_PATH" --region "$REGION" --endpoint-url "https://s3.$REGION.amazonaws.com" || exit 1

      # Publish new "latest" module
      aws s3 cp "$MODULE_PATH" "$REGIONAL_BUCKET_LATEST_PATH" --region "$REGION" --endpoint-url "https://s3.$REGION.amazonaws.com" || exit 1

      echo "Shared library file for $MODULE_NAME ($OS_ARCH) published to:"
      echo "$REGIONAL_BUCKET_LATEST_PATH"
    done
  done
done
