#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash
set -e

if ! command -v redoc-cli &> /dev/null
then
    echo "Please install redoc-cli: npm install -g redoc-cli"
    exit
fi
cd openapi
redoc-cli bundle RES.openapi.yaml -o RES.openapi.redoc.html
echo "Generated redoc bundle: spec/openapi/RES.openapi.redoc.html"
