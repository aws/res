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

# Determine Dockerfile based on architecture
if [[ "$(uname -m)" == "aarch64" ]]; then
    output_folder="out/arm64"
else
    output_folder="out/x86_64"
fi

dockerfile="Dockerfile.build"
# Build Docker image
${container_runtime} build ${ENV} -f "source/res/host_modules_pipeline/docker/${dockerfile}" -t host_modules_build .

# Create output folder if it doesn't exist
mkdir -p "${PWD}/${output_folder}"

# Copy built files out
${container_runtime} run \
    --rm=true \
    -v "${PWD}/${output_folder}:/out" host_modules_build \
    /bin/bash -c "cp /opt/host_modules/out/* /out"
