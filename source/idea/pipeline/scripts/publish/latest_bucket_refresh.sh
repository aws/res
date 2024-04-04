#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

RELEASE_VERSION=$(echo "$(<RES_VERSION.txt )" | xargs)

IFS=',' read -r -a regions <<< "$ONBOARDED_REGIONS"
for region in "${regions[@]}"
do
  AWS_REGION=$region

  SOURCE_BUCKET_PATH="s3://$ARTIFACTS_BUCKET_PREFIX_NAME-$region/releases/$RELEASE_VERSION"
  DESTINATION_BUCKET_PATH="s3://$ARTIFACTS_BUCKET_PREFIX_NAME-$region/releases/latest"

  # Cleanup the existing latest folder and copy the latest release into it
  aws s3 rm $DESTINATION_BUCKET_PATH --recursive
  aws s3 cp $SOURCE_BUCKET_PATH $DESTINATION_BUCKET_PATH --recursive
done
