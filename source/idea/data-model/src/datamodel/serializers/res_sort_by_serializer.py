#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for ResSortBy - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: key, order
"""

from typing import Dict, Any, Optional
import logging

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils

logger = logging.getLogger(__name__)


class ResSortBySerializer(BaseSerializer):
    """
    Serializer for ResSortBy model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for ResSortBy.
        
        Args:
            data: Converted data dictionary (enums already converted to strings)
            
        Returns:
            Customized data dictionary
        """
        return data
        
    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for ResSortBy.
        
        Args:
            data: Data dictionary to be customized
            
        Returns:
            Customized data dictionary
        """
        return data


# Create singleton instance for easy import
ressortby_serializer = ResSortBySerializer()
