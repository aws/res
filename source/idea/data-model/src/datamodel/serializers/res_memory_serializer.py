#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for ResMemory - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: value, unit
"""

from typing import Dict, Any, Optional
import logging
from decimal import Decimal

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils

logger = logging.getLogger(__name__)


class ResMemorySerializer(BaseSerializer):
    """
    Serializer for ResMemory model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for ResMemory.
        
        Convert float values to Decimal for DynamoDB compatibility.
        
        Args:
            data: Converted data dictionary (enums already converted to strings)
            
        Returns:
            Customized data dictionary
        """
        # Convert float values to Decimal for DynamoDB compatibility
        if 'value' in data and data['value'] is not None:
            if isinstance(data['value'], (int, float)):
                data['value'] = Decimal(str(data['value']))
        return data
        
    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for ResMemory.
        
        Convert Decimal values back to float for API compatibility.
        
        Args:
            data: Data dictionary to be customized
            
        Returns:
            Customized data dictionary
        """
        # Convert Decimal values back to float for API compatibility
        if 'value' in data and data['value'] is not None:
            if isinstance(data['value'], Decimal):
                data['value'] = float(data['value'])
        return data


# Create singleton instance for easy import
resmemory_serializer = ResMemorySerializer()
