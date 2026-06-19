#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from unittest.mock import patch
import pytest

from datamodel.serializers.virtual_desktop_session_serializer import (
    VirtualDesktopSessionSerializer,
)


class TestVirtualDesktopSessionSerializer:
    """Test cases for VirtualDesktopSessionSerializer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = VirtualDesktopSessionSerializer()

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_from_ddb_dict_with_valid_schedule_fields(
        self, mock_timestamps_to_iso
    ):
        """Test from_ddb_dict converts schedule fields correctly."""
        mock_timestamps_to_iso.side_effect = lambda x: x

        input_data = {
            "idea_session_id": "session-123",
            "owner": "user1",
            "tuesday_schedule": {
                "schedule_type": "WORKING_HOURS",
                "day_of_week": "tuesday",
            },
            "session_tags": None,
            "session_type": "CONSOLE",
        }

        result = self.serializer.from_ddb_dict(input_data)

        assert "schedule" in result
        tuesday = result["schedule"]["tuesday"]
        assert tuesday["day_of_week"] == "tuesday"
        assert str(tuesday["schedule_type"]) == "ScheduleType.WORKING_HOURS" or tuesday["schedule_type"] == "WORKING_HOURS"

        # Check that individual day schedule fields are removed
        assert "tuesday_schedule" not in result

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_from_ddb_dict_with_non_day_of_week(
        self, mock_timestamps_to_iso
    ):
        """Test from_ddb_dict converts schedule fields correctly when day_of_week is None."""
        mock_timestamps_to_iso.side_effect = lambda x: x

        input_data = {
            "idea_session_id": "session-123",
            "owner": "user1",
            "tuesday_schedule": {"schedule_type": "NO_SCHEDULE", "day_of_week": "None"},
            "session_tags": None,
            "session_type": "CONSOLE",
            "software_stack": {},
        }

        result = self.serializer.from_ddb_dict(input_data)

        assert "schedule" in result
        tuesday = result["schedule"]["tuesday"]
        assert tuesday["day_of_week"] == "tuesday"
        assert str(tuesday["schedule_type"]) == "ScheduleType.NO_SCHEDULE" or tuesday["schedule_type"] == "NO_SCHEDULE"
        assert "tuesday_schedule" not in result

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_from_ddb_dict_with_empty_tags(
        self, mock_timestamps_to_iso
    ):
        """Test from_ddb_dict handles empty session_tags."""
        mock_timestamps_to_iso.side_effect = lambda x: x

        input_data = {
            "idea_session_id": "session-123",
            "session_tags": {},
            "session_type": "CONSOLE",
            "software_stack": {},
        }

        result = self.serializer.from_ddb_dict(input_data)

        assert result["tags"] == []
        assert "session_tags" not in result

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_from_ddb_dict_with_none_tags(
        self, mock_timestamps_to_iso
    ):
        """Test from_ddb_dict handles None session_tags."""
        mock_timestamps_to_iso.side_effect = lambda x: x

        input_data = {
            "idea_session_id": "session-123",
            "session_tags": None,
            "session_type": "CONSOLE",
            "software_stack": {},
        }

        result = self.serializer.from_ddb_dict(input_data)

        assert result["tags"] == []
        assert "session_tags" not in result

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_renames_session_type_to_type(self, mock_timestamps_to_iso):
        """Test _customize_from_ddb renames session_type back to type."""
        mock_timestamps_to_iso.side_effect = lambda x: x

        input_data = {
            "idea_session_id": "session-123",
            "session_type": "CONSOLE",
            "session_tags": None,
            "software_stack": {},
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["type"] == "CONSOLE"
        assert "session_type" not in result

    def test_customize_to_ddb_renames_type_to_session_type(self):
        """Test _customize_to_ddb renames type to session_type."""
        input_data = {
            "idea_session_id": "session-123",
            "type": "CONSOLE",
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["session_type"] == "CONSOLE"
        assert "type" not in result

    def test_customize_to_ddb_flattens_schedule(self):
        """Test to_ddb_dict flattens schedule into day_schedule columns."""
        from datamodel.models.virtual_desktop_session import VirtualDesktopSession
        from datamodel.models.virtual_desktop_week_schedule import VirtualDesktopWeekSchedule
        from datamodel.models.virtual_desktop_schedule import VirtualDesktopSchedule

        session = VirtualDesktopSession(
            idea_session_id="session-123",
            schedule=VirtualDesktopWeekSchedule(
                monday=VirtualDesktopSchedule(schedule_type="WORKING_HOURS", day_of_week="monday"),
                friday=VirtualDesktopSchedule(schedule_type="NO_SCHEDULE", day_of_week="friday"),
            ),
        )

        result = self.serializer.to_ddb_dict(session)

        assert "schedule" not in result
        assert result["monday_schedule"]["schedule_type"] == "WORKING_HOURS"
        assert result["friday_schedule"]["schedule_type"] == "NO_SCHEDULE"

    def test_customize_to_ddb_handles_no_schedule(self):
        """Test _customize_to_ddb handles missing schedule gracefully."""
        input_data = {
            "idea_session_id": "session-123",
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert "schedule" not in result
        # No _schedule keys should be added
        assert not any(k.endswith("_schedule") for k in result)

    def test_customize_to_ddb_handles_empty_schedule(self):
        """Test _customize_to_ddb handles empty schedule dict."""
        input_data = {
            "idea_session_id": "session-123",
            "schedule": {},
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert "schedule" not in result
