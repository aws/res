#!/usr/bin/env python3
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Generate serializer classes for each Smithy data model to handle API <-> DDB conversions.
Each serializer provides hooks for custom logic while doing nothing by default.
"""

import os
import sys
import re
from pathlib import Path


def extract_model_info(model_file_path):
    """Extract model class name, fields, and type information from generated model file."""
    with open(model_file_path, 'r') as f:
        content = f.read()

    # Extract class name
    class_match = re.search(r'class (\w+)\(Model\):', content)
    if not class_match:
        return None, [], [], []

    class_name = class_match.group(1)

    # Extract imports to categorize field types
    enum_imports = {}
    model_imports = {}
    import_matches = re.findall(r'from datamodel\.models\.(\w+) import (\w+)', content)
    
    models_dir = model_file_path.parent
    for module_name, class_name_import in import_matches:
        import_file_path = models_dir / f"{module_name}.py"
        if import_file_path.exists():
            with open(import_file_path, 'r') as import_file:
                import_content = import_file.read()
                if 'from enum import Enum' in import_content and f'class {class_name_import}(str, Enum):' in import_content:
                    enum_imports[class_name_import] = module_name
                elif f'class {class_name_import}(Model):' in import_content:
                    model_imports[class_name_import] = module_name

    # Extract openapi_types to understand fields
    openapi_match = re.search(r'self\.openapi_types = \{([^}]+)\}', content, re.DOTALL)
    fields = []
    enum_fields = []
    model_fields = []
    
    if openapi_match:
        types_content = openapi_match.group(1)
        # Handle both simple types and complex types (including List[Type])
        field_matches = re.findall(r"'(\w+)':\s*([^,\n]+)", types_content)
        
        for field_name, field_type in field_matches:
            field_type = field_type.strip()
            fields.append((field_name, field_type))
            
            # Check for enums
            if field_type in enum_imports:
                enum_fields.append((field_name, field_type, enum_imports[field_type]))
            
            # Check for model objects
            elif field_type in model_imports:
                model_fields.append((field_name, field_type, model_imports[field_type]))
            
            # Check for List[ModelType]
            elif field_type.startswith('List[') and field_type.endswith(']'):
                inner_type = field_type[5:-1]  # Extract type from List[Type]
                if inner_type in model_imports:
                    model_fields.append((field_name, field_type, model_imports[inner_type], True))  # True indicates it's a list
                elif inner_type in enum_imports:
                    enum_fields.append((field_name, field_type, enum_imports[inner_type], True))

    return class_name, fields, enum_fields, model_fields

def generate_serializer_class(class_name, fields, enum_fields, model_fields):
    """Generate a serializer class for API <-> DDB conversion with dynamic field handling."""

    field_list = ', '.join([f[0] for f in fields]) if fields else 'No fields detected'

    return f'''"""
Serializer for {class_name} - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: {field_list}
"""

from typing import Dict, Any, Optional
import logging

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils

logger = logging.getLogger(__name__)


class {class_name}Serializer(BaseSerializer):
    """
    Serializer for {class_name} model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for {class_name}.
        
        Args:
            data: Converted data dictionary (enums already converted to strings)
            
        Returns:
            Customized data dictionary
        """
        return data
        
    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for {class_name}.
        
        Args:
            data: Data dictionary to be customized
            
        Returns:
            Customized data dictionary
        """
        return data


# Create singleton instance for easy import
{class_name.lower()}_serializer = {class_name}Serializer()
'''

def create_base_serializer():
    """Create base serializer class with all common serialization logic."""

    content = '''"""
Base serializer implementation for API <-> DDB conversion patterns.

This module provides the core serialization logic that all model-specific
serializers inherit from. Contains all common dynamic serialization behavior.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import importlib
import logging
import re
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
                    module_name = re.sub(r'(?<!^)(?=[A-Z])', '_', expected_type.__name__).lower()
                    serializer_module = importlib.import_module(f'datamodel.serializers.{module_name}_serializer')
                    # Singleton instances use lowercased class name without underscores
                    # e.g. VirtualDesktopSoftwareStackSerializer -> virtualdesktopsoftwarestack_serializer
                    # This differs from the module file name which uses snake_case
                    singleton_name = expected_type.__name__.lower() + '_serializer'
                    serializer_instance = getattr(serializer_module, singleton_name)
                    # Return the processed dictionary, not an object
                    return serializer_instance.from_ddb_dict(value)
                except (ImportError, AttributeError) as e:
                    logger.debug(f"Could not load serializer for {expected_type.__name__}: {e}")
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
'''

    return content

def create_serializers_init():
    """Create __init__.py for serializers package."""

    content = '''"""
Serializers package for API <-> DDB conversions.

This package contains serializer classes for each Smithy model, providing
hooks for custom transformation logic between API data models and DynamoDB
dictionary formats.

Usage:
    from datamodel.serializers.permission_profile_serializer import permission_profile_serializer

    # Convert API model to DDB format
    ddb_data = permission_profile_serializer.to_ddb_dict(api_model)

    # Convert DDB record back to API format
    api_data = permission_profile_serializer.from_ddb_dict(ddb_record)
    api_model = PermissionProfile.from_dict(api_data)
"""

from .base_serializer import BaseSerializer, SerializerUtils

__all__ = [
    'BaseSerializer',
    'SerializerUtils',
]
'''

    return content

def main():
    """Generate serializer classes for all models."""
    if len(sys.argv) > 1:
        models_dir = sys.argv[1]
    else:
        models_dir = "generated/server-stub/api/models"

    if len(sys.argv) > 2:
        serializers_dir = sys.argv[2]
    else:
        serializers_dir = "generated/server-stub/api/serializers"

    # Create serializers directory
    Path(serializers_dir).mkdir(parents=True, exist_ok=True)

    # Create base utilities
    base_serializer_path = Path(serializers_dir) / "base_serializer.py"
    with open(base_serializer_path, 'w') as f:
        f.write(create_base_serializer())
    print(f"Created base serializer utilities: {base_serializer_path}")

    # Create __init__.py
    init_path = Path(serializers_dir) / "__init__.py"
    with open(init_path, 'w') as f:
        f.write(create_serializers_init())
    print(f"Created serializers __init__.py: {init_path}")

    # Generate serializers for each model
    models_path = Path(models_dir)
    if not models_path.exists():
        print(f"Models directory not found: {models_dir}")
        return

    created_serializers = []

    for model_file in models_path.glob("*.py"):
        if model_file.name in ['__init__.py', 'base_model.py']:
            continue

        # Skip enum files (they don't need serializers)
        with open(model_file, 'r') as f:
            content = f.read()
        if 'from enum import Enum' in content or 'class Enum' in content:
            continue

        # Skip request/response content classes (API wrappers, not data models)
        if (model_file.name.endswith('_request_content.py') or
            model_file.name.endswith('_response_content.py') or
            'RequestContent' in model_file.name or
            'ResponseContent' in model_file.name):
            continue

        class_name, fields, enum_fields, model_fields = extract_model_info(model_file)
        if not class_name:
            continue

        serializer_content = generate_serializer_class(class_name, fields, enum_fields, model_fields)
        serializer_file = Path(serializers_dir) / f"{model_file.stem}_serializer.py"

        # Only create if it doesn't exist (don't overwrite custom implementations)
        if not serializer_file.exists():
            with open(serializer_file, 'w') as f:
                f.write(serializer_content)
            created_serializers.append(serializer_file.name)
            print(f"Created serializer: {serializer_file} (enums: {len(enum_fields)}, models: {len(model_fields)})")
        else:
            print(f"Serializer already exists (skipping): {serializer_file}")

    # Update __init__.py to import all created serializers
    if created_serializers:
        update_init_file(init_path, created_serializers, models_path)

def update_init_file(init_path, serializer_files, models_path):
    """Update __init__.py to import all serializers."""

    imports = []
    all_exports = ['BaseSerializer', 'SerializerUtils']

    for serializer_file in serializer_files:
        # Extract class name from filename
        module_name = serializer_file.replace('.py', '')
        class_name = ''.join(word.capitalize() for word in module_name.split('_')[:-1])  # Remove 'serializer' suffix

        if class_name:
            instance_name = f"{class_name.lower()}_serializer"
            imports.append(f"from .{module_name} import {instance_name}")
            all_exports.append(instance_name)

    updated_content = f'''"""
Serializers package for API <-> DDB conversions.

This package contains serializer classes for each Smithy model, providing
hooks for custom transformation logic between API data models and DynamoDB
dictionary formats.

Usage:
    from datamodel.serializers import permission_profile_serializer

    # Convert API model to DDB format
    ddb_data = permission_profile_serializer.to_ddb_dict(api_model)

    # Convert DDB record back to API format
    api_data = permission_profile_serializer.from_ddb_dict(ddb_record)
    api_model = PermissionProfile.from_dict(api_data)
"""

from .base_serializer import BaseSerializer, SerializerUtils

# Auto-generated imports
{chr(10).join(imports)}

__all__ = {all_exports}
'''

    with open(init_path, 'w') as f:
        f.write(updated_content)
    print(f"Updated {init_path} with {len(imports)} serializer imports")

if __name__ == "__main__":
    main()
