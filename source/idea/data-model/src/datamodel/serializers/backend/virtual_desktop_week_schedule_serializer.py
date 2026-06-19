#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for VirtualDesktopWeekSchedule - handles conversion between API model and DDB dict.

API format:  {"monday": {"schedule_type": "...", ...}, "tuesday": {...}, ...}
DDB format:  {"monday_schedule": {"schedule_type": "...", ...}, "tuesday_schedule": {...}, ...}
"""

from typing import Dict, Any
import json
import logging

from datamodel.serializers.base_serializer import BaseSerializer

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

logger = logging.getLogger(__name__)


class VirtualDesktopWeekScheduleSerializer(BaseSerializer):

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert API schedule format to DDB column format.

        {"monday": {...}, ...} -> {"monday_schedule": {...}, ...}
        """
        result = {}
        for day in DAYS_OF_WEEK:
            if day in data:
                result[f"{day}_schedule"] = json.loads(json.dumps(data[day]))
        return result

    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DDB column format to API schedule format.

        {"monday_schedule": {...}, ...} -> {"monday": {...}, ...}
        """
        result = {}
        for day in DAYS_OF_WEEK:
            key = f"{day}_schedule"
            if key in data and data[key] is not None:
                day_schedule = data[key].copy()
                if not day_schedule.get("day_of_week") or day_schedule["day_of_week"] == "None":
                    day_schedule["day_of_week"] = day
                result[day] = day_schedule
        return result


# Create singleton instance for easy import
virtualdesktopweekschedule_serializer = VirtualDesktopWeekScheduleSerializer()
