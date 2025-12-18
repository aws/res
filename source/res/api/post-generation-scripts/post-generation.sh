#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

GENERATED_DIR="generated/server-stub"

# Inject authentication parameters into controller functions and fix security function names
./post-generation-scripts/inject_auth_parameters.sh "$GENERATED_DIR"

# Update OpenAPI spec file (rename and add security comments)
./post-generation-scripts/update_openapi_spec.sh "$GENERATED_DIR"

# Convert all enum-like Model classes to proper Python string enums
echo "Converting enum-like models to proper string enums..."
python3 ./post-generation-scripts/convert_string_enums.py "$GENERATED_DIR/api/models"

# Patch util.py to properly handle enum deserialization
echo "Patching enum deserialization in util.py..."
python3 ./post-generation-scripts/patch_enum_deserialization.py "$GENERATED_DIR/api/util.py"

# Generate CustomJsonifier for Connexion 3 AsyncApp using separate script
python3 ./post-generation-scripts/generate_jsonifier.py "$GENERATED_DIR"

# Add copyright headers to all Python files
./post-generation-scripts/add_copyright_headers.sh "$GENERATED_DIR"

echo "Customization completed!"
