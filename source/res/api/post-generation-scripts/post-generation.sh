#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
set -euo pipefail

# Usage: ./post-generation.sh <lambda-name>
# Examples:
#   ./post-generation.sh backend
#   ./post-generation.sh dcv-session-management

LAMBDA_NAME="${1:?Usage: $0 <lambda-name>}"
GENERATED_DIR="generated/${LAMBDA_NAME}/server-stub"

# Rewrite imports from 'api' to 'datamodel' namespace
echo "Rewriting imports from 'api' to 'datamodel' namespace..."
REWRITE_DIRS="$GENERATED_DIR/api/models $GENERATED_DIR/api/controllers"
if [ -d "$GENERATED_DIR/api/serializers" ]; then
    REWRITE_DIRS="$REWRITE_DIRS $GENERATED_DIR/api/serializers"
fi
if [ -d "$GENERATED_DIR/api/test" ]; then
    REWRITE_DIRS="$REWRITE_DIRS $GENERATED_DIR/api/test"
fi
python3 ./post-generation-scripts/rewrite_api_to_data_model_imports.py $REWRITE_DIRS

# Convert all enum-like Model classes to proper Python string enums
echo "Converting enum-like models to proper string enums..."
python3 ./post-generation-scripts/convert_string_enums.py "$GENERATED_DIR/api/models"

# Patch util.py to properly handle enum deserialization
echo "Patching enum deserialization in util.py..."
python3 ./post-generation-scripts/patch_enum_deserialization.py "$GENERATED_DIR/api/util.py"

# Generate CustomJsonifier for Connexion 3 AsyncApp
python3 ./post-generation-scripts/generate_jsonifier.py "$GENERATED_DIR"

# Inject authentication parameters into controller functions
./post-generation-scripts/inject_auth_parameters.sh "$GENERATED_DIR" "$LAMBDA_NAME"

# Update OpenAPI spec file (rename and add security comments)
./post-generation-scripts/update_openapi_spec.sh "$GENERATED_DIR" "$LAMBDA_NAME"

# Backend-specific steps
if [ "$LAMBDA_NAME" = "backend" ]; then
    # Generate DDB serializer classes for each data model
    echo "Generating DDB serializer classes for data models..."
    python3 ./post-generation-scripts/generate_serializer_hooks.py "$GENERATED_DIR/api/models" "$GENERATED_DIR/api/serializers"

    # Inject DDB serializer methods into generated model classes
    echo "Injecting DDB serializer methods into model classes..."
    python3 ./post-generation-scripts/inject_serializer_hooks.py "$GENERATED_DIR/api/models"
fi

# Add copyright headers to all Python files
./post-generation-scripts/add_copyright_headers.sh "$GENERATED_DIR"

# Copy generated data models and serializers to the data-model package
./post-generation-scripts/copy_to_data_model.sh "$LAMBDA_NAME" "$GENERATED_DIR"

echo "${LAMBDA_NAME} post-generation completed!"
