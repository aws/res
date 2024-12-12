#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader


def env_using_file_system_loader(
    search_path: str, auto_escape: bool = False
) -> Environment:
    return Environment(
        loader=FileSystemLoader(searchpath=search_path, followlinks=False),
        autoescape=auto_escape,  # nosec B701
    )


def flatten_jinja_config(
    config_entries: List[Dict[str, Any]], prefix: str, config: Dict[str, Any]
) -> None:
    for key, value in config.items():
        if "." in key or ":" in key:
            raise Exception(f"Invalid key: {key}")
        path_prefix = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            flatten_jinja_config(config_entries, path_prefix, value)
        else:
            config_entries.append({"key": path_prefix, "value": value})
