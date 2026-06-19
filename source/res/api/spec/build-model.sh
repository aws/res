#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash
set -ex

if ! command -v yq &> /dev/null
then
    echo "Please install yq: https://mikefarah.gitbook.io/yq/"
    echo "   GO111MODULE=on go get github.com/mikefarah/yq/v4; export PATH=\$PATH:~/go/bin"
    exit 1
fi

# Usage: ./build-model.sh [subproject]
# If no subproject specified, builds all.
# Examples:
#   ./build-model.sh              # Build all
#   ./build-model.sh backend      # Build backend only
#   ./build-model.sh dcv-session-management  # Build DCV session management only

SUBPROJECT="${1:-}"

build_subproject() {
    local name="$1"
    local json_path="smithy/${name}/build/smithyprojections/${name}/source/openapi"

    pushd smithy && ../../gradlew ":${name}:build" && popd

    local output_file
    output_file=$(ls "${json_path}"/*.openapi.json 2>/dev/null | head -1)
    if [ -z "$output_file" ]; then
        echo "Error: No .openapi.json file found in ${json_path}" >&2
        exit 1
    fi
    yq eval -P "$output_file" -o yaml > "openapi/$(basename "${output_file}" .json).yaml"
    # Ensure boolean-like enum values (yes/no/true/false) are quoted to prevent
    # YAML 1.1 parsers (e.g., OpenAPI Generator) from interpreting them as booleans.
    yq eval -i '(.. | select(tag == "!!str" and (. == "yes" or . == "no"))) style="double"' "openapi/$(basename "${output_file}" .json).yaml"
}

if [ -z "$SUBPROJECT" ]; then
    build_subproject "backend"
    build_subproject "dcv-session-management"
else
    build_subproject "$SUBPROJECT"
fi
