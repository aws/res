#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# set container runtime preferring finch
command -v docker &> /dev/null && container_runtime=docker
command -v finch &> /dev/null && container_runtime=finch
if [ -z "${container_runtime}" ]; then
    echo "Couldn't find docker or finch. Please install a container runtime."
    echo "see: https://github.com/runfinch/finch for finch or https://docs.docker.com/engine/install/"
    exit 1
fi

${container_runtime} build -f source/res/host_modules_pipeline/docker/Dockerfile.test -t test_host_modules .
${container_runtime} run --rm=true \
    ${ENV} \
    test_host_modules "$@"
