#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from datamodel.serializers.virtual_desktop_week_schedule_serializer import (
    VirtualDesktopWeekScheduleSerializer,
)


class TestVirtualDesktopWeekScheduleSerializer:

    def setup_method(self):
        self.serializer = VirtualDesktopWeekScheduleSerializer()

    def test_to_ddb_renames_day_keys(self):
        """API format {day: {...}} -> DDB format {day_schedule: {...}}"""
        api_data = {
            "monday": {"schedule_type": "WORKING_HOURS", "day_of_week": "monday"},
            "friday": {"schedule_type": "STOP_ALL_DAY", "day_of_week": "friday"},
        }

        result = self.serializer._customize_to_ddb(api_data)

        assert "monday_schedule" in result
        assert "friday_schedule" in result
        assert result["monday_schedule"]["schedule_type"] == "WORKING_HOURS"
        assert result["friday_schedule"]["schedule_type"] == "STOP_ALL_DAY"
        # Original day keys should not be in result
        assert "monday" not in result
        assert "friday" not in result

    def test_to_ddb_skips_missing_days(self):
        """Only days present in input should appear in output."""
        api_data = {
            "tuesday": {"schedule_type": "NO_SCHEDULE", "day_of_week": "tuesday"},
        }

        result = self.serializer._customize_to_ddb(api_data)

        assert "tuesday_schedule" in result
        assert len(result) == 1

    def test_from_ddb_renames_schedule_keys(self):
        """DDB format {day_schedule: {...}} -> API format {day: {...}}"""
        ddb_data = {
            "tuesday_schedule": {"schedule_type": "WORKING_HOURS", "day_of_week": "tuesday"},
        }

        result = self.serializer._customize_from_ddb(ddb_data)

        assert "tuesday" in result
        assert result["tuesday"]["schedule_type"] == "WORKING_HOURS"
        assert result["tuesday"]["day_of_week"] == "tuesday"

    def test_from_ddb_fills_missing_day_of_week(self):
        """day_of_week should be inferred from the key when missing."""
        ddb_data = {
            "wednesday_schedule": {"schedule_type": "CUSTOM_SCHEDULE"},
        }

        result = self.serializer._customize_from_ddb(ddb_data)

        assert result["wednesday"]["day_of_week"] == "wednesday"

    def test_from_ddb_fixes_stringified_none_day_of_week(self):
        """day_of_week == 'None' (string) should be replaced with actual day."""
        ddb_data = {
            "thursday_schedule": {"schedule_type": "NO_SCHEDULE", "day_of_week": "None"},
        }

        result = self.serializer._customize_from_ddb(ddb_data)

        assert result["thursday"]["day_of_week"] == "thursday"

    def test_from_ddb_skips_none_values(self):
        """Entries with None value should be skipped entirely."""
        ddb_data = {
            "monday_schedule": None,
            "tuesday_schedule": {"schedule_type": "WORKING_HOURS", "day_of_week": "tuesday"},
        }

        result = self.serializer._customize_from_ddb(ddb_data)

        assert "monday" not in result
        assert "tuesday" in result

    def test_from_ddb_does_not_mutate_input(self):
        """Input dict should not be modified."""
        ddb_data = {
            "friday_schedule": {"schedule_type": "STOP_ALL_DAY", "day_of_week": "None"},
        }
        original_inner = ddb_data["friday_schedule"].copy()

        self.serializer._customize_from_ddb(ddb_data)

        assert ddb_data["friday_schedule"] == original_inner

    def test_from_ddb_empty_input(self):
        """Empty input should return empty result."""
        result = self.serializer._customize_from_ddb({})
        assert result == {}

    def test_to_ddb_empty_input(self):
        """Empty input should return empty result."""
        result = self.serializer._customize_to_ddb({})
        assert result == {}
