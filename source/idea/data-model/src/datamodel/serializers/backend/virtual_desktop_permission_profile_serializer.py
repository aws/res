#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for VirtualDesktopPermissionProfile - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: profile_id, title, description, permissions, created_on, updated_on
"""


from typing import Dict, Any, Optional
import logging
import os
import yaml

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils

logger = logging.getLogger(__name__)

DEFAULT_PROFILE_FIELDS = {"profile_id", "title", "description", "created_on", "updated_on"}


class VirtualDesktopPermissionProfileSerializer(BaseSerializer):
    """
    Serializer for VirtualDesktopPermissionProfile model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def __init__(self):
        self._permission_metadata = self._load_permission_metadata()

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for VirtualDesktopPermissionProfile.

        Args:
            data: Converted data dictionary (enums already converted to strings)

        Returns:
            Customized data dictionary
        """
        for permission in data.get("permissions") or []:
            data[permission["key"]] = (
                permission.get("enabled", False)
            )

        data.pop("permissions", None)
        return data

    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for VirtualDesktopPermissionProfile.

        Args:
            data: Data dictionary to be customized

        Returns:
            Customized data dictionary
        """
        permissions = []
        for key, value in data.items():
            if key not in DEFAULT_PROFILE_FIELDS:
                # This is a permission field - add metadata from config
                metadata = self._permission_metadata.get(key, {"name": key, "description": ""})
                permissions.append(
                    {
                        "key": key,
                        "name": metadata.get("name", key),
                        "description": metadata.get("description", ""),
                        "enabled": bool(value) if value is not None else False,
                    }
                )

        SerializerUtils.timestamps_to_iso(data)
        data["permissions"] = permissions

        return data

    @staticmethod
    def _load_permission_metadata():
        """Load permission metadata from YAML config file."""
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "permission-config.yaml"
        )

        with open(config_path, "r") as f:
            return yaml.safe_load(f)


# Create singleton instance for easy import
virtualdesktoppermissionprofile_serializer = VirtualDesktopPermissionProfileSerializer()
