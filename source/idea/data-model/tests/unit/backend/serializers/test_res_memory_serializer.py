#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import sys
import unittest
from decimal import Decimal
import pytest

# Import the actual serializer
from datamodel.serializers.res_memory_serializer import ResMemorySerializer


class TestResMemorySerializer:
    """Test cases for ResMemorySerializer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = ResMemorySerializer()

    def test_customize_to_ddb_converts_float_to_decimal(self):
        """Test _customize_to_ddb converts float values to Decimal for DynamoDB compatibility."""
        input_data = {
            "value": 8.5,  # Float value
            "unit": "GB"
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert isinstance(result["value"], Decimal)
        assert result["value"] == Decimal("8.5")
        assert result["unit"] == "GB"

    def test_customize_to_ddb_converts_int_to_decimal(self):
        """Test _customize_to_ddb converts int values to Decimal for DynamoDB compatibility."""
        input_data = {
            "value": 8,  # Integer value
            "unit": "GB"
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert isinstance(result["value"], Decimal)
        assert result["value"] == Decimal("8")
        assert result["unit"] == "GB"

    def test_customize_to_ddb_handles_none_value(self):
        """Test _customize_to_ddb handles None values correctly."""
        input_data = {
            "value": None,
            "unit": "GB"
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["value"] is None
        assert result["unit"] == "GB"

    def test_customize_to_ddb_handles_missing_value(self):
        """Test _customize_to_ddb handles missing value field."""
        input_data = {
            "unit": "GB"
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert "value" not in result or result.get("value") is None
        assert result["unit"] == "GB"

    def test_customize_from_ddb_converts_decimal_to_float(self):
        """Test _customize_from_ddb converts Decimal values back to float for API compatibility."""
        input_data = {
            "value": Decimal("8.5"),  # Decimal value from DynamoDB
            "unit": "GB"
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert isinstance(result["value"], float)
        assert result["value"] == 8.5
        assert result["unit"] == "GB"

    def test_customize_from_ddb_handles_none_value(self):
        """Test _customize_from_ddb handles None values correctly."""
        input_data = {
            "value": None,
            "unit": "GB"
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["value"] is None
        assert result["unit"] == "GB"

    def test_customize_from_ddb_handles_missing_value(self):
        """Test _customize_from_ddb handles missing value field."""
        input_data = {
            "unit": "GB"
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert "value" not in result or result.get("value") is None
        assert result["unit"] == "GB"
