#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Script to handle OpenAPI spec file renaming and security section updates
# Usage: ./update_openapi_spec.sh <generated_directory>

GENERATED_DIR="$1"

if [ -z "$GENERATED_DIR" ]; then
    echo "Error: Generated directory path is required"
    echo "Usage: $0 <generated_directory>"
    exit 1
fi

echo "Updating OpenAPI spec file..."

# Rename openapi.yaml to RES.openapi.yaml if it exists
if [ -f "$GENERATED_DIR/api/openapi/openapi.yaml" ]; then
    mv "$GENERATED_DIR/api/openapi/openapi.yaml" "$GENERATED_DIR/api/openapi/RES.openapi.yaml"
    echo "Renamed openapi.yaml to RES.openapi.yaml"
fi

# Add comment before security section about local development
OPENAPI_FILE="$GENERATED_DIR/api/openapi/RES.openapi.yaml"
if [ -f "$OPENAPI_FILE" ]; then
    sed -i '' '/^security:/i\
# Comment out the security section for local development
' "$OPENAPI_FILE"
    echo "Added comment before security section in OpenAPI spec"
fi

echo "OpenAPI spec file update completed!"
