#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Script to handle OpenAPI spec file renaming and security section updates
# Usage: ./update_openapi_spec.sh <generated_directory> <lambda_name>

GENERATED_DIR="$1"
LAMBDA_NAME="$2"

if [ -z "$GENERATED_DIR" ] || [ -z "$LAMBDA_NAME" ]; then
    echo "Error: Generated directory path and lambda name are required"
    echo "Usage: $0 <generated_directory> <lambda_name>"
    exit 1
fi

# Map lambda name to openapi spec filename
case "$LAMBDA_NAME" in
    backend)
        SPEC_NAME="RES.openapi.yaml"
        ;;
    dcv-session-management)
        SPEC_NAME="DCVSessionManagement.openapi.yaml"
        ;;
    *)
        echo "Error: Unknown lambda name: $LAMBDA_NAME"
        exit 1
        ;;
esac

echo "Updating OpenAPI spec file..."

# Rename openapi.yaml to the correct spec name
if [ -f "$GENERATED_DIR/api/openapi/openapi.yaml" ]; then
    mv "$GENERATED_DIR/api/openapi/openapi.yaml" "$GENERATED_DIR/api/openapi/$SPEC_NAME"
    echo "Renamed openapi.yaml to $SPEC_NAME"
fi

# Add comment before security section about local development
OPENAPI_FILE="$GENERATED_DIR/api/openapi/$SPEC_NAME"
if [ -f "$OPENAPI_FILE" ]; then
    sed -i '' '/^security:/i\
# Comment out the security section for local development
' "$OPENAPI_FILE"
    echo "Added comment before security section in OpenAPI spec"
fi

echo "OpenAPI spec file update completed!"
