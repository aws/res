#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Base serializer implementation for API <-> DDB conversion patterns.

This module provides the core serialization logic that all model-specific
serializers inherit from. Contains all common dynamic serialization behavior.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
from enum import Enum

from res.utils import time_utils  # type: ignore

logger = logging.getLogger(__name__)


class BaseSerializer:
    """
    Base serializer class containing all common serialization logic.
    
    All model-specific serializers inherit from this class to get
    dynamic enum and nested object serialization capabilities.
    """
    
    def to_ddb_dict(self, model_instance) -> Dict[str, Any]:
        """
        Convert any model instance to DynamoDB dictionary format.

        Dynamically iterates through all fields, converting:
        - String enums to their string values
        - Smithy model objects by calling to_ddb_dict recursively
        - Lists by processing each item recursively

        Args:
            model_instance: Any Smithy model instance from API

        Returns:
            Dictionary suitable for DynamoDB storage
        """
        # Start with the basic dict conversion
        data = model_instance.to_dict()

        # Dynamically process each field based on its actual type
        for field_name in list(data.keys()):
            actual_value = getattr(model_instance, field_name, None)
            
            if actual_value is None:
                continue
                
            # Handle different field types dynamically
            if isinstance(actual_value, list):
                # Process list items
                converted_list = []
                for item in actual_value:
                    if hasattr(item, 'to_ddb_dict'):
                        # Smithy model object - recursive call
                        converted_list.append(item.to_ddb_dict())
                    elif isinstance(item, Enum) or (hasattr(item, 'value') and hasattr(item.__class__, '__bases__')):
                        # Enum in list - convert to string
                        converted_list.append(item.value if hasattr(item, 'value') else str(item))
                    else:
                        # Primitive value
                        converted_list.append(item)
                data[field_name] = converted_list
                
            elif hasattr(actual_value, 'to_ddb_dict'):
                # Smithy model object - recursive call
                data[field_name] = actual_value.to_ddb_dict()
                
            elif isinstance(actual_value, Enum) or (hasattr(actual_value, 'value') and hasattr(actual_value.__class__, '__bases__')):
                # String enum - convert to string value
                data[field_name] = actual_value.value if hasattr(actual_value, 'value') else str(actual_value)

        # Allow subclasses to add custom transformations
        return self._customize_to_ddb(data)

    def from_ddb_dict(self, ddb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert DynamoDB dictionary to format suitable for model creation.

        Dynamically uses the model's openapi_types to reconstruct:
        - String values back to enums
        - DDB dictionaries back to Smithy model objects (recursively)
        - Lists with recursive processing of each item

        Args:
            ddb_data: Dictionary from DynamoDB

        Returns:
            Dictionary suitable for Model.from_dict()
        """
        data = ddb_data.copy()
        
        # Allow subclasses to add custom transformations BEFORE default logic
        data = self._customize_from_ddb(data)
        
        # Get the model class by name - we can infer it from the serializer class name
        model_class_name = self.__class__.__name__.replace('Serializer', '')
        
        # Import the specific model module (we know it exists from Smithy generation)
        import re
        import importlib
        module_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_class_name).lower()
        
        try:
            # Import the model - should always work for generated models
            model_module = importlib.import_module(f'datamodel.models.{module_name}')
            model_class = getattr(model_module, model_class_name)
            
            # Create a temporary instance to access openapi_types
            temp_instance = model_class()
            openapi_types = temp_instance.openapi_types
            
            # Process each field based on its expected type
            for field_name, expected_type in openapi_types.items():
                if field_name not in data or data[field_name] is None:
                    continue
                    
                field_value = data[field_name]
                
                # Handle List[Type] - extract the inner type
                if hasattr(expected_type, '__origin__') and expected_type.__origin__ is list:
                    inner_type = expected_type.__args__[0]
                    if isinstance(field_value, list):
                        converted_list = []
                        for item in field_value:
                            converted_item = self._convert_ddb_value_to_type(item, inner_type)
                            converted_list.append(converted_item)
                        data[field_name] = converted_list
                
                # Handle single values
                else:
                    converted_value = self._convert_ddb_value_to_type(field_value, expected_type)
                    if converted_value is not None:
                        data[field_name] = converted_value
                        
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not import model {model_class_name}: {e}")
            # Fall back to pass-through behavior
            pass

        return data
        
    def _convert_ddb_value_to_type(self, value, expected_type):
        """
        Convert a single DDB value to the expected type.
        
        Args:
            value: Value from DDB
            expected_type: Expected Python type
            
        Returns:
            Converted value or original value if conversion not needed/possible
        """
        if value is None:
            return None
            
        try:
            # Check if it's an enum type (has Enum in its bases)
            if hasattr(expected_type, '__bases__'):
                for base in expected_type.__bases__:
                    if hasattr(base, '__name__') and 'Enum' in base.__name__:
                        # It's an enum - convert string to enum
                        if isinstance(value, str):
                            return expected_type(value)
                        return value
            
            # Check if it's a model type (has from_ddb_dict method)
            if hasattr(expected_type, 'from_ddb_dict') and isinstance(value, dict):
                # BaseSerializer should never create objects - only return dictionaries
                # Let util.deserialize_model() handle object creation
                try:
                    # Get the serializer for this type and process the dictionary
                    import re
                    import importlib
                    module_name = re.sub(r'(?<!^)(?=[A-Z])', '_', expected_type.__name__).lower()
                    serializer_module = importlib.import_module(f'datamodel.serializers.{module_name}_serializer')
                    serializer_instance = getattr(serializer_module, module_name + '_serializer')
                    # Return the processed dictionary, not an object
                    return serializer_instance.from_ddb_dict(value)
                except (ImportError, AttributeError):
                    # Fallback - return the dictionary as-is
                    return value
            
            # Check if it's a model type with from_dict fallback
            elif hasattr(expected_type, 'from_dict') and isinstance(value, dict):
                # Return the dictionary for util.deserialize_model() to handle
                return value
                
            # For primitive types, return as-is
            return value
            
        except Exception as e:
            logger.warning("Failed to convert value " + str(value) + " to type " + str(expected_type) + ": " + str(e))
            return value

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook for subclasses to add custom API -> DDB transformations.
        
        Args:
            data: Converted data dictionary
            
        Returns:
            Customized data dictionary
        """
        # Default: no customization
        return data
        
    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook for subclasses to add custom DDB -> API transformations.
        
        Args:
            data: Converted data dictionary
            
        Returns:
            Customized data dictionary
        """
        # Default: no customization
        return data


class SerializerUtils:
    """Static utilities for serializer implementations."""

    @staticmethod
    def timestamps_to_iso(data, *timestamp_fields):
        """
        Convert timestamp fields from milliseconds to ISO format strings.

        :param data: Dictionary containing timestamp fields
        :param timestamp_fields: Field names to convert (defaults to 'created_on' and 'updated_on')
        :return: Data with converted timestamps
        """
        # Default fields if none specified
        if not timestamp_fields:
            timestamp_fields = ('created_on', 'updated_on')

        for field in timestamp_fields:
            if data.get(field):
                data[field] = time_utils.ms_to_iso(int(data[field]))

        return data
