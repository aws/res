#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for VirtualDesktopSessionPermission - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: idea_session_id, idea_session_owner, idea_session_name, idea_session_instance_type, idea_session_state, idea_session_base_os, idea_session_hibernation_enabled, idea_session_type, permission_profile, actor_type, actor_name, created_on, idea_session_created_on, updated_on, expiry_date
"""

from typing import Dict, Any, Optional
import logging

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils

logger = logging.getLogger(__name__)


class VirtualDesktopSessionPermissionSerializer(BaseSerializer):
    """
    Serializer for VirtualDesktopSessionPermission model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for VirtualDesktopSessionPermission.

        Args:
            data: Converted data dictionary (enums already converted to strings)

        Returns:
            Customized data dictionary
        """
        data["permission_profile_id"] = (
            data.get("permission_profile") or {}
        ).get("profile_id")

        data.pop(
            "permission_profile", None
        )

        for attribute in ["expiry_date", "idea_session_created_on"]:
            data[attribute] = int(data.get(attribute) or 0)

        return data

    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for VirtualDesktopSessionPermission.

        Args:
            data: Data dictionary to be customized

        Returns:
            Customized data dictionary
        """
        data["permission_profile"] = {
            "profile_id": data.get("permission_profile_id")
        }

        return SerializerUtils.timestamps_to_iso(data, 'created_on', 'updated_on', 'idea_session_created_on', 'expiry_date')


# Create singleton instance for easy import
virtualdesktopsessionpermission_serializer = VirtualDesktopSessionPermissionSerializer()
