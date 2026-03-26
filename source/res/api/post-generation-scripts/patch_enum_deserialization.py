#!/usr/bin/env python3
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Script to patch the auto-generated util.py file to properly handle enum deserialization.
This fixes the issue where EnumType.__call__() missing 1 required positional argument: 'value'
"""

import os
import sys
import re


def patch_util_file(util_file_path: str) -> bool:
    """
    Patch the util.py file to add proper enum handling in the _deserialize function.
    
    Returns:
        True if the file was patched successfully, False otherwise
    """
    
    if not os.path.exists(util_file_path):
        print(f"Util file not found: {util_file_path}")
        return False
    
    try:
        with open(util_file_path, 'r') as f:
            content = f.read()
        
        # Check if already patched
        if 'from enum import Enum' in content and 'issubclass(klass, Enum)' in content:
            print("Util file already patched for enum handling")
            return True
        
        # Add enum import after other imports
        import_pattern = r'(from api import typing_utils)'
        import_replacement = r'from datamodel import typing_utils\nfrom enum import Enum'
        
        content = re.sub(import_pattern, import_replacement, content)
        
        # Find the _deserialize function and add enum handling
        deserialize_pattern = r'(def _deserialize\(data, klass\):.*?""".*?""".*?if data is None:.*?return None.*?if klass in \(int, float, str, bool, bytearray\):.*?return _deserialize_primitive\(data, klass\).*?elif klass == object:.*?return _deserialize_object\(data\).*?elif klass == datetime\.date:.*?return deserialize_date\(data\).*?elif klass == datetime\.datetime:.*?return deserialize_datetime\(data\))'
        
        enum_handling = r'\1\n    elif isinstance(klass, type) and issubclass(klass, Enum):\n        return klass(data) if data is not None else None'
        
        content = re.sub(deserialize_pattern, enum_handling, content, flags=re.DOTALL)
        
        # Write the patched content back
        with open(util_file_path, 'w') as f:
            f.write(content)
        
        print(f"Successfully patched {util_file_path} for enum handling")
        return True
        
    except Exception as e:
        print(f"Error patching util file {util_file_path}: {e}")
        return False


def main():
    """Main function to run the util.py enum patching."""
    if len(sys.argv) > 1:
        util_file_path = sys.argv[1]
    else:
        # Default path to the generated util.py
        util_file_path = os.path.join("source", "idea", "infrastructure", "resources", "lambda_functions", "backend", "api", "util.py")
    
    if not os.path.isabs(util_file_path):
        # Make path relative to current working directory
        util_file_path = os.path.join(os.getcwd(), util_file_path)
    
    print(f"Patching enum deserialization in: {util_file_path}")
    
    success = patch_util_file(util_file_path)
    
    if success:
        print("Enum deserialization patch applied successfully!")
    else:
        print("Failed to apply enum deserialization patch.")
        sys.exit(1)


if __name__ == "__main__":
    main()
