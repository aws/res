#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash
set -ex

docker run -p 8080:8080 -e URL=docs/RES.openapi.yaml --name res-swagger-ui -v "$(pwd)/openapi":/usr/share/nginx/html/docs/ swaggerapi/swagger-ui
