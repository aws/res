#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
set -euo pipefail

# Rewrites bare 'dcv_session_management_client' imports to fully qualified
# 'res.clients.dcv_session_management_client' imports in the auto-generated
# client package so it works when installed under the res.clients namespace.

TARGET_DIR="${1:?Usage: $0 <target-dir>}"

echo "Rewriting dcv_session_management_client imports in ${TARGET_DIR}..."

find "$TARGET_DIR" -name "*.py" -exec sed -i '' \
    -e 's/from dcv_session_management_client/from res.clients.dcv_session_management_client/g' \
    -e 's/import dcv_session_management_client/import res.clients.dcv_session_management_client/g' \
    -e 's/getattr(dcv_session_management_client\./getattr(res.clients.dcv_session_management_client./g' \
    {} +

echo "Import rewrite completed."
