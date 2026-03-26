#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for VirtualDesktopServer - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: server_id, idea_session_id, idea_session_owner, instance_id, instance_type, private_ip, private_dns_name, public_ip, public_dns_name, availability, unavailability_reason, console_session_count, virtual_session_count, max_concurrent_sessions_per_user, max_virtual_sessions, state, locked, root_volume_size, root_volume_iops, instance_profile_arn, security_groups, subnet_id, key_pair_name, is_idle
"""

from typing import Dict, Any, Optional
import logging

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils

logger = logging.getLogger(__name__)


class VirtualDesktopServerSerializer(BaseSerializer):
    """
    Serializer for VirtualDesktopServer model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for VirtualDesktopServer.
        
        Args:
            data: Converted data dictionary (enums already converted to strings)
            
        Returns:
            Customized data dictionary
        """
        return data
        
    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for VirtualDesktopServer.
        
        Args:
            data: Data dictionary to be customized
            
        Returns:
            Customized data dictionary
        """
        return data


# Create singleton instance for easy import
virtualdesktopserver_serializer = VirtualDesktopServerSerializer()
