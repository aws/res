#!/usr/bin/env python3
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Rewrite relative imports to absolute imports for shared models in __init__.py."""

import sys
from pathlib import Path

init_file = Path(sys.argv[1])
shared_modules = sys.argv[2:]

text = init_file.read_text()
for mod in shared_modules:
    text = text.replace(f"from .{mod} import", f"from datamodel.models.{mod} import")
init_file.write_text(text)
