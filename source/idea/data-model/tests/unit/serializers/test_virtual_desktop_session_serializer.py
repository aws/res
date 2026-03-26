#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, Mock
import pytest

# Import the actual serializer
from datamodel.serializers.virtual_desktop_session_serializer import (
    VirtualDesktopSessionSerializer,
)


class TestVirtualDesktopSessionSerializer:
    """Test cases for VirtualDesktopSessionSerializer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = VirtualDesktopSessionSerializer()

    @patch(
        "datamodel.serializers.virtual_desktop_session_serializer.virtualdesktopsoftwarestack_serializer.from_ddb_dict"
    )
    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_with_valid_schedule_fields(
        self, mock_timestamps_to_iso, mock_stack_serializer
    ):
        """Test _customize_from_ddb converts schedule fields correctly."""
        mock_timestamps_to_iso.side_effect = lambda x: x
        mock_stack_serializer.return_value = {}

        input_data = {
            "idea_session_id": "session-123",
            "owner": "user1",
            "tuesday_schedule": {
                "schedule_type": "WORKING_HOURS",
                "day_of_week": "tuesday",
            },
            "session_tags": None,
            "session_type": "CONSOLE",
            "software_stack": {},
        }

        result = self.serializer._customize_from_ddb(input_data)

        # Check schedule is reconstructed
        assert "schedule" in result
        assert result["schedule"]["tuesday"] == {
            "schedule_type": "WORKING_HOURS",
            "day_of_week": "tuesday",
        }

        # Check that individual day schedule fields are removed
        assert "tuesday_schedule" not in result

        # Check timestamps_to_iso was called
        mock_timestamps_to_iso.assert_called_once()

    @patch(
        "datamodel.serializers.virtual_desktop_session_serializer.virtualdesktopsoftwarestack_serializer.from_ddb_dict"
    )
    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_with_non_day_of_week(
        self, mock_timestamps_to_iso, mock_stack_serializer
    ):
        """Test _customize_from_ddb converts schedule fields correctly."""
        mock_timestamps_to_iso.side_effect = lambda x: x
        mock_stack_serializer.return_value = {}

        input_data = {
            "idea_session_id": "session-123",
            "owner": "user1",
            "tuesday_schedule": {"schedule_type": "NO_SCHEDULE", "day_of_week": "None"},
            "session_tags": None,
            "session_type": "CONSOLE",
            "software_stack": {},
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert "schedule" in result
        assert result["schedule"]["tuesday"] == {
            "schedule_type": "NO_SCHEDULE",
            "day_of_week": "tuesday",
        }
        assert "tuesday_schedule" not in result

        # Check timestamps_to_iso was called
        mock_timestamps_to_iso.assert_called_once()

    @patch(
        "datamodel.serializers.virtual_desktop_session_serializer.virtualdesktopsoftwarestack_serializer.from_ddb_dict"
    )
    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_with_empty_tags(
        self, mock_timestamps_to_iso, mock_stack_serializer
    ):
        """Test _customize_from_ddb handles empty session_tags."""
        mock_timestamps_to_iso.side_effect = lambda x: x
        mock_stack_serializer.return_value = {}

        input_data = {
            "idea_session_id": "session-123",
            "session_tags": {},
            "session_type": "CONSOLE",
            "software_stack": {},
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["tags"] == []
        assert "session_tags" not in result

    @patch(
        "datamodel.serializers.virtual_desktop_session_serializer.virtualdesktopsoftwarestack_serializer.from_ddb_dict"
    )
    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_with_none_tags(
        self, mock_timestamps_to_iso, mock_stack_serializer
    ):
        """Test _customize_from_ddb handles None session_tags."""
        mock_timestamps_to_iso.side_effect = lambda x: x
        mock_stack_serializer.return_value = {}

        input_data = {
            "idea_session_id": "session-123",
            "session_tags": None,
            "session_type": "CONSOLE",
            "software_stack": {},
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["tags"] == []
        assert "session_tags" not in result
