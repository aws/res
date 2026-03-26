#!/usr/bin/env python3
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Script to convert OpenAPI Generator enum-like Model classes to proper Python Enums.
This script analyzes generated model files and converts classes that have enum-like
patterns (class attributes with string values and no other properties) to proper Enum classes.
"""

import os
import re
import ast
import sys
from typing import List, Dict, Tuple, Optional


def is_enum_like_model(file_path: str) -> Tuple[bool, Optional[Dict[str, str]], Optional[str]]:
    """
    Analyze a Python model file to determine if it represents an enum-like class.
    
    Returns:
        Tuple of (is_enum_like, enum_values_dict, class_name)
        - is_enum_like: True if the class should be converted to an enum
        - enum_values_dict: Dictionary of constant_name -> value if it's an enum
        - class_name: Original class name from the source file
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # Check if it inherits from Model and has "allowed enum values" comment
        if 'from datamodel.models.base_model import Model' not in content:
            return False, None, None
        
        if 'allowed enum values' not in content:
            return False, None, None
        
        # Parse the file to extract class constants
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                
                # Look for class-level assignments that are string constants
                enum_values = {}
                has_non_enum_attributes = False
                
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        # Check if it's a simple assignment like CONSTANT = 'value'
                        if (len(item.targets) == 1 and 
                            isinstance(item.targets[0], ast.Name) and
                            isinstance(item.value, ast.Constant) and
                            isinstance(item.value.value, str)):
                            
                            constant_name = item.targets[0].id
                            constant_value = item.value.value
                            
                            # Skip private attributes and common model attributes
                            if (not constant_name.startswith('_') and 
                                constant_name not in ['openapi_types', 'attribute_map']):
                                enum_values[constant_name] = constant_value
                    
                    elif isinstance(item, ast.FunctionDef):
                        # Skip methods like __init__, from_dict
                        continue
                    elif isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant):
                        # Skip docstrings and comments
                        continue
                    elif isinstance(item, ast.Assign) and len(item.targets) == 1:
                        target = item.targets[0]
                        if isinstance(target, ast.Name) and target.id in ['openapi_types', 'attribute_map']:
                            # These are expected model attributes, not enum indicators
                            continue
                        else:
                            # Other assignments might indicate it's not a pure enum
                            has_non_enum_attributes = True
                
                # Consider it an enum if it has string constants and no complex attributes
                if enum_values and not has_non_enum_attributes:
                    return True, enum_values, class_name
        
        return False, None, None
        
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return False, None, None


def generate_enum_class(class_name: str, enum_values: Dict[str, str], description: str = None) -> str:
    """
    Generate a proper Python Enum class from the enum values.
    
    Args:
        class_name: Name of the enum class
        enum_values: Dictionary of constant_name -> value
        description: Optional description for the enum class
    
    Returns:
        String containing the complete enum class definition
    """
    if not description:
        description = f"Enumeration for {class_name}"
    
    lines = [
        "from enum import Enum",
        "",
        "",
        f"class {class_name}(str, Enum):",
        f'    """{description}"""',
        ""
    ]
    
    # Add enum values
    for constant_name, constant_value in enum_values.items():
        lines.append(f"    {constant_name} = '{constant_value}'")
    
    return "\n".join(lines) + "\n"


def extract_class_description(file_path: str) -> Optional[str]:
    """Extract the class description from the original model file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for description patterns in comments or docstrings
        description_patterns = [
            r'"""([^"]+)"""',
            r"'''([^']+)'''",
            r'# Description: (.+)',
            r'description: (.+)'
        ]
        
        for pattern in description_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if desc and not desc.startswith('NOTE: This class is auto generated'):
                    return desc
        
        return None
        
    except Exception:
        return None


def convert_model_to_enum(file_path: str) -> bool:
    """
    Convert a model file to an enum if it matches the enum pattern.
    
    Returns:
        True if the file was converted, False otherwise
    """
    is_enum, enum_values, original_class_name = is_enum_like_model(file_path)
    
    if not is_enum or not enum_values or not original_class_name:
        return False
    
    # Use the original class name from the source file
    class_name = original_class_name
    
    # Extract description
    description = extract_class_description(file_path)
    if not description:
        description = f"Enumeration values for {class_name}"
    
    # Generate the new enum class
    enum_content = generate_enum_class(class_name, enum_values, description)
    
    # Write the new enum file
    try:
        with open(file_path, 'w') as f:
            f.write(enum_content)
        
        print(f"Converted {file_path} to proper Enum class (preserved original class name: {class_name})")
        return True
        
    except Exception as e:
        print(f"Error writing enum file {file_path}: {e}")
        return False


def convert_all_enums_in_directory(models_dir: str) -> List[str]:
    """
    Convert all enum-like models in the given directory to proper Enums.
    
    Returns:
        List of file paths that were converted
    """
    converted_files = []
    
    if not os.path.exists(models_dir):
        print(f"Models directory not found: {models_dir}")
        return converted_files
    
    for file_name in os.listdir(models_dir):
        if file_name.endswith('.py') and not file_name.startswith('__'):
            file_path = os.path.join(models_dir, file_name)
            
            if os.path.isfile(file_path):
                if convert_model_to_enum(file_path):
                    converted_files.append(file_path)
    
    return converted_files


def main():
    """Main function to run the enum conversion."""
    if len(sys.argv) > 1:
        models_dir = sys.argv[1]
    else:
        # Default to the generated models directory
        models_dir = "generated/api/models"
    
    print(f"Converting enum-like models in: {models_dir}")
    converted_files = convert_all_enums_in_directory(models_dir)
    
    if converted_files:
        print(f"\nSuccessfully converted {len(converted_files)} files to proper Enums:")
        for file_path in converted_files:
            print(f"  - {file_path}")
    else:
        print("No enum-like models found to convert.")


if __name__ == "__main__":
    main()
