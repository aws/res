#!/bin/bash

######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################

# Engineering Studio on AWS - Installation Script
#
# Usage:
# ./res-admin.sh --help
#
# Environment Variables:
# * IDEA_REVISION - Use to override the default IDEA version.
# * IDEA_DOCKER_REPO - Use to override the default Docker/ECR repository.
# * IDEA_ECR_CREDS_RESET - Set to false, if you handle AWS ECR authentication manually.
# * IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER - Set to "Ec2InstanceMetadata", if you want install IDEA from an EC2 Instance
#                         using Instance Profile credentials from EC2 Instance Metadata.
# * IDEA_ADMIN_ENABLE_CDK_NAG_SCAN - Set to "false", if you want to disable cdk-nag scan. Default: true
# * RES_DEV_MODE - Set to "true" if you are working with IDEA sources

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
IDEA_REVISION=${IDEA_REVISION:-"v3.0.0-pre-alpha-feature"}
IDEA_DOCKER_REPO=${IDEA_DOCKER_REPO:-"public.ecr.aws/i4h1n0f0/idea-administrator"}
IDEA_ECR_CREDS_RESET=${IDEA_ECR_CREDS_RESET:-"true"}
IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER=${IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER:=""}
IDEA_ADMIN_ENABLE_CDK_NAG_SCAN=${IDEA_ADMIN_ENABLE_CDK_NAG_SCAN:-"true"}

DOCUMENTATION_ERROR="https://ide-on-aws.com"
NC="\033[0m" # No Color
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"

verify_command() {
  # shellcheck disable=SC2181
  if [[ "$?" -ne "0" ]]; then
    echo -e "${RED}[MESSAGE]: ${1} \n[HELP]: Refer to ${DOCUMENTATION_ERROR} for troubleshooting.${NC}"
    exit 1
  fi
}

if [[ "${RES_DEV_MODE}" == "true" ]]; then
  if [[ ! -f ${SCRIPT_DIR}/RES_VERSION.txt ]]; then
    echo -e "${RED}res-admin.sh must be executed from IDEA project root directory when using developer mode."
    exit 1
  fi
  if [[ -z "${VIRTUAL_ENV}" ]]; then
    if [[ -d ${SCRIPT_DIR}/venv ]]; then
      source ${SCRIPT_DIR}/venv/bin/activate
    else
      echo -e "${RED}Python Virtual Environment not detected. Install virtual environment to execute res-admin.sh in developer mode."
      exit 1
    fi
  fi
  IDEA_SKIP_WEB_BUILD=${IDEA_SKIP_WEB_BUILD:-'0'}
  TOKENS=$(echo $(printf ",\"%s\"" "${@}"))
  TOKENS=${TOKENS:1}
  if [[ $(uname -s) == "Linux" ]]; then
    ARGS=$(echo "[${TOKENS}]" | base64 -w0)
  else
    ARGS=$(echo "[${TOKENS}]" | base64)
  fi
  CMD="invoke cli.admin --args=${ARGS}"

  IDEA_SKIP_WEB_BUILD=${IDEA_SKIP_WEB_BUILD} \
  IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER=${IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER} \
  IDEA_ADMIN_ENABLE_CDK_NAG_SCAN=${IDEA_ADMIN_ENABLE_CDK_NAG_SCAN} \
  eval $CMD

  exit $?
fi

cd "${SCRIPT_DIR}"

# Check if Docker is installed
DOCKER_BIN=$(command -v docker)
verify_command "Docker not detected. Download and install it from https://docs.docker.com/get-docker/. Read the Docker Subscription Service Agreement first (https://www.docker.com/legal/docker-subscription-service-agreement/)."

# Check if aws cli (https://aws.amazon.com/cli/) is installed
AWSCLI_BIN=$(command -v aws)
verify_command "awscli not detected. Download and install it from https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"

# Create folder hierarchy
MKDIR_BIN=$(command -v mkdir)
${MKDIR_BIN} -p ${HOME}/.idea/clusters
verify_command "Unable to create ${HOME}/.idea/clusters. Verify path and permissions."

# Check if Docker is running
${DOCKER_BIN} info >> /dev/null 2>&1
verify_command "Docker is installed on the system but it does not seems to be running. Start Docker first."

# Reset ECR credentials
if [[ "${IDEA_ECR_CREDS_RESET}" == "true" ]]; then
  # Check if user is connected to internet an can ping ECR repo
  DIG_BIN=$(command -v dig)
  ${DIG_BIN} +tries=1 +time=3 ${IDEA_DOCKER_REPO} >> /dev/null 2>&1
  verify_command "Unable to query ECR. Are you connected to internet?"

  ${DOCKER_BIN} logout public.ecr.aws >> /dev/null 2>&1
  verify_command "Failed to refresh ECR credentials. docker logout public.ecr.aws failed"
fi

# Pull IDEA docker image if needed
${DOCKER_BIN} images | grep "${IDEA_DOCKER_REPO}" | grep -q "${IDEA_REVISION}"
if [[ $? -ne 0 ]]; then
  ${DOCKER_BIN} pull ${IDEA_DOCKER_REPO}:${IDEA_REVISION}
  verify_command "Unable to download IDEA container image. Refer to the error above."
fi

# Launch installer
${DOCKER_BIN} run --rm -it -v "${HOME}/.idea/clusters:/root/.idea/clusters" \
              -e IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER="${IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER}" \
              -e IDEA_ADMIN_ENABLE_CDK_NAG_SCAN="${IDEA_ADMIN_ENABLE_CDK_NAG_SCAN}" \
              -v ~/.aws:/root/.aws "${IDEA_DOCKER_REPO}:${IDEA_REVISION}" \
              idea-admin "${@}"

