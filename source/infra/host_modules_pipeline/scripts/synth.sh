#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

invoke clean.library build.library package.library
invoke clean.datamodel build.datamodel package.datamodel

SYNTH_CMD="npx cdk synth RESHostModulesPipelineStack -c repository_name=$PIPELINE_REPOSITORY_NAME -c branch_name=$PIPELINE_BRANCH_NAME -c publish_modules=$PIPELINE_PUBLISH_MODULES"

if [ "$PIPELINE_PUBLISH_MODULES" = "true" ]; then
    SYNTH_CMD="$SYNTH_CMD -c public_release=$PIPELINE_PUBLIC_RELEASE"
    if [ -n "$PIPELINE_S3_BUCKET_NAME" ]; then
        SYNTH_CMD="$SYNTH_CMD -c s3_bucket_name=$PIPELINE_S3_BUCKET_NAME"
    fi
fi

echo "Executing CDK synthesis command: $SYNTH_CMD"
eval $SYNTH_CMD