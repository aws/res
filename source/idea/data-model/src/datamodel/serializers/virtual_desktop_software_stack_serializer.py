#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for VirtualDesktopSoftwareStack - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: stack_id, base_os, name, description, created_on, updated_on, ami_id, failure_reason, enabled, min_storage, min_ram, architecture, gpu, placement, version, projects, allowed_instance_types
"""

from typing import Dict, Any, Optional
import logging

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils
# Removed VirtualDesktopTenancy import to avoid circular dependency
# Using string constant instead of enum value

from res.resources import software_stacks, projects

logger = logging.getLogger(__name__)


class VirtualDesktopSoftwareStackSerializer(BaseSerializer):
    """
    Serializer for VirtualDesktopSoftwareStack model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for VirtualDesktopSoftwareStack.

        Args:
            data: Converted data dictionary (enums already converted to strings)

        Returns:
            Customized data dictionary
        """
        data[software_stacks.SOFTWARE_STACK_DB_PROJECTS_KEY] = [project.get("project_id") for project in (data.get("projects") or [])]
        min_storage = data.get("min_storage") or {}
        data[software_stacks.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY] = min_storage.get("value")
        data[software_stacks.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY] = min_storage.get("unit")

        min_ram = data.get("min_ram") or {}
        data[software_stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY] = min_ram.get("value")
        data[software_stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY] = min_ram.get("unit")

        placement = data.get("placement") or {}
        data[software_stacks.SOFTWARE_STACK_DB_HOST_ID_KEY] = placement.get("host_id")
        data[software_stacks.SOFTWARE_STACK_DB_HOST_RESOURCE_GROUP_ARN_KEY] = placement.get("host_resource_group_arn")
        data[software_stacks.SOFTWARE_STACK_DB_TENANCY_KEY] = placement.get("tenancy", "default")
        data[software_stacks.SOFTWARE_STACK_DB_AFFINITY_KEY] = placement.get("affinity")

        data.pop('min_storage', None)
        data.pop('min_ram', None)
        data.pop('placement', None)

        return data

    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for VirtualDesktopSoftwareStack.

        Args:
            data: Data dictionary to be customized

        Returns:
            Customized data dictionary
        """

        data["min_ram"] = {
            "value": data.get("min_ram_value"),
            "unit": data.get("min_ram_unit"),
        }
        data["min_storage"] = {
            "value": data.get("min_storage_value"),
            "unit": data.get("min_storage_unit"),
        }
        data["placement"] = {
            "host_id": data.get("host_id"),
            "host_resource_group_arn": data.get("host_resource_group_arn"),
            "tenancy": data.get("tenancy"),
            "affinity": data.get("affinity"),
        }

        return SerializerUtils.timestamps_to_iso(data)


# Create singleton instance for easy import
virtualdesktopsoftwarestack_serializer = VirtualDesktopSoftwareStackSerializer()
