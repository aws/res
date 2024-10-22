#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

COMMIT_ID=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -b -8)
RELEASE_VERSION=$(echo "$(<RES_VERSION.txt )" | xargs)

# Set the CDK context based on the environment variables
python -c "import os; import json; print(json.dumps(dict(os.environ)))" | tee cdk.context.json

if [ "$ECR_REPOSITORY_URI_PARAMETER" != "" ]
then
  ECR_REPOSITORY_URI=$ECR_REPOSITORY_URI_PARAMETER
else
  ECR_REPOSITORY_URI=$(aws ecr-public describe-repositories --region us-east-1 --repository-names "$ECR_REPOSITORY" --output text --query "repositories[0].repositoryUri")
fi

echo Uploading template to buckets
# Synthesize exclusively the install stack
npx cdk synth $INSTALL_STACK_NAME -c publish_templates=$PUBLISH_TEMPLATES -c file_asset_prefix="releases/$RELEASE_VERSION/" -c registry_name=$ECR_REPOSITORY_URI:$RELEASE_VERSION-$COMMIT_ID
ARTIFACT_FOLDER=$([ -z $RELEASE_VERSION ] && echo $COMMIT_ID || echo $RELEASE_VERSION)

invoke package.infra-ami-deps
infra_ami_package="dist/res-infra-dependencies.tar.gz"
package_name="res-infra-dependencies.tar.gz"

IFS=',' read -r -a regions <<< "$ONBOARDED_REGIONS"
for region in "${regions[@]}"
do
    AWS_REGION=$region
    npx cdk-assets publish -p cdk.out/$INSTALL_STACK_NAME.assets.json -v
    # Overrides if there is an existing install template
    aws s3api put-object --bucket "$ARTIFACTS_BUCKET_PREFIX_NAME-$region" --key "releases/$RELEASE_VERSION/$INSTALL_STACK_NAME.template.json" --body ./cdk.out/$INSTALL_STACK_NAME.template.json
    if [[ -f $infra_ami_package ]]; then
      aws s3 cp $infra_ami_package "s3://$ARTIFACTS_BUCKET_PREFIX_NAME-$region/releases/$RELEASE_VERSION/$package_name"
    fi
done

if [ "$ECR_REPOSITORY_URI_PARAMETER" == "" ]
then
  invoke build package
  invoke docker.prepare-artifacts

  echo Logging in to Amazon ECR...
  aws --version
  aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws

  echo Building the Docker image...
  docker build --build-arg IMAGE_TAG=$RELEASE_VERSION-$COMMIT_ID -t $ECR_REPOSITORY_URI:$RELEASE_VERSION-$COMMIT_ID deployment/ecr/idea-administrator
  docker images
  echo Pushing the Docker image...

  docker push $ECR_REPOSITORY_URI:$RELEASE_VERSION-$COMMIT_ID
fi
