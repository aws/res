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


class TestValidateActorName:
    """Tests for validate_actor_name."""

    @pytest.mark.parametrize(
        "name",
        [
            "alice",
            "bob.smith",
            "first-last",
            "under_score",
            "Mix.Of-All_3.chars",
        ],
    )
    def test_valid_actor_names(self, name):
        string_utils.validate_actor_name(name)  # should not raise

    @pytest.mark.parametrize(
        "name",
        [
            "",
            " ",
            "user name",
            "user;rm -rf /",
            "$(whoami)",
            "`id`",
            'user"quote',
            "user\ninjection",
            "user\x00null",
            "alice\n",
        ],
    )
    def test_invalid_actor_names(self, name):
        with pytest.raises(ValueError):
            string_utils.validate_actor_name(name)

    def test_none_actor_name(self):
        with pytest.raises(ValueError):
            string_utils.validate_actor_name(None)
