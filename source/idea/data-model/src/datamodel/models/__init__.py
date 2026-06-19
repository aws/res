#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from datamodel.subdir_finder import install

# Shared models (e.g., error types) live at this directory level and are
# resolved by Python's normal import system. Lambda-specific models live
# in subdirs and are resolved by SubdirFinder. If the same module name
# exists in multiple subdirs, an ImportError is raised to prevent silent
# wrong-class-imported bugs.
install(os.path.dirname(__file__), "datamodel.models.", ["backend", "dcv_session_management"])
