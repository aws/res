#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Variables
X86_64_DIR=$1
ARM64_DIR=$2
S3_BUCKET_NAME=${S3_BUCKET_NAME}
OS_ARCHITECTURES=("x86_64" "arm64")
PUBLIC_RELEASE=${PUBLIC_RELEASE}

IFS=',' read -r -a REGIONS <<< "$ONBOARDED_REGIONS"
# Check if PUBLIC_RELEASE is false and S3_BUCKET_NAME is provided
if [ "$PUBLIC_RELEASE" != "true" ] && [ -z "$S3_BUCKET_NAME" ]; then
  echo "S3_BUCKET_NAME must be set when PUBLIC_RELEASE is false"
  exit 1
fi

# Iterate over modules in the version file
jq -c '.modules[]' $VERSION_FILE | while read module; do
  MODULE_NAME=$(echo $module | jq -r '.name')
  VERSION=$(echo $module | jq -r '.version')

  for OS_ARCH in "${OS_ARCHITECTURES[@]}"; do
    # Determine the build directory based on architecture
    if [ "$OS_ARCH" == "x86_64" ]; then
      BUILD_DIR=$X86_64_DIR
    else
      BUILD_DIR=$ARM64_DIR
    fi

    # Define paths
    RELEASE_PATH="host_modules/$MODULE_NAME/$VERSION/$OS_ARCH/$MODULE_NAME.so"
    MODULE_PATH="$BUILD_DIR/out/$OS_ARCH/$MODULE_NAME.so"

    # Check if the version already exists in the S3 bucket
    if [ "$PUBLIC_RELEASE" == "true" ]; then
      for REGION in "${REGIONS[@]}"; do
        REGIONAL_BUCKET="$ARTIFACTS_BUCKET_PREFIX_NAME-$REGION"
        REGIONAL_BUCKET_RELEASE_PATH="s3://$REGIONAL_BUCKET/$RELEASE_PATH"

        # Check if the file already exists
        if aws s3 ls "$REGIONAL_BUCKET_RELEASE_PATH" --region "$REGION" --endpoint-url "https://s3.$REGION.amazonaws.com" >/dev/null 2>&1; then
          echo "Error: Version $VERSION for $MODULE_NAME ($OS_ARCH) already exists in $REGIONAL_BUCKET."
          exit 1
        fi

        # Publish new hosted module
        aws s3 cp "$MODULE_PATH" "$REGIONAL_BUCKET_RELEASE_PATH" --region "$REGION" --endpoint-url "https://s3.$REGION.amazonaws.com"  || exit 1

        echo "Shared library file for $MODULE_NAME ($OS_ARCH) published to:"
        echo "$REGIONAL_BUCKET_RELEASE_PATH"
      done
    else
      S3_BUCKET_RELEASE_PATH="s3://$S3_BUCKET_NAME/$RELEASE_PATH"

      # Check if the file already exists
      if aws s3 ls "$S3_BUCKET_RELEASE_PATH" >/dev/null 2>&1; then
        echo "Error: Version $VERSION for $MODULE_NAME ($OS_ARCH) already exists in $S3_BUCKET_NAME."
        exit 1
      fi

      # Publish new hosted module
      aws s3 cp "$MODULE_PATH" "$S3_BUCKET_RELEASE_PATH" || exit 1

      echo "Shared library file for $MODULE_NAME ($OS_ARCH) published to:"
      echo "$S3_BUCKET_RELEASE_PATH"
    fi
  done
done
