#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
#
# Copy generated code to the data-model package.
#
# - Models: fully replaced each run
# - Shared models (from spec/smithy/shared/): placed in models/ root
# - Serializers: new ones added, existing preserved, stale removed
# - Base files and utilities: always replaced
#
# Usage: ./copy_to_data_model.sh <lambda-name> <generated-dir>
set -euo pipefail

LAMBDA_NAME="${1:?Usage: $0 <lambda-name> <generated-dir>}"
GENERATED_DIR="${2:?Usage: $0 <lambda-name> <generated-dir>}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_MODEL="${SCRIPT_DIR}/../../../idea/data-model/src/datamodel"
SHARED_SMITHY="${SCRIPT_DIR}/../spec/smithy/shared"
SUBDIR="${LAMBDA_NAME//-/_}"

GEN_MODELS="$GENERATED_DIR/api/models"
GEN_SERIALIZERS="$GENERATED_DIR/api/serializers"
DEST_MODELS="$DATA_MODEL/models"
DEST_SUBDIR="$DEST_MODELS/$SUBDIR"
DEST_SERIALIZERS="$DATA_MODEL/serializers"
DEST_SER_SUBDIR="$DEST_SERIALIZERS/$SUBDIR"

# Build shared model filenames from shared Smithy structure names
shared_models="base_model.py"
for struct in $(grep -h '^structure ' "$SHARED_SMITHY"/*.smithy 2>/dev/null | awk '{print $2}' | tr -d '{'); do
    snake=$(echo "$struct" | sed 's/\([A-Z]\)/_\1/g' | sed 's/^_//' | tr '[:upper:]' '[:lower:]')
    for suffix in "_response_content.py" ".py"; do
        [ -f "$GEN_MODELS/${snake}${suffix}" ] && { shared_models="$shared_models ${snake}${suffix}"; break; }
    done
done

is_shared() { echo "$shared_models" | grep -qw "$1"; }

# --- Models: wipe subdir and replace ---
rm -f "$DEST_SUBDIR"/*.py 2>/dev/null || true
mkdir -p "$DEST_SUBDIR"

for f in "$GEN_MODELS"/*.py; do
    name="$(basename "$f")"
    if is_shared "$name"; then cp "$f" "$DEST_MODELS/"; else cp "$f" "$DEST_SUBDIR/"; fi
done

# Fix imports: shared models use absolute imports
if [ -f "$DEST_SUBDIR/__init__.py" ]; then
    mods=""
    for name in $shared_models; do mods="$mods ${name%.py}"; done
    python3 "$SCRIPT_DIR/rewrite_shared_imports.py" "$DEST_SUBDIR/__init__.py" $mods
fi

# Utilities: always replace, shared at datamodel/ package root
for f in typing_utils.py util.py jsonifier.py; do
    [ -f "$GENERATED_DIR/api/$f" ] && cp "$GENERATED_DIR/api/$f" "$DATA_MODEL/"
done

# --- Serializers: add new, preserve existing, remove stale ---
if [ -d "$GEN_SERIALIZERS" ]; then
    mkdir -p "$DEST_SER_SUBDIR"

    # Base serializer: always replace
    [ -f "$GEN_SERIALIZERS/base_serializer.py" ] && cp "$GEN_SERIALIZERS/base_serializer.py" "$DEST_SERIALIZERS/"

    # New serializers only
    for f in "$GEN_SERIALIZERS"/*.py; do
        name="$(basename "$f")"
        [[ "$name" == "base_serializer.py" ]] && continue
        [ -f "$DEST_SER_SUBDIR/$name" ] || cp "$f" "$DEST_SER_SUBDIR/"
    done

    # Remove stale serializers (model no longer exists)
    for f in "$DEST_SER_SUBDIR"/*.py; do
        [ -f "$f" ] || continue
        name="$(basename "$f")"
        [[ "$name" == "__init__.py" ]] && continue
        model="${name%_serializer.py}.py"
        [ -f "$DEST_SUBDIR/$model" ] || [ -f "$DEST_MODELS/$model" ] || { echo "  Removing stale: $name"; rm -f "$f"; }
    done
fi

echo "Done: ${LAMBDA_NAME} copied to data-model package."
