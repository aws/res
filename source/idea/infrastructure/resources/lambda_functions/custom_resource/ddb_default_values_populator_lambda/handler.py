#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from urllib.request import Request, urlopen

import yaml
from res.constants import DEFAULT_REGION_KEY  # type: ignore
from res.resources import cluster_settings  # type: ignore
from res.resources import email_templates  # type: ignore
from res.resources import permission_profiles  # type: ignore
from res.resources import software_stacks  # type: ignore
from res.resources import modules as modules_db
from res.utils import jinja2_utils  # type: ignore

from .constants import (
    BASE_PERMISSION_PROFILE_CONFIG_PATH,
    BASE_SOFTWARE_STACK_CONFIG_PATH,
    DEFAULT_EMAIL_TEMPLATES_CONFIG_PATH,
    REGION_ELB_ACCOUNT_ID_CONFIG,
    TEMPLATES_DIR,
)
from .utils import get_parameters_for_templates

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class CustomResourceResponse(TypedDict):
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html
    Status: str
    Reason: str
    PhysicalResourceId: str
    StackId: str
    RequestId: str
    LogicalResourceId: str


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    logger.info(f"Start populating default values")
    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
    )
    aws_region = os.environ.get(DEFAULT_REGION_KEY)
    aws_partition = os.environ.get("aws_partition")
    aws_dns_suffix = os.environ.get("aws_dns_suffix")
    try:
        if event["RequestType"] == "Create":
            _initialize_modules_cluster_settings()
            _initialize_dynamic_settings()
            _populate_default_software_stacks()
            _populate_default_permission_profiles()
            _populate_default_email_templates()
        elif event["RequestType"] == "Update":
            _initialize_dynamic_settings()
        with open(REGION_ELB_ACCOUNT_ID_CONFIG, "r") as f:
            region_elb_account_id_config = yaml.safe_load(f)
        elb_account_id = region_elb_account_id_config.get(aws_region, "")
        if elb_account_id:
            elb_principal_type = "AWS"
            elb_principal_value = f"arn:{aws_partition}:iam::{elb_account_id}:root"
        else:
            elb_principal_type = "Service"
            elb_principal_value = f"logdelivery.elasticloadbalancing.{aws_dns_suffix}"
        response["Data"] = {
            "elb_principal_type": elb_principal_type,
            "elb_principal_value": elb_principal_value,
        }
    except Exception as e:
        response["Status"] = "FAILED"
        response["Reason"] = "FAILED"
        logger.error(f"Failed to populate default values: {str(e)}")
    finally:
        _send_response(url=event["ResponseURL"], response=response)


def _send_response(url: str, response: CustomResourceResponse) -> None:
    request = Request(
        method="PUT",
        url=url,
        data=json.dumps(response).encode("utf-8"),
    )
    urlopen(request)


def _get_modules_cluster_settings() -> (
    Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]
):
    """
    Process yml templates and replace parameters with corresponding values.
    Generates two lists of dictionaries with DDB keys prefixed with module name and corresponding values.
    :return: Tuple containint two lists:
        1. List of dictionaries to be used for cluster-settings table population
        2. List of dictionaries to be used for modules table population
    """
    settings: List[Dict[str, Any]] = []
    # Generate base cluster settings based on inputs
    values = get_parameters_for_templates()
    env = jinja2_utils.env_using_file_system_loader(search_path=TEMPLATES_DIR)
    config_template = env.get_template("res.yml")
    config_content = config_template.render(**values)
    config = yaml.safe_load(config_content)
    logger.info(f"Loaded config: {config}")
    total_len = 0
    modules = config["modules"]
    for module in modules:
        module_name = module["name"]
        module_id = module["id"]
        logger.info(f"Processing module: {module_name}")
        config_files = module["config_files"]
        for file in config_files:
            template = env.get_template(os.path.join(module_name, file))
            module_settings = template.render(
                **values, module_id=module_id, module_name=module_name
            )
            module_settings = yaml.safe_load(module_settings)
            config_entries: List[Dict[str, Any]] = []
            jinja2_utils.flatten_jinja_config(
                config_entries, module_id, module_settings
            )
            logging.info(
                f"Loaded settings for module: {module_name}, total entries: {len(config_entries)}"
            )
            total_len += len(config_entries)
            settings.extend(config_entries)
    logging.info(f"Total entries added: {total_len}")
    return settings, modules


def _initialize_modules_cluster_settings() -> None:
    """
    Populate cluster-settings and modules table with key/value pairs retrieved from template.
    :return: None
    """
    # Get base cluster settings
    settings, modules = _get_modules_cluster_settings()
    settings = {entries["key"]: entries["value"] for entries in settings}  # type: ignore

    # Add base cluster settings to table
    _, failed_list = cluster_settings.create_settings(settings=settings)
    if failed_list:
        raise Exception(f"Failed to create settings for: {failed_list}")

    # Add to modules table
    try:
        for module in modules:
            modules_db.create_module(
                {
                    modules_db.MODULES_TABLE_HASH_KEY: module["id"],
                    modules_db.MODULES_TABLE_NAME_KEY: module["name"],
                    modules_db.MODULES_TABLE_TYPE_KEY: module["type"],
                }
            )
    except Exception as e:
        raise Exception(f"Failed to create modules")


def _initialize_dynamic_settings() -> None:
    """
    Populate cluster-settings table with settings that will be handled during update event.
    :return: None
    """
    settings = _get_dynamic_settings()
    # Add cluster settings to table
    _, failed_list = cluster_settings.create_settings(settings=settings)
    if failed_list:
        raise Exception(f"Failed to create settings for: {failed_list}")


def _get_dynamic_settings() -> Dict[str, Optional[str]]:
    """
    Retrieve settings that will be handled during update event.
    :return: Dict contains key/value pair.
    """
    return {"shared_library_arn": os.environ.get("shared_library_arn")}


def _populate_default_permission_profiles() -> None:
    if permission_profiles.is_permission_profiles_table_empty():
        logger.info("Empty permission profile table. Creating base permission profiles")
        base_permission_profiles = _load_base_permission_profiles()
        if base_permission_profiles:
            for profile in base_permission_profiles:
                logger.info(
                    f"Start populating {profile[permission_profiles.PERMISSION_PROFILE_DB_HASH_KEY]}"
                )
                permission_profiles.create_permission_profile(profile)


def _load_base_permission_profiles() -> Optional[List[Dict[str, Any]]]:
    with open(BASE_PERMISSION_PROFILE_CONFIG_PATH, "r") as f:
        base_permission_profile_config = yaml.safe_load(f)

    if not base_permission_profile_config:
        logger.error(f"{BASE_PERMISSION_PROFILE_CONFIG_PATH} file is empty. Returning")
        return None

    default_permission_profiles = []
    for profile_name in base_permission_profile_config:
        profile_info = base_permission_profile_config.get(profile_name, {})
        profile_title = profile_info.pop("profile_title", "")
        if not profile_title:
            raise Exception(f"missing required field profile_title for {profile_name}")
        profile_description = profile_info.pop("profile_description", "")
        profile_info[permission_profiles.PERMISSION_PROFILE_DB_HASH_KEY] = profile_name
        profile_info[permission_profiles.PERMISSION_PROFILE_DB_TITLE_KEY] = (
            profile_title
        )
        profile_info[permission_profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY] = (
            profile_description
        )
        default_permission_profiles.append(profile_info)
    return default_permission_profiles


def _populate_default_software_stacks() -> None:
    if software_stacks.is_software_stacks_table_empty():
        logger.info("Empty software stack table. Creating base software stacks")
        base_software_stacks = _load_base_software_stacks()
        if base_software_stacks:
            for stack in base_software_stacks:
                logger.info(
                    f"Start populating {stack[software_stacks.SOFTWARE_STACK_DB_HASH_KEY]} {stack[software_stacks.SOFTWARE_STACK_DB_RANGE_KEY]}"
                )
                software_stacks.create_software_stack(stack)


def _load_base_software_stacks() -> Optional[List[Dict[str, Any]]]:
    with open(BASE_SOFTWARE_STACK_CONFIG_PATH, "r") as f:
        base_stacks_config = yaml.safe_load(f)

    if not base_stacks_config:
        logger.error(f"{BASE_SOFTWARE_STACK_CONFIG_PATH} is empty. Returning")
        return None

    base_software_stacks = []
    for base_os in software_stacks.BASE_OS:
        logger.info(f"Processing base_os: {base_os}")
        os_config = base_stacks_config.get(base_os)
        for arch in software_stacks.ARCHITECTURE:
            arch_key = _reformat_key(arch)
            logger.info(f"Processing architecture: {arch_key} with base_os: {base_os}")
            arch_config = os_config.get(arch_key)
            if not arch_config:
                logger.error(
                    f"Entry for architecture: {arch_key} within base_os: {base_os}. NOT FOUND. Returning"
                )
                continue

            default_name = arch_config.get("default-name")
            default_description = arch_config.get("default-description")
            default_min_storage_value = arch_config.get("default-min-storage-value")
            default_min_storage_unit = arch_config.get("default-min-storage-unit")
            default_min_ram_value = arch_config.get("default-min-ram-value")
            default_min_ram_unit = arch_config.get("default-min-ram-unit")

            if (
                not default_name
                or not default_description
                or not default_min_storage_value
                or not default_min_storage_unit
                or not default_min_ram_value
                or not default_min_ram_unit
            ):
                error_message = (
                    f"Invalid base-software-stack-config.yaml configuration for OS: {base_os} Arch Config: "
                    f"{arch}. Missing default-name and/or default-description and/or default-min-storage-value "
                    f"and/or default-min-storage-unit and/or default-min-ram-value and/or default-min-ram-unit"
                )
                logger.error(error_message)
                raise Exception(error_message)

            aws_region = os.environ.get("AWS_DEFAULT_REGION")
            logger.info(
                f"Processing arch: {arch_key} within base_os: {base_os} "
                f"for aws_region: {aws_region}"
            )

            region_configs = arch_config.get(aws_region)
            if not region_configs:
                logger.error(
                    f"Entry for arch: {arch_key} within base_os: {base_os}. "
                    f"for aws_region: {aws_region} "
                    f"NOT FOUND. Returning"
                )
                continue

            for region_config in region_configs:
                ami_id = region_config.get("ami-id")
                if not ami_id:
                    error_message = (
                        f"Invalid base-software-stack-config.yaml configuration for OS: {base_os} Arch"
                        f" Config: {arch} AWS-Region: {aws_region}."
                        f" Missing ami-id"
                    )
                    logger.error(error_message)
                    raise Exception(error_message)

                ss_id_suffix = region_config.get("ss-id-suffix")
                if not ss_id_suffix:
                    error_message = (
                        f"Invalid base-software-stack-config.yaml configuration for OS: {base_os} Arch"
                        f" Config: {arch} AWS-Region: {aws_region}."
                        f" Missing ss-id-suffix"
                    )
                    logger.error(error_message)
                    raise Exception(error_message)

                gpu_manufacturer = region_config.get("gpu-manufacturer")
                if gpu_manufacturer and gpu_manufacturer not in {
                    "AMD",
                    "NVIDIA",
                    "NO_GPU",
                }:
                    error_message = (
                        f"Invalid base-software-stack-config.yaml configuration for OS: {base_os} Arch"
                        f" Config: {arch} AWS-Region: {aws_region}."
                        f" Invalid gpu-manufacturer {gpu_manufacturer} can be one of AMD, NVIDIA, NO_GPU only"
                    )

                    logger.error(error_message)
                    raise Exception(error_message)
                elif not gpu_manufacturer:
                    gpu_manufacturer = "NO_GPU"

                custom_stack_name = region_config.get(
                    software_stacks.SOFTWARE_STACK_DB_NAME_KEY, default_name
                )
                custom_stack_description = region_config.get(
                    software_stacks.SOFTWARE_STACK_DB_DESCRIPTION_KEY,
                    default_description,
                )
                custom_stack_min_storage_value = region_config.get(
                    _reformat_key(
                        software_stacks.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY
                    ),
                    default_min_storage_value,
                )
                custom_stack_min_storage_unit = region_config.get(
                    _reformat_key(
                        software_stacks.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY
                    ),
                    default_min_storage_unit,
                )
                custom_stack_min_ram_value = region_config.get(
                    _reformat_key(software_stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY),
                    default_min_ram_value,
                )
                custom_stack_min_ram_unit = region_config.get(
                    _reformat_key(software_stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY),
                    default_min_ram_unit,
                )
                custom_stack_gpu_manufacturer = gpu_manufacturer

                software_stack_id = f"{software_stacks.BASE_STACK_PREFIX}-{base_os}-{arch_key}-{ss_id_suffix}"

                base_software_stacks.append(
                    {
                        software_stacks.SOFTWARE_STACK_DB_HASH_KEY: base_os,
                        software_stacks.SOFTWARE_STACK_DB_RANGE_KEY: software_stack_id,
                        software_stacks.SOFTWARE_STACK_DB_NAME_KEY: custom_stack_name,
                        software_stacks.SOFTWARE_STACK_DB_DESCRIPTION_KEY: custom_stack_description,
                        software_stacks.SOFTWARE_STACK_DB_AMI_ID_KEY: ami_id,
                        software_stacks.SOFTWARE_STACK_DB_ENABLED_KEY: True,
                        software_stacks.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: custom_stack_min_storage_value,
                        software_stacks.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: custom_stack_min_storage_unit,
                        software_stacks.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: custom_stack_min_ram_value,
                        software_stacks.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: custom_stack_min_ram_unit,
                        software_stacks.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: arch,
                        software_stacks.SOFTWARE_STACK_DB_GPU_KEY: custom_stack_gpu_manufacturer,
                        software_stacks.SOFTWARE_STACK_DB_PROJECTS_KEY: [],
                    }
                )

    return base_software_stacks


def _reformat_key(key: str) -> str:
    return key.replace("_", "-")


def _populate_default_email_templates() -> None:
    if email_templates.is_email_templates_table_empty():
        logger.info("Empty email template table. Creating base email templates")
        base_email_templates = _load_base_email_templates()
        if base_email_templates:
            for template in base_email_templates:
                logger.info(f"Start populating {template['name']}")
                email_templates.create_email_template(template)


def _load_base_email_templates() -> Optional[List[Dict[str, Any]]]:
    with open(DEFAULT_EMAIL_TEMPLATES_CONFIG_PATH, "r") as f:
        default_email_templates_config = yaml.safe_load(f)

    if not default_email_templates_config:
        raise Exception(f"{DEFAULT_EMAIL_TEMPLATES_CONFIG_PATH} file is empty.")

    default_email_templates = []
    for template in default_email_templates_config.get("templates", {}):
        default_email_templates.append(template)
    return default_email_templates
