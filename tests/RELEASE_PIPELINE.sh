#!/bin/bash

# Run automated code review, non-inclusive terms scan, verify documentation and more
# Run all tests by default, use comma-separated list to run only specific tests
# RELEASE_PIPELINE.sh cfn_nag,mkdocs,build
# github & mkdocs are disabled by default
if [[ $# -gt 1 ]];
  then
    echo "Specify comma separated (no space) list of tests to run. eg: cfn_nag,build,integtest"
    exit 1
fi

if [[ $# -ne 0 ]];
  then
    IFS=', ' read -r -a TESTS_TO_RUN <<< "$1"
else
  TESTS_TO_RUN=(
  viperlight # Verify we do not have any references to AWS API keys, email addresses ..
  bandit # Python static code analysis
  inclusive # Verify we do not use non-inclusive terms
  build # Build & Install SOCA
  integtests # Run SOCA integration test - require SOCA to be up and running -

  # Following tests are disabled by default. Uncomment them as needed
  # mkdocs # Verify we do not have any broken links on the documentation
  # github # Prepare folder ready to be commit to Github
  )
fi

REGION=$(aws configure list | grep region | awk '{print $2}')
if [[ -z "$REGION" ]]; then
  echo "Unable to determine AWS region. Make sure you have awscli configured"
  exit
else
  echo "Detected region $REGION"
fi

# Parameters to use if building/installing soca
# You can export SOCA_PIPELINE_xxxx environment variable to automatize deployment if you do not want to use the default

# shellcheck disable=SC2199
if [[ "${TESTS_TO_RUN[@]}" =~ "build" ]]; then
  [[ -n "$SOCA_PIPELINE_BUCKET" ]] || { echo "SOCA_PIPELINE_BUCKET variable not set. Please specify it (export SOCA_PIPELINE_BUCKET=xxx)  with the value of a S3 bucket to use"; exit 1; }
  [[ -n "$SOCA_PIPELINE_SSH_KEY" ]] || { echo "SOCA_PIPELINE_SSH_KEY variable not set. Please specify it (export SOCA_PIPELINE_SSH_KEY=xxx) with the value of the SSH key to configure"; exit 1; }
  ADMIN_LDAP_USER=$(openssl rand -hex 12) # generate random ldap username
  ADMIN_LDAP_PASSWORD="pa@sw0rD#123@"# generate random ldap password
  CLUSTER_NAME=$(openssl rand -hex 12 | head -c 5) # generate random cluster id
  VPC_CIDR=${SOCA_PIPELINE_VPC_CIDR:-"140.0.0.0/16"} # VPC cidr to deploy. I pick 140 on purpose as this is an unusual value so you probably won't need to change it as it should not collide with any existing vpcs
  BASE_OS=${SOCA_PIPELINE_BASE_OS:-"amazonlinux2"} # Base OS to use
  DELETE_STACK_AFTER_TEST=${SOCA_PIPELINE_DELETE_STACK:-"false"} # if true, deployed cluster will be automatically removed
fi

CWD=$(dirname "${BASH_SOURCE[0]}")
cd $CWD || exit 2
PYTHON=$(command -v python3)
BASH=$(command -v bash)

# shellcheck disable=SC2199
if [[ "${TESTS_TO_RUN[@]}" =~ "viperlight" ]]; then
  echo "=============  BEGIN VIPERLIGHT CHECKS  ============="
  $BASH  modules/viperlight.sh $CWD || exit 1
  echo "=============  END VIPERLIGHT CHECKS  ============="
fi

# shellcheck disable=SC2199
if [[ "${TESTS_TO_RUN[@]}" =~ "bandit" ]]; then
  echo "=============  BEGIN PYTHON SCANNER  ============="
  $BASH  modules/code_scan.sh $CWD || exit 1
  echo "=============  END PYTHON SCANNER  ============="
fi

# shellcheck disable=SC2199
if [[ "${TESTS_TO_RUN[@]}" =~ "inclusive" ]]; then
  echo "=============  BEGIN INCLUSIVE SCANNER  ============="
  $PYTHON modules/inclusive_scanner.py || exit 1
  echo "=============  END INCLUSIVE SCANNER  ============="
fi

# shellcheck disable=SC2199
if [[ "${TESTS_TO_RUN[@]}" =~ "mkdocs" ]]; then
  echo "=============  BEGIN VERIFY MKDOCS  ============="
  $BASH modules/verify_documentation.sh $CWD || exit 1
  echo "=============  END VERIFY MKDOCS  ============="
fi

# shellcheck disable=SC2199
if [[ "${TESTS_TO_RUN[@]}" =~ "build" ]]; then
  echo "=============  BUILDING & INSTALLING SOCA  ============="
  ../installer/soca_installer.sh -m 1 \
   -r $REGION \
   -b $SOCA_PIPELINE_BUCKET \
   -n $CLUSTER_NAME \
   -lu $ADMIN_LDAP_USER \
   -lp $ADMIN_LDAP_PASSWORD \
   --vpc-cidr $VPC_CIDR \
   -ssh $SOCA_PIPELINE_SSH_KEY \
   --operating-system $BASE_OS || exit 1

   # Retrieve SOCA Endpoint
   GET_SOCA_ENDPOINT=$(aws cloudformation describe-stacks --stack-name soca-$CLUSTER_NAME --query "Stacks[0].Outputs[?OutputKey=='WebUserInterface'].OutputValue" --output text)
   echo "Detected Endpoint: $GET_SOCA_ENDPOINT"
   echo "Created unique auth: $ADMIN_LDAP_USER / $ADMIN_LDAP_PASSWORD"
   echo "=============  END BUILDING & INSTALLING SOCA  ============="
fi

# shellcheck disable=SC2199
if [[ "${TESTS_TO_RUN[@]}" =~ "integtests" ]]; then
  echo "=============  BEGIN SOCA INTEGRATION TESTS  ============="
  $PYTHON modules/soca_integration_tests.py -e $GET_SOCA_ENDPOINT -u $ADMIN_LDAP_USER -p $ADMIN_LDAP_PASSWORD -r $REGION
  echo "=============  END SOCA INTEGRATION TESTS  ============="
  if [[ "$DELETE_STACK_AFTER_TEST" == "true" ]]; then
    echo "Disabling Stack termination protection"
    aws cloudformation update-termination-protection --stack-name soca-$CLUSTER_NAME --no-enable-termination-protection
    echo "Deleting Stack"
    aws cloudformation delete-stack --stack-name soca-$CLUSTER_NAME
  fi
fi

# shellcheck disable=SC2199
if [[ "${TESTS_TO_RUN[@]}" =~ "github" ]]; then
  echo "=============  BUILDING & PREPARING GITHUB RELEASE  ============="
  $PYTHON modules/github_release.py || exit 1
  echo "=============  END BUILDING & PREPARING RELEASE  ============="
fi
