#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Read modules.json and iterate over each module
modules=$(jq -r '.modules | .[] | .name' ./modules.json)
for module in $modules; do
    echo "Building module: $module"
    go build -buildmode=c-shared -o ./out/${module}.so ./${module}
done
