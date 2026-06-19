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

logger = logging.getLogger(__name__)


class VirtualDesktopSessionSerializer(BaseSerializer):
    """
    Serializer for VirtualDesktopSession model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add custom API -> DDB transformations for VirtualDesktopSession."""
        
        if 'type' in data:
            data['session_type'] = data.pop('type')
        
        schedule = data.pop('schedule', None)
        if schedule and isinstance(schedule, dict):
            data.update(schedule)
        
        return data
        
    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for VirtualDesktopSession.
        
        Args:
            data: Data dictionary to be customized
            
        Returns:
            Customized data dictionary
        """
        schedule_ddb_data = {}
        for key in list(data.keys()):
            if key.endswith('_schedule'):
                schedule_ddb_data[key] = data.pop(key)
        
        if schedule_ddb_data:
            data['schedule'] = schedule_ddb_data
        else:
            data['schedule'] = {}
        session_tags = data.pop('session_tags', [])
        data['tags'] = [] if not session_tags else session_tags

        if "session_type" in data:
            data["type"] = data.pop("session_type")
        
        return SerializerUtils.timestamps_to_iso(data)


# Create singleton instance for easy import
virtualdesktopsession_serializer = VirtualDesktopSessionSerializer()