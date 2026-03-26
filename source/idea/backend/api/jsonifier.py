#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
from datetime import datetime, date
from datamodel.models.base_model import Model

# Try to import the base jsonifier class if it exists
try:
    from connexion.jsonifier import Jsonifier
    base_jsonifier = Jsonifier
except ImportError:
    # Fallback if no base jsonifier class exists
    base_jsonifier = object

logger = logging.getLogger(__name__)


class CustomJsonifier(base_jsonifier):
    """Custom jsonifier class for Connexion 3 AsyncApp that handles Model objects and Enums with circular reference detection."""
    
    @staticmethod
    def _convert_to_serializable(obj, seen=None, depth=0):
        """
        Recursively convert objects to JSON-serializable format.
        Handles circular references by tracking seen objects.
        """
        if seen is None:
            seen = set()
        
        # Prevent infinite recursion
        if depth > 50:
            return str(obj)
        
        # Handle None
        if obj is None:
            return None
        
        # Handle primitive types
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Handle datetime objects
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        
        # Check for circular references using object id
        obj_id = id(obj)
        if obj_id in seen:
            logger.warning(f"Circular reference detected for object type: {type(obj).__name__}")
            return None
        
        # Handle lists
        if isinstance(obj, list):
            return [CustomJsonifier._convert_to_serializable(item, seen, depth + 1) for item in obj]
        
        # Handle dicts
        if isinstance(obj, dict):
            seen.add(obj_id)
            try:
                return {k: CustomJsonifier._convert_to_serializable(v, seen, depth + 1) for k, v in obj.items()}
            finally:
                seen.discard(obj_id)
        
        # Handle Model objects by converting them to dictionaries
        if isinstance(obj, Model):
            seen.add(obj_id)
            try:
                dikt = {}
                for attr in obj.openapi_types:
                    value = getattr(obj, attr)
                    if value is None:
                        continue  # Skip null values
                    attr_name = obj.attribute_map[attr]
                    dikt[attr_name] = CustomJsonifier._convert_to_serializable(value, seen, depth + 1)
                return dikt
            finally:
                seen.discard(obj_id)
        
        # Handle objects with to_dict method
        if hasattr(obj, 'to_dict') and callable(obj.to_dict):
            seen.add(obj_id)
            try:
                return CustomJsonifier._convert_to_serializable(obj.to_dict(), seen, depth + 1)
            finally:
                seen.discard(obj_id)
        
        # Handle other objects with __dict__
        if hasattr(obj, '__dict__'):
            seen.add(obj_id)
            try:
                return CustomJsonifier._convert_to_serializable(obj.__dict__, seen, depth + 1)
            finally:
                seen.discard(obj_id)
        
        # Fallback: convert to string
        return str(obj)
    
    @staticmethod
    def dumps(obj, **kwargs):
        """JSON dumps method that handles Model objects and Enums with circular reference detection."""
        # Pre-process the object to remove circular references
        serializable_obj = CustomJsonifier._convert_to_serializable(obj)
        return json.dumps(serializable_obj, **kwargs)
    
    @staticmethod
    def loads(s, **kwargs):
        """Standard JSON loads method."""
        return json.loads(s, **kwargs)


# Backward compatibility alias for any code expecting JSONEncoder
JSONEncoder = CustomJsonifier
