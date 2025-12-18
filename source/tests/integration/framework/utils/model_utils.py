#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Utilities for importing backend models dynamically and data manipulation.

This module provides helper functions for importing backend models from the
lambda functions backend directory using importlib, allowing test files to
access backend models without direct dependencies. It also includes utility
functions for data cleaning and manipulation.
"""

import importlib.util
import os
import sys
from typing import Any


def import_backend_model(model_name: str) -> Any:
    """
    Dynamically import a backend model using importlib.

    This function locates and imports backend models from the lambda functions
    backend directory, handling the sys.path manipulation needed for dependencies.

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
    backend_path = os.path.join(
        source_dir, "idea", "infrastructure", "resources", "lambda_functions", "backend"
    )

    model_file_path = os.path.join(backend_path, "api", "models", f"{model_name}.py")

    if not os.path.exists(model_file_path):
        raise ImportError(f"Backend model file not found: {model_file_path}")

    spec = importlib.util.spec_from_file_location(
        f"api.models.{model_name}", model_file_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create module spec for {model_name}")

    module = importlib.util.module_from_spec(spec)

    # Add backend path to sys.path temporarily for dependencies
    backend_added = False
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
        backend_added = True

    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        raise ImportError(f"Failed to import backend model {model_name}: {str(e)}")
    finally:
        # Clean up sys.path
        if backend_added and backend_path in sys.path:
            sys.path.remove(backend_path)


def get_backend_model_class(model_name: str, class_name: str) -> Any:
    """
    Import a backend model and return a specific class from it.

    Args:
        model_name: Name of the model file (without .py extension)
        class_name: Name of the class to extract from the module

    Returns:
        The requested class from the backend model

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
            f"Class '{class_name}' not found in backend model '{model_name}'"
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
