#!/usr/bin/env python3
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Script to rewrite imports in generated models and serializers from 'api' namespace to 'datamodel' namespace.

This script processes all Python files in the specified directories and replaces:
- from api import ... → from datamodel import ...
- from api.models.* import ... → from datamodel.models.* import ...
- from api.serializers.* import ... → from datamodel.serializers.* import ...
- import api.* → import datamodel.*
"""

import os
import sys
import re
from typing import List


def rewrite_imports_in_file(file_path: str) -> bool:
    """
    Rewrite imports from 'api' to 'datamodel' namespace in a single file.
    
    Returns:
        True if the file was modified, False otherwise
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Replace 'from api import ...' with 'from datamodel import ...'
        content = re.sub(r'from api import ', 'from datamodel import ', content)
        
        # Replace all 'from api.' imports with 'from datamodel.'
        content = re.sub(r'from api\.', 'from datamodel.', content)
        
        # Replace all 'import api.' imports with 'import datamodel.'
        content = re.sub(r'import api\.', 'import datamodel.', content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def rewrite_imports_in_directory(directory: str) -> List[str]:
    """
    Recursively rewrite imports in all Python files in a directory.
    
    Returns:
        List of file paths that were modified
    """
    modified_files = []
    
    if not os.path.exists(directory):
        print(f"Directory not found: {directory}")
        return modified_files
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                if os.path.isfile(file_path):
                    if rewrite_imports_in_file(file_path):
                        modified_files.append(file_path)
    
    return modified_files


def main():
    """Main function to run the import rewriting."""
    if len(sys.argv) < 2:
        print("Usage: python3 rewrite_api_to_data_model_imports.py <directory1> [directory2] ...")
        sys.exit(1)
    
    directories = sys.argv[1:]
    all_modified_files = []
    
    for directory in directories:
        print(f"Rewriting imports in: {directory}")
        modified_files = rewrite_imports_in_directory(directory)
        all_modified_files.extend(modified_files)
    
    if all_modified_files:
        print(f"\nSuccessfully updated {len(all_modified_files)} files:")
        for file_path in all_modified_files:
            print(f"  - {file_path}")
    else:
        print("No files needed import updates.")


if __name__ == "__main__":
    main()
