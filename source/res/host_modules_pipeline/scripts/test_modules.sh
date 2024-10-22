#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Read modules.json and iterate over each module
modules=$(jq -r '.modules | .[] | .name' ./modules.json)
for module in $modules; do
    echo "Checking for test files in module: $module"

    # Check if test files exist
    if ls ./${module}/*_test.go 1> /dev/null 2>&1; then
        echo "Running unit test on module: $module"
        go test ./${module}
    else
        echo "No test files found in module: $module, skipping..."
    fi
done
