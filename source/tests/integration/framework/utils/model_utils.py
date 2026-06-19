#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Utilities for importing data models dynamically and data manipulation.

This module provides helper functions for importing data models from the
data-model package using importlib, allowing test files to access data models
without direct dependencies. It also includes utility functions for data
cleaning and manipulation.
"""

import importlib.util
import os
import sys
from typing import Any


def import_backend_model(model_name: str) -> Any:
    """
    Dynamically import a data model using importlib.

    This function locates and imports data models from the data-model package,
    handling the sys.path manipulation needed for dependencies.

    Args:
        model_name: Name of the model file (without .py extension)

    Returns:
        The imported module containing the model classes

    Raises:
        ImportError: If the model file cannot be found or imported

    Example:
        >>> base_model_module = import_backend_model('base_model')
        >>> Model = base_model_module.Model
    """
    current_file = os.path.abspath(__file__)
    # Go up 5 levels: utils -> framework -> integration -> tests -> source
    source_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    )
    data_model_path = os.path.join(source_dir, "idea", "data-model", "src")

    SUBDIRS = ["backend", "dcv_session_management"]

    model_file_path = None
    # Check parent models/ dir first (shared models live here)
    candidate = os.path.join(data_model_path, "datamodel", "models", f"{model_name}.py")
    if os.path.exists(candidate):
        model_file_path = candidate
    else:
        for subdir in SUBDIRS:
            candidate = os.path.join(
                data_model_path, "datamodel", "models", subdir, f"{model_name}.py"
            )
            if os.path.exists(candidate):
                model_file_path = candidate
                break

    if model_file_path is None:
        raise ImportError(
            f"Data model file not found in subdirs {SUBDIRS}: {model_name}"
        )

    spec = importlib.util.spec_from_file_location(
        f"datamodel.models.{model_name}", model_file_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create module spec for {model_name}")

    module = importlib.util.module_from_spec(spec)

    # Add data-model src path to sys.path temporarily for dependencies
    data_model_added = False
    if data_model_path not in sys.path:
        sys.path.insert(0, data_model_path)
        data_model_added = True

    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        raise ImportError(f"Failed to import data model {model_name}: {str(e)}")
    finally:
        # Clean up sys.path
        if data_model_added and data_model_path in sys.path:
            sys.path.remove(data_model_path)


def get_backend_model_class(model_name: str, class_name: str) -> Any:
    """
    Import a data model and return a specific class from it.

    Args:
        model_name: Name of the model file (without .py extension)
        class_name: Name of the class to extract from the module

    Returns:
        The requested class from the data model

    Raises:
        ImportError: If the model file cannot be imported
        AttributeError: If the class is not found in the module

    Example:
        >>> Model = get_backend_model_class('base_model', 'Model')
        >>> VirtualDesktopBaseOS = get_backend_model_class('virtual_desktop_base_os', 'VirtualDesktopBaseOS')
    """
    module = import_backend_model(model_name)

    if not hasattr(module, class_name):
        raise AttributeError(
            f"Class '{class_name}' not found in data model '{model_name}'"
        )

    return getattr(module, class_name)


def remove_none_values(data: Any) -> Any:
    """
    Recursively remove None values from dictionaries and lists.

    This utility function is commonly used when preparing data for API requests
    to avoid schema validation errors where None values are not expected.

    Args:
        data: The data structure to clean (dict, list, or primitive type)

    Returns:
        The cleaned data structure with None values removed

    Example:
        >>> data = {"key1": "value1", "key2": None, "key3": {"nested": None}}
        >>> clean_data = remove_none_values(data)
        >>> # Returns: {"key1": "value1", "key3": {}}
    """
    if isinstance(data, dict):
        return {
            key: remove_none_values(value)
            for key, value in data.items()
            if value is not None
        }
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data if item is not None]
    else:
        return data
