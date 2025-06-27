#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import sys
from unittest.mock import Mock
from _pytest.monkeypatch import MonkeyPatch

# initialize monkey patch globally
monkeypatch = MonkeyPatch()

# Mock winreg globally
mock_winreg = Mock()
sys.modules['winreg'] = mock_winreg
