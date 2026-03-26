#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
from res.utils import string_utils


class TestStringUtils:
    """Test class for string_utils module."""

    def test_validate_input_valid(self):
        """Test validate_input with valid input."""
        result = string_utils.validate_input("abc123", r"^[a-z0-9]+$")
        assert result is True

    def test_validate_input_invalid(self):
        """Test validate_input with invalid input."""
        result = string_utils.validate_input("abc-123", r"^[a-z0-9]+$")
        assert result is False

    def test_validate_input_empty_string(self):
        """Test validate_input with empty string."""
        result = string_utils.validate_input("", r"^[a-z0-9]+$")
        assert result is False
