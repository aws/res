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
pushd smithy && ../../gradlew build && popd
GENERATED_JSON_PATH="smithy/build/smithyprojections/smithy/source/openapi/RES.openapi.json"
# Convert json into yaml
yq eval -P $GENERATED_JSON_PATH -o yaml > openapi/RES.openapi.yaml
