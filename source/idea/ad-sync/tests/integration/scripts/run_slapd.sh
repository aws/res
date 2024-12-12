#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
integ_test_dir="source/idea/ad-sync/tests/integration"
random_string() {
    if [[ $OSTYPE == 'darwin'* ]]; then
        echo $RANDOM | md5 | head -c 10; echo;
    else
        echo $RANDOM | md5sum | head -c 10; echo;
    fi
}

build() {
    # Set Public ECR registry
    PUBLIC_ECR_URL=public.ecr.aws

    # Authenticate with AWS using an IAM profile
    aws ecr-public get-login-password --region us-east-1| ${container_runtime} login --username AWS --password-stdin ${PUBLIC_ECR_URL}

    set -e
    ${container_runtime} build -f $script_dir/../docker/Dockerfile.slapd --build-arg INTEG_TEST_DIR=$integ_test_dir -t slapd .
    set +e
}

run_container() {
    # Make DEBUG=-1 to see output from slapd
    SLAP_DEBUG=0
    # Run slapd with debug level so that it doesn't daemonize
    ${container_runtime} run -d --name=slapd --rm=true --name=${container_name} -p 389:389 slapd slapd -d ${SLAP_DEBUG} -F /etc/ldap/slapd.d
}

run() {
    container_exists=$(${container_runtime} ps -a --format '{{.Names}}' | grep "^$container_name$")
    container_running=$(${container_runtime} ps --format '{{.Names}}' | grep "^$container_name$")

    if [ -n "$container_exists" ]; then
      if [ -n "$container_running" ]; then
        echo "$container_name is running."
      else
        echo "$container_name exists but is not running."
        run_container
      fi
    else
      echo "$container_name does not exist"
      run_container
    fi
}


# set container runtime preferring finch
command -v docker &> /dev/null && container_runtime=docker
command -v finch &> /dev/null && container_runtime=finch
if [ -z "${container_runtime}" ]; then
    echo "Coldn't find docker or finch. Please install a container runtime."
    echo "see: https://github.com/runfinch/finch for finch or https://docs.docker.com/engine/install/"
    exit 1
fi

admin_password=$(random_string)

service_account_name=ServiceAccount
service_account_password=RESPassword1.


echo "service account name: " ${service_account_name}
echo "service account password: " ${service_account_password}

container_name=slapd

build
run


# Set the admin password to a known value
echo -e "${admin_password}\n${admin_password}\n" | ${container_runtime} exec -i ${container_name} slappasswd
export ADMIN_PASSWORD=${admin_password}
echo export ADMIN_PASSWORD=${admin_password}

# allow slapd to start as it is in the background
sleep 5

${container_runtime} exec -i ${container_name} bash -c "service_account_name=${service_account_name} service_account_password=${service_account_password} admin_password=secret /opt/res-adsync/scripts/setup_ou.sh"
