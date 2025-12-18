#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import yaml
from functools import lru_cache


@lru_cache(maxsize=1)
def load_permission_metadata():
    """Load permission metadata from YAML config file."""
    config_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'config',
        'permission-config.yaml'
    )
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def convert_db_dict_to_api_format(db_dict):
    """
    Convert DynamoDB dict format (flattened permissions) to API format (permissions list).
    
    In DynamoDB, permissions are stored as individual boolean fields.
    In the API, permissions should be a list of Permission objects with name and description.
    """
    # Known profile fields
    profile_fields = {
        'profile_id', 'title', 'description', 'created_on', 'updated_on'
    }
    
    # Load permission metadata
    permission_metadata = load_permission_metadata()
    
    # Extract permissions from remaining fields
    permissions = []
    for key, value in db_dict.items():
        if key not in profile_fields:
            # This is a permission field - add metadata from config
            metadata = permission_metadata.get(key, {'name': key, 'description': ''})
            permissions.append({
                'key': key,
                'name': metadata.get('name', key),
                'description': metadata.get('description', ''),
                'enabled': bool(value) if value is not None else False
            })
    
    # Build the API format dict
    api_dict = {
        'profile_id': db_dict.get('profile_id'),
        'title': db_dict.get('title'),
        'description': db_dict.get('description'),
        'permissions': permissions,
        'created_on': db_dict.get('created_on'),
        'updated_on': db_dict.get('updated_on')
    }
    
    return api_dict
