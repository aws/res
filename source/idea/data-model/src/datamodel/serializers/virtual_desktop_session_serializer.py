#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for VirtualDesktopSession - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: dcv_session_id, idea_session_id, base_os, name, owner, type, server, created_on, updated_on, state, description, software_stack, project, schedule, connection_count, force, hibernation_enabled, is_launched_by_admin, locked, tags, logins, is_idle, failure_reason
"""

from typing import Dict, Any, Optional
import logging

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils
from res.resources import sessions, schedules
from datamodel.serializers.virtual_desktop_software_stack_serializer import virtualdesktopsoftwarestack_serializer

logger = logging.getLogger(__name__)


class VirtualDesktopSessionSerializer(BaseSerializer):
    """
    Serializer for VirtualDesktopSession model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for VirtualDesktopSession.
        
        Args:
            data: Converted data dictionary (enums already converted to strings)
            
        Returns:
            Customized data dictionary
        """
        return data
        
    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for VirtualDesktopSession.
        
        Args:
            data: Data dictionary to be customized
            
        Returns:
            Customized data dictionary
        """
        schedule_dict = {}

        for day in schedules.DayOfWeek:
            day_schedule_key = f"{day.value}_schedule"
            if day_schedule_key not in data:
                continue
            day_schedule = data[day_schedule_key].copy()
            if day_schedule.get('day_of_week') == 'None':
                day_schedule['day_of_week'] = day.value
                
            schedule_dict[day.value] = day_schedule
            
            data.pop(day_schedule_key)

        data['schedule'] = schedule_dict
        data['tags'] = data.get("session_tags") or []
        data.pop('session_tags')

        data["type"] = data.get("session_type")
        data.pop('session_type')

        data["software_stack"] = virtualdesktopsoftwarestack_serializer.from_ddb_dict(data["software_stack"])

        return SerializerUtils.timestamps_to_iso(data)


# Create singleton instance for easy import
virtualdesktopsession_serializer = VirtualDesktopSessionSerializer()
