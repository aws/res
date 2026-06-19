#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from datamodel.subdir_finder import install

install(os.path.dirname(__file__), "datamodel.serializers.", ["backend", "dcv_session_management"])
