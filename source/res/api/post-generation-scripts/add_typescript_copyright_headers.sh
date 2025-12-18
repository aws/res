#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Script to add copyright headers to generated TypeScript files
# Usage: ./add_typescript_copyright_headers.sh <generated_directory>

GENERATED_DIR="$1"

if [ -z "$GENERATED_DIR" ]; then
    echo "Error: Generated directory path is required"
    echo "Usage: $0 <generated_directory>"
    exit 1
fi

echo "Adding copyright headers to TypeScript files..."

# Copyright header content
COPYRIGHT_HEADER="/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the \"License\"). You may not use this file except in compliance
 * with the License. A copy of the License is located at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 * OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

"

# Function to add copyright header to a file
add_copyright_header() {
    local file="$1"

    # Check if file already has Amazon copyright header
    if grep -q "Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved." "$file"; then
        echo "  Skipping $file (already has copyright header)"
        return
    fi

    # Create temporary file with copyright header + original content
    {
        echo "$COPYRIGHT_HEADER"
        cat "$file"
    } > "$file.tmp"

    # Replace original file
    mv "$file.tmp" "$file"
    echo "  Added copyright header to $file"
}

# Add copyright header to all TypeScript files in generated directory
find "$GENERATED_DIR" -name "*.ts" -type f | while read -r file; do
    add_copyright_header "$file"
done

echo "Copyright headers added to all TypeScript files!"
