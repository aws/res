#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List

import res.exceptions as exceptions  # type: ignore
from res.utils import logging_utils, table_utils, time_utils  # type: ignore

SOFTWARE_STACK_TABLE_NAME = "vdc.controller.software-stacks"
SOFTWARE_STACK_DB_HASH_KEY = "base_os"
SOFTWARE_STACK_DB_RANGE_KEY = "stack_id"
SOFTWARE_STACK_DB_NAME_KEY = "name"
SOFTWARE_STACK_DB_DESCRIPTION_KEY = "description"
SOFTWARE_STACK_DB_CREATED_ON_KEY = "created_on"
SOFTWARE_STACK_DB_UPDATED_ON_KEY = "updated_on"
SOFTWARE_STACK_DB_AMI_ID_KEY = "ami_id"
SOFTWARE_STACK_DB_ENABLED_KEY = "enabled"
SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY = "min_storage_value"
SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY = "min_storage_unit"
SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY = "min_ram_value"
SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY = "min_ram_unit"
SOFTWARE_STACK_DB_ARCHITECTURE_KEY = "architecture"
SOFTWARE_STACK_DB_GPU_KEY = "gpu"
SOFTWARE_STACK_DB_TENANCY_KEY = "tenancy"
SOFTWARE_STACK_DB_PROJECTS_KEY = "projects"
SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY = "allowed_instance_types"
SOFTWARE_STACK_DB_VERSION_KEY = "version"
BASE_STACK_PREFIX = "ss-base"

BASE_OS = [
    "amazonlinux2",
    "amzn2023",
    "rhel8",
    "rhel9",
    "ubuntu2204",
    "ubuntu2404",
    "windows",
]
ARCHITECTURE = ["x86_64", "arm64"]

logger = logging_utils.get_logger(SOFTWARE_STACK_TABLE_NAME)


def create_software_stack(software_stack: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a software stack
    :param software_stack: software stack to create
    :return: created software stack
    """

    if not software_stack:
        raise Exception("Software Stack required")

    base_os = software_stack.get(SOFTWARE_STACK_DB_HASH_KEY, "")
    stack_id = software_stack.get(SOFTWARE_STACK_DB_RANGE_KEY, "")
    if not base_os or not stack_id:
        raise Exception("base_os and stack_id are required")

    logger.info(
        f"Creating software stack {SOFTWARE_STACK_DB_HASH_KEY}: {base_os}, {SOFTWARE_STACK_DB_RANGE_KEY}: {stack_id}"
    )

    try:
        if get_software_stack(base_os=base_os, stack_id=stack_id):
            raise Exception(
                f"{SOFTWARE_STACK_DB_HASH_KEY}: {base_os}, {SOFTWARE_STACK_DB_RANGE_KEY}: {stack_id} already exists."
            )
    except exceptions.SoftwareStackNotFound:
        pass

    current_time_ms = time_utils.current_time_ms()
    software_stack[SOFTWARE_STACK_DB_CREATED_ON_KEY] = current_time_ms
    software_stack[SOFTWARE_STACK_DB_UPDATED_ON_KEY] = current_time_ms
    software_stack[SOFTWARE_STACK_DB_VERSION_KEY] = (
        software_stack.get(SOFTWARE_STACK_DB_VERSION_KEY) or 1
    )

    created_software_stck = table_utils.create_item(
        table_name=SOFTWARE_STACK_TABLE_NAME, item=software_stack
    )

    logger.info(
        f"Created software stack {SOFTWARE_STACK_DB_HASH_KEY}: {base_os}, {SOFTWARE_STACK_DB_RANGE_KEY}: {stack_id} successfully"
    )

    return created_software_stck


def get_software_stack(base_os: str, stack_id: str) -> Dict[str, Any]:
    """
    Get a software stack
    :param stack_id: software stack id
    :param base_os: software stack base os
    :return: software stack
    """
    if not base_os or not stack_id:
        raise Exception("Stack ID and Base OS required")

    logger.info(
        f"Getting software stack for {SOFTWARE_STACK_DB_HASH_KEY}: {base_os}, {SOFTWARE_STACK_DB_RANGE_KEY}: {stack_id}"
    )

    software_stack = table_utils.get_item(
        SOFTWARE_STACK_TABLE_NAME,
        key={
            SOFTWARE_STACK_DB_HASH_KEY: base_os,
            SOFTWARE_STACK_DB_RANGE_KEY: stack_id,
        },
    )

    if not software_stack:
        raise exceptions.SoftwareStackNotFound(
            f"Software stack not found for {SOFTWARE_STACK_DB_HASH_KEY}: {base_os}, {SOFTWARE_STACK_DB_RANGE_KEY}: {stack_id}"
        )

    return software_stack


def is_software_stacks_table_empty() -> bool:
    """
    Check if software stack DDB is empty
    :return whether software stack DDB is empty
    """
    return table_utils.is_table_empty(SOFTWARE_STACK_TABLE_NAME)


def update_software_stack_allowed_instance_types(
    global_allowed_instance_types: List[str],
) -> None:
    """
    Update all existing software stack's allowed insatnce types when global allowed list is changed
    :param global_allowed_instance_types: new global_allowed_instance_types to be used for updating
    """
    if not global_allowed_instance_types:
        raise Exception("Global allowed instance types list is required")

    software_stacks = table_utils.list_items(SOFTWARE_STACK_TABLE_NAME)
    for software_stack in software_stacks:
        base_os = software_stack.get(SOFTWARE_STACK_DB_HASH_KEY, "")
        stack_id = software_stack.get(SOFTWARE_STACK_DB_RANGE_KEY, "")
        logger.info(
            f"Updating software stack for {SOFTWARE_STACK_DB_HASH_KEY}: {base_os}, {SOFTWARE_STACK_DB_RANGE_KEY}: {stack_id}"
        )

        current_allowed_types = software_stack.get(
            SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY, []
        )
        new_allowed_instance_types = list(
            set(current_allowed_types) & set(global_allowed_instance_types)
        )
        software_stack[SOFTWARE_STACK_DB_ALLOWED_INSTANCE_TYPES_KEY] = (
            new_allowed_instance_types
        )

        table_utils.update_item(
            SOFTWARE_STACK_TABLE_NAME,
            key={
                SOFTWARE_STACK_DB_HASH_KEY: base_os,
                SOFTWARE_STACK_DB_RANGE_KEY: stack_id,
            },
            item=software_stack,
        )
