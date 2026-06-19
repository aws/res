#!/bin/bash

# Script to add copyright headers to generated Python files
# Usage: ./add_copyright_headers.sh <generated_directory>

GENERATED_DIR="$1"

if [ -z "$GENERATED_DIR" ]; then
    echo "Error: Generated directory path is required"
    echo "Usage: $0 <generated_directory>"
    exit 1
fi

echo "Adding copyright headers to Python files..."

# Add copyright header to all Python files in generated directory
# Only add 'from __future__ import annotations' if the file doesn't already have it
find "$GENERATED_DIR" -name "*.py" | while read -r file; do
    if grep -q 'from __future__ import annotations' "$file"; then
        sed -i '' '1i\
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.\
#  SPDX-License-Identifier: Apache-2.0\

' "$file"
    else
        sed -i '' '1i\
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.\
#  SPDX-License-Identifier: Apache-2.0\
from __future__ import annotations\

' "$file"
    fi
done

# Handle empty __init__.py files separately
find "$GENERATED_DIR" -name "__init__.py" -empty -exec sh -c 'echo "#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
" > "$1"' _ {} \;

echo "Copyright headers added to all Python files!"
