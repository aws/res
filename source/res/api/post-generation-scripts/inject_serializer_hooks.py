#!/usr/bin/env python3
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Inject serializer methods into generated model classes for API <-> DDB conversions.
"""

import os
import sys
import re
from pathlib import Path

def inject_serializer_methods(model_file_path, class_name):
    """Inject DDB serializer methods into a model class."""
    
    with open(model_file_path, 'r') as f:
        content = f.read()
    
    # Skip if already injected
    if 'def to_ddb_dict(self):' in content:
        return False
    
    # Add import for serializer
    serializer_module = f"{model_file_path.stem}_serializer"
    serializer_instance = f"{class_name.lower()}_serializer"
    serializer_import = f"from datamodel.serializers.{serializer_module} import {serializer_instance}"
    
    # Find import section and add serializer import
    util_import_match = re.search(r'from datamodel import util', content)
    if util_import_match:
        insertion_point = util_import_match.end()
        content = content[:insertion_point] + f'\n{serializer_import}' + content[insertion_point:]
    else:
        # If no util import found, add after other imports
        import_match = re.search(r'(from .* import .*\n)', content)
        if import_match:
            insertion_point = import_match.end()
            content = content[:insertion_point] + f'{serializer_import}\n' + content[insertion_point:]
    
    # Add custom methods before the existing from_dict method
    custom_methods = f'''

    def to_ddb_dict(self):
        """
        Convert this {class_name} instance to DynamoDB dictionary format.
        
        Uses the {class_name}Serializer to handle API -> DDB transformation.
        Override the serializer methods to customize conversion logic.
        
        Returns:
            Dictionary suitable for DynamoDB storage
        """
        return {serializer_instance}.to_ddb_dict(self)
    
    @classmethod
    def from_ddb_dict(cls, ddb_data):
        """
        Create {class_name} instance from DynamoDB dictionary.
        
        Uses the {class_name}Serializer to handle DDB -> API transformation.
        Override the serializer methods to customize conversion logic.
        
        Args:
            ddb_data: Dictionary from DynamoDB record
            
        Returns:
            {class_name} instance
        """
        api_data = {serializer_instance}.from_ddb_dict(ddb_data)
        return cls.from_dict(api_data)'''
    
    # Find the @classmethod decorator before from_dict
    from_dict_pattern = r'(\s+)(@classmethod\s+def from_dict\(cls, dikt\))'
    match = re.search(from_dict_pattern, content, re.MULTILINE)
    
    if match:
        # Add methods before from_dict, ensuring exactly one blank line
        insertion_point = match.start()
        # Remove any existing whitespace before @classmethod and add exactly what we want
        content = content[:insertion_point].rstrip() + custom_methods + content[insertion_point:]
    else:
        # If from_dict not found, add at end of class
        class_end_pattern = rf'(class {class_name}\(Model\):.*?)(\n\n|\nclass|\Z)'
        match = re.search(class_end_pattern, content, re.DOTALL)
        if match:
            class_content = match.group(1)
            insertion_point = match.start(1) + len(class_content)
            content = content[:insertion_point] + custom_methods + content[insertion_point:]
    
    with open(model_file_path, 'w') as f:
        f.write(content)
    
    return True

def main():
    """Inject DDB serializer hooks into all model files."""
    if len(sys.argv) > 1:
        models_dir = sys.argv[1]
    else:
        models_dir = "generated/server-stub/api/models"
    
    models_path = Path(models_dir)
    if not models_path.exists():
        print(f"Models directory not found: {models_dir}")
        return
    
    injected_count = 0
    
    for model_file in models_path.glob("*.py"):
        if model_file.name in ['__init__.py', 'base_model.py']:
            continue
        
        # Skip enum files (they don't need DDB serializers)
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
        
        # Extract class name
        class_match = re.search(r'class (\w+)\(Model\):', content)
        if not class_match:
            continue
        
        class_name = class_match.group(1)
        
        if inject_serializer_methods(model_file, class_name):
            print(f"Injected DDB serializer methods into {model_file.name} ({class_name})")
            injected_count += 1
        else:
            print(f"DDB serializer methods already present in {model_file.name}")
    
    print(f"Completed injection: {injected_count} models updated")

if __name__ == "__main__":
    main()
