#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

RED='\033[1;31m'
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'

BUCKET_PREFIX=$(python3 -c "from idea.constants import ARTIFACTS_BUCKET_PREFIX_NAME; print(ARTIFACTS_BUCKET_PREFIX_NAME)")
PIPELINE_STACK_NAME=$(python3 -c "from idea.constants import PIPELINE_STACK_NAME; print(PIPELINE_STACK_NAME)")

function run(){
    echo -e "${GREEN}Setting up s3 buckets across all available regions"
    codeBuildRoleName=$(aws cloudformation describe-stacks --stack-name $PIPELINE_STACK_NAME --output text --query 'Stacks[0].Outputs[?OutputKey==`PublishCodeBuildRole`].OutputValue')
    regions=$(aws account list-regions --region-opt-status-contains ENABLED ENABLED_BY_DEFAULT --query "Regions[*].RegionName")
    resources=""
    for region in $(echo "$regions" | jq -r '.[]')
    do
        bucketName=$BUCKET_PREFIX-$region
        echo -e "${BLUE}Creating $bucketName bucket"
        if [ "$region" == "us-east-1" ]; then
            bucketResults=$(aws s3api create-bucket --bucket $bucketName --region $region)
        else
            bucketResults=$(aws s3api create-bucket --bucket $bucketName --region $region --create-bucket-configuration LocationConstraint=$region)
        fi
        echo -e "${PURPLE}Enabling bucket versioning"
        aws s3api put-bucket-versioning --bucket $bucketName --versioning-configuration Status=Enabled
    done
    echo -e "${CYAN}Attaching role with permission to buckets"
    aws iam put-role-policy --role-name $codeBuildRoleName --policy-name $BUCKET_PREFIX-policy \
        --policy-document "{ \"Statement\":
            [{
                    \"Effect\": \"Allow\",
                    \"Action\": [\"s3:PutObject\", \"s3:getBucketLocation\", \"s3:ListBucket\", \"s3:GetObject\", \"s3:DeleteObject\"],
                    \"Resource\": [\"arn:aws:s3:::$BUCKET_PREFIX-*\"]
                }
            ]}"
}

run
