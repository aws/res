#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

export AWS_ACCOUNT=$(echo $CODEBUILD_BUILD_ARN | cut -f5 -d ':')
COMMIT_ID=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -b -8)
RELEASE_VERSION=$(echo "$(<RES_VERSION.txt )" | xargs)

# Run lint and type checks here to make the build fail early
tox -e lint,type

# Set the CDK context based on the environment variables
python -c "import os; import json; print(json.dumps(dict(os.environ)))" | tee cdk.context.json

invoke build package
invoke docker.prepare-artifacts

echo Logging in to Amazon ECR...
aws --version
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"

ECR_REPOSITORY_URI=$(aws ecr describe-repositories --region $AWS_REGION --repository-names $ECR_REPOSITORY --output text --query "repositories[0].repositoryUri")

echo Building the Docker image...
docker build --build-arg IMAGE_TAG=$RELEASE_VERSION-$COMMIT_ID -t $ECR_REPOSITORY_URI:$RELEASE_VERSION-$COMMIT_ID deployment/ecr/idea-administrator
docker images
echo Pushing the Docker image...

docker push $ECR_REPOSITORY_URI:$RELEASE_VERSION-$COMMIT_ID

# Synthesize the template
npx cdk synth -c repository_name=$REPOSITORY_NAME -c branch_name=$BRANCH -c deploy=$DEPLOY -c batteries_included=$BATTERIES_INCLUDED -c integration_tests=$INTEGRATION_TESTS -c destroy=$DESTROY -c registry_name=$ECR_REPOSITORY_URI:$RELEASE_VERSION-$COMMIT_ID -c publish_templates=$PUBLISH_TEMPLATES -c file_asset_prefix="releases/$RELEASE_VERSION/" -c ecr_public_repository_name=$ECR_PUBLIC_REPOSITORY_NAME -c use_bi_parameters_from_ssm=$USE_BI_PARAMETERS_FROM_SSM -c destroy_batteries_included=$DESTROY_BATTERIES_INCLUDED -c portal_domain_name=$PORTAL_DOMAIN_NAME
