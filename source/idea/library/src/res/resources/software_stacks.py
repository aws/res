#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Optional, Tuple

import res.exceptions as exceptions  # type: ignore
from res.resources import cluster_settings, projects  # type: ignore
from res.utils import (  # type: ignore
    ec2_utils,
    logging_utils,
    memory_utils,
    table_utils,
    time_utils,
)
from res.utils.table_utils import FilterOperator

# Table and key definitions
SOFTWARE_STACK_TABLE_NAME = "vdc.controller.software-stacks"
SOFTWARE_STACK_DB_HASH_KEY = "base_os"
SOFTWARE_STACK_DB_RANGE_KEY = "stack_id"

# Field key definitions
SOFTWARE_STACK_DB_BASE_OS_KEY = "base_os"
SOFTWARE_STACK_DB_STACK_ID_KEY = "stack_id"
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

# Placement-related keys
SOFTWARE_STACK_DB_AFFINITY_KEY = "affinity"
SOFTWARE_STACK_DB_HOST_ID_KEY = "host_id"
SOFTWARE_STACK_DB_HOST_RESOURCE_GROUP_ARN_KEY = "host_resource_group_arn"

# Other constants
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

    created_software_stack = table_utils.create_item(
        table_name=SOFTWARE_STACK_TABLE_NAME,
        item=software_stack,
        attribute_names_to_check=[SOFTWARE_STACK_DB_RANGE_KEY],
    )

    logger.info(
        f"Created software stack {SOFTWARE_STACK_DB_HASH_KEY}: {base_os}, {SOFTWARE_STACK_DB_RANGE_KEY}: {stack_id} successfully"
    )

    return created_software_stack


def get_software_stack_by_name(software_stack_name: str):

    scan_filter = {
        "name": {
            "AttributeValueList": [software_stack_name],
            "ComparisonOperator": "EQ",
        }
    }

    items = table_utils.list_items(SOFTWARE_STACK_TABLE_NAME, scan_filter)
    return items[0] if items else None


def get_software_stack(
    base_os: str, stack_id: str, get_project_details: bool = False
) -> Dict[str, Any]:
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

    if (
        get_project_details
        and SOFTWARE_STACK_DB_PROJECTS_KEY in software_stack
        and software_stack[SOFTWARE_STACK_DB_PROJECTS_KEY]
    ):
        software_stack[SOFTWARE_STACK_DB_PROJECTS_KEY] = [
            projects.get_project(project_id)
            for project_id in software_stack[SOFTWARE_STACK_DB_PROJECTS_KEY]
        ]

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


def delete_software_stack(base_os: str, stack_id: str) -> None:
    """
    Delete a software stack
    :param base_os: software stack base os
    :param stack_id: software stack id
    """

    get_software_stack(base_os, stack_id)

    table_utils.delete_item(
        SOFTWARE_STACK_TABLE_NAME,
        key={
            SOFTWARE_STACK_DB_HASH_KEY: base_os,
            SOFTWARE_STACK_DB_RANGE_KEY: stack_id,
        },
    )


def list_software_stacks_paginated(
    filter_expression: Any = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List software stacks with optional filtering and pagination
    :param filter_expression: Optional DynamoDB filter expression
    :param next_token: Pagination token
    :return: tuple of (list of software stacks, next_token)
    """
    logger.info(f"Listing software stacks with filter: {filter_expression}")

    software_stacks, next_token = table_utils.list_items_paginated(
        SOFTWARE_STACK_TABLE_NAME,
        filter_expression=filter_expression,
        next_token=next_token,
    )

    for software_stack in software_stacks:
        if software_stack.get(SOFTWARE_STACK_DB_PROJECTS_KEY, []):
            software_stack[SOFTWARE_STACK_DB_PROJECTS_KEY] = [
                projects.get_project(project_id)
                for project_id in software_stack[SOFTWARE_STACK_DB_PROJECTS_KEY]
            ]

    return software_stacks, next_token


def update_software_stack(software_stack: Dict[str, Any]) -> Dict[str, Any]:
    base_os = software_stack[SOFTWARE_STACK_DB_HASH_KEY]
    stack_id = software_stack[SOFTWARE_STACK_DB_RANGE_KEY]
    existing_software_stack = get_software_stack(base_os, stack_id)

    logger.info(
        f"Updating software stack {SOFTWARE_STACK_DB_HASH_KEY}: {base_os}, {SOFTWARE_STACK_DB_RANGE_KEY}: {stack_id}"
    )

    current_time_ms = time_utils.current_time_ms()
    software_stack[SOFTWARE_STACK_DB_UPDATED_ON_KEY] = current_time_ms
    software_stack.pop(SOFTWARE_STACK_DB_CREATED_ON_KEY, None)

    software_stack[SOFTWARE_STACK_DB_VERSION_KEY] = (
        existing_software_stack[SOFTWARE_STACK_DB_VERSION_KEY] + 1
    )

    if not base_os or not stack_id:
        raise Exception("base_os and stack_id are required")

    table_utils.update_item(
        SOFTWARE_STACK_TABLE_NAME,
        key={
            SOFTWARE_STACK_DB_HASH_KEY: base_os,
            SOFTWARE_STACK_DB_RANGE_KEY: stack_id,
        },
        item=software_stack,
    )

    if (
        SOFTWARE_STACK_DB_PROJECTS_KEY in software_stack
        and software_stack[SOFTWARE_STACK_DB_PROJECTS_KEY]
    ):
        software_stack[SOFTWARE_STACK_DB_PROJECTS_KEY] = [
            projects.get_project(project_id)
            for project_id in software_stack[SOFTWARE_STACK_DB_PROJECTS_KEY]
        ]

    return software_stack


def list_software_stacks(
    project_id: Optional[str] = None,
    base_os: Optional[str] = None,
    name: Optional[str] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    List software stacks with filtering
    :param project_id: Filter by project ID
    :param base_os: Filter by base OS
    :param name: Filter by stack name
    :param next_token: Pagination token
    :return: tuple of (list of session permissions, next_token)
    """
    filter_expression = table_utils.construct_filter_expression(
        {
            SOFTWARE_STACK_DB_PROJECTS_KEY: (FilterOperator.CONTAINS, project_id),
            SOFTWARE_STACK_DB_BASE_OS_KEY: base_os,
            SOFTWARE_STACK_DB_NAME_KEY: (FilterOperator.CONTAINS, name),
        }
    )

    return list_software_stacks_paginated(
        filter_expression=filter_expression,
        next_token=next_token,
    )


def get_valid_instance_types_by_software_stack(
    hibernation_support: bool,
    software_stack: Dict[str, Any] = None,
    gpu: str = None,
) -> List[Dict]:
    """Get valid instance types filtered by software stack requirements"""
    # Get allowed/denied instance types from cluster settings
    allowed_instance_types = (
        cluster_settings.get_setting("vdc.dcv_session.instance_types.allow") or []
    )

    valid_instance_types_dict = ec2_utils.get_valid_instance_types_by_allowed_list(
        hibernation_support,
        allowed_instance_types,
    )

    if software_stack and software_stack[SOFTWARE_STACK_DB_BASE_OS_KEY] == "windows":
        image_info = ec2_utils.describe_image_id(
            software_stack[SOFTWARE_STACK_DB_AMI_ID_KEY]
        )

    valid_instance_types_names = []
    valid_instance_types = []
    for instance_type_name in valid_instance_types_dict.keys():
        instance_type_family = instance_type_name.split(".")[0]
        instance_info = valid_instance_types_dict[instance_type_name]
        logger.debug(
            f"Processing - Instance Name: {instance_type_name}   Family: {instance_type_family}"
        )

        if (
            software_stack
            and software_stack[SOFTWARE_STACK_DB_BASE_OS_KEY] == "rhel8"
            and instance_type_family == "g4dn"
        ):
            logger.debug(f"g4dn instances are disabled for RHEL8 instances")
            continue

        if not validate_min_ram(instance_type_name, software_stack):
            continue

        supported_archs = instance_info.get("ProcessorInfo", {}).get(
            "SupportedArchitectures", []
        )
        if (
            software_stack
            and software_stack[SOFTWARE_STACK_DB_ARCHITECTURE_KEY]
            not in supported_archs
        ):
            logger.debug(
                f"Software Stack arch ({software_stack[SOFTWARE_STACK_DB_ARCHITECTURE_KEY]}) != Instance {instance_type_name} ({supported_archs}) Skipped."
            )
            continue

        if (
            software_stack
            and software_stack[SOFTWARE_STACK_DB_BASE_OS_KEY] == "windows"
        ):
            instance_boot_modes = instance_info.get("SupportedBootModes", [])
            image_boot_mode = image_info.get("BootMode", "")
            if image_boot_mode:
                if (
                    image_boot_mode != "uefi-preferred"
                    and image_boot_mode not in instance_boot_modes
                ):
                    logger.debug(
                        f"Software stack ({software_stack}) restrictions on BootMode ({image_boot_mode}): Instance {instance_type_name} doesn't support ({image_boot_mode}). Skipped."
                    )
                    continue
            else:
                if "legacy-bios" not in instance_boot_modes:
                    logger.debug(
                        f"Software stack ({software_stack}) restrictions on BootMode (legacy-bios): Instance {instance_type_name} doesn't support legacy-bios. Skipped."
                    )
                    continue

        supported_gpus = instance_info.get("GpuInfo", {}).get("Gpus", [])
        logger.debug(f"Instance {instance_type_name} GPU ({supported_gpus})")
        gpu_to_check_against = None
        if gpu:
            gpu_to_check_against = gpu
        elif software_stack:
            gpu_to_check_against = software_stack[SOFTWARE_STACK_DB_GPU_KEY]

        if gpu_to_check_against == "NO_GPU":
            if len(supported_gpus) > 0:
                logger.debug(
                    f"Instance {instance_type_name} Should not have GPU ({supported_gpus}) but it does."
                )
                continue
        elif gpu_to_check_against is not None:
            gpu_found = False
            for supported_gpu in supported_gpus:
                gpu_found = (
                    gpu_to_check_against.lower()
                    == str(supported_gpu.get("Manufacturer", "")).lower()
                )
                if gpu_found:
                    break

            if not gpu_found:
                logger.debug(
                    f"Instance {instance_type_name} - Needed a GPU but didn't find one."
                )
                continue

        if software_stack:
            if software_stack[
                SOFTWARE_STACK_DB_TENANCY_KEY
            ] == "host" and not ec2_utils.dedicated_hosts_supported(instance_type_name):
                logger.debug(
                    f"Instance {instance_type_name} doesn't support tenancy {software_stack[SOFTWARE_STACK_DB_TENANCY_KEY]}. Skipped."
                )
                continue

        logger.debug(
            f"Instance {instance_type_name} - Added as valid_instance_types for software_stack"
        )
        valid_instance_types_names.append(instance_type_name)
        valid_instance_types.append(instance_info)

    logger.debug(
        f"Returning valid_instance_types for software_stack: {valid_instance_types_names}"
    )
    return valid_instance_types


def validate_min_ram(
    instance_type_name: str,
    software_stack: Dict[str, Any] = None,
) -> bool:
    """Validate minimum RAM requirements"""
    if software_stack:
        ram_value, ram_unit = ec2_utils.get_instance_ram(instance_type_name)
        if memory_utils.is_greater_than(
            software_stack[SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY],
            software_stack[SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY],
            ram_value,
            ram_unit,
        ):
            logger.debug(
                f"Software stack ({software_stack[SOFTWARE_STACK_DB_NAME_KEY]}) restrictions on RAM ({software_stack[SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY]} {software_stack[SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY]}): Instance {instance_type_name} lacks enough ({ram_value} {ram_unit}). Skipped."
            )
            return False
    return True
