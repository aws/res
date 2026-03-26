#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from enum import Enum
from threading import RLock
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError
from res.clients.aws.aws_provider import AwsClientProvider
from res.resources import cluster_settings, software_stacks
from res.utils import logging_utils

# Global AWS client provider and cache for instance type information
_aws_client_provider = AwsClientProvider()
_instance_types_lock = RLock()
instance_types_cache = {}

logger = logging_utils.get_logger("ec2-utils")


class VirtualDesktopGpu(str, Enum):
    NO_GPU = "NO_GPU"
    NVIDIA = "NVIDIA"
    AMD = "AMD"


def add_instance_data_to_cache(cache_dict: Dict):
    """Add EC2 instance type data to cache"""
    with _instance_types_lock:
        instance_type_names_key = "aws.ec2.all-instance-types-names-list"
        instance_info_key = "aws.ec2.all-instance-types-data"

        if (
            instance_type_names_key not in cache_dict
            or instance_info_key not in cache_dict
        ):
            instance_type_names = []
            instance_info_data = {}

            ec2_client = _aws_client_provider.ec2()
            has_more = True
            next_token = None
            while has_more:
                if next_token is None:
                    result = ec2_client.describe_instance_types(MaxResults=100)
                else:
                    result = ec2_client.describe_instance_types(
                        MaxResults=100, NextToken=next_token
                    )

                next_token = str(result.get("NextToken", ""))
                has_more = next_token and len(next_token) > 0
                current_instance_types = result.get("InstanceTypes", [])
                for current_instance_type in current_instance_types:
                    instance_type_name = str(
                        current_instance_type.get("InstanceType", "")
                    )
                    instance_type_names.append(instance_type_name)
                    instance_info_data[instance_type_name] = current_instance_type

            cache_dict[instance_type_names_key] = instance_type_names
            cache_dict[instance_info_key] = instance_info_data


def get_instance_type_info(instance_type: str) -> Dict:
    """Get instance type information"""
    instance_info_key = "aws.ec2.all-instance-types-data"

    if instance_info_key not in instance_types_cache:
        add_instance_data_to_cache(instance_types_cache)

    return instance_types_cache[instance_info_key][instance_type]


def dedicated_hosts_supported(instance_type: str) -> bool:
    """Check if instance type supports dedicated hosts"""
    instance_info = get_instance_type_info(instance_type)
    return instance_info.get("DedicatedHostsSupported", False)


def get_systems_manager_parameter(parameter_arn: str) -> Dict[str, Any]:
    """Get parameter from Systems Manager"""
    try:
        ssm_client = _aws_client_provider.ssm()
        return ssm_client.get_parameter(
            Name=parameter_arn,
        ).get("Parameter", {})
    except ClientError as e:
        logger.error(e)
        return {}


def describe_image_id(ami_id: str) -> dict:
    """Describe AMI image by ID"""
    if not ami_id:
        return {}

    if ami_id.startswith("arn:"):
        parameter = get_systems_manager_parameter(ami_id)
        ami_id = parameter.get("Value", "")

    try:
        ec2_client = _aws_client_provider.ec2()
        response = dict(ec2_client.describe_images(ImageIds=[ami_id]))
    except ClientError as e:
        logger.error(e)
        return {}

    images = response.get("Images", [])
    for image in images:
        return image
    return {}


def get_instance_ram(instance_type: str) -> tuple[float, str]:
    """Get instance RAM information"""
    instance_info = get_instance_type_info(instance_type)
    return float(instance_info.get("MemoryInfo", {}).get("SizeInMiB", 0)), "MiB"


def is_gpu_instance(instance_type: str) -> bool:
    """Check if instance type has GPU support"""
    return get_gpu_manufacturer(instance_type) != VirtualDesktopGpu.NO_GPU


def get_gpu_manufacturer(instance_type: str) -> VirtualDesktopGpu:
    """Get GPU manufacturer for instance type"""
    instance_info = get_instance_type_info(instance_type)
    supported_gpus = instance_info.get("GpuInfo", {}).get("Gpus", [])
    if len(supported_gpus) == 0:
        return VirtualDesktopGpu.NO_GPU

    for supported_gpu in supported_gpus:
        manufacturer = str(supported_gpu.get("Manufacturer", "")).lower()
        if manufacturer == VirtualDesktopGpu.NVIDIA.lower():
            return VirtualDesktopGpu.NVIDIA
        elif manufacturer == VirtualDesktopGpu.AMD.lower():
            return VirtualDesktopGpu.AMD

    return VirtualDesktopGpu.NO_GPU


def get_architecture(instance_type: str) -> Optional[str]:
    """Get architecture for instance type"""
    instance_info = get_instance_type_info(instance_type)
    supported_archs = instance_info.get("ProcessorInfo", {}).get(
        "SupportedArchitectures", []
    )
    for supported_arch in supported_archs:
        if supported_arch in software_stacks.ARCHITECTURE:
            return supported_arch
    return None


def get_valid_instance_types_by_allowed_list(
    hibernation_support: bool,
    allowed_instance_types: List[str],
) -> Dict:
    """Get valid instance types based on allowed/denied lists"""
    instance_type_names_key = "aws.ec2.all-instance-types-names-list"
    instance_info_key = "aws.ec2.all-instance-types-data"

    if (
        instance_type_names_key not in instance_types_cache
        or instance_info_key not in instance_types_cache
    ):
        add_instance_data_to_cache(instance_types_cache)

    instance_types_names = instance_types_cache[instance_type_names_key]
    instance_info_data = instance_types_cache[instance_info_key]

    valid_instance_types_dict = {}

    allowed_instance_type_names = set()
    allowed_instance_type_families = set()
    for instance_type in allowed_instance_types:
        if "." in instance_type:
            allowed_instance_type_names.add(instance_type)
        else:
            allowed_instance_type_families.add(instance_type)

    denied_instance_types = (
        cluster_settings.get_setting("vdc.dcv_session.instance_types.deny") or []
    )
    denied_instance_type_names = set()
    denied_instance_type_families = set()
    for instance_type in denied_instance_types:
        if "." in instance_type:
            denied_instance_type_names.add(instance_type)
        else:
            denied_instance_type_families.add(instance_type)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"get_valid_instance_types() - Instance Allow/Deny Summary")
        logger.debug(f"Allowed instance Families: {allowed_instance_type_families}")
        logger.debug(f"Allowed instances: {allowed_instance_type_names}")
        logger.debug(f"Denied instance Families: {denied_instance_type_families}")
        logger.debug(f"Denied instances: {denied_instance_type_names}")

    for instance_type_name in instance_types_names:
        instance_type_family = instance_type_name.split(".")[0]
        logger.debug(
            f"Processing - Instance Name: {instance_type_name}   Family: {instance_type_family}"
        )

        if (
            instance_type_name not in allowed_instance_type_names
            and instance_type_family not in allowed_instance_type_families
        ):
            logger.debug(
                f"Found {instance_type_name} ({instance_type_family}) NOT in ALLOW config: ({allowed_instance_type_names} / {allowed_instance_type_families})"
            )
            continue

        if (
            instance_type_name in denied_instance_type_names
            or instance_type_family in denied_instance_type_families
        ):
            logger.debug(
                f"Found {instance_type_name} ({instance_type_family}) IN DENIED config: ({denied_instance_type_names} / {denied_instance_type_families})"
            )
            continue

        instance_info = instance_info_data[instance_type_name]
        hibernation_supported = bool(instance_info.get("HibernationSupported", False))
        if hibernation_support and not hibernation_supported:
            logger.debug(
                f"Hibernation ({hibernation_support}) != Instance {instance_type_name} ({hibernation_supported}) Skipped."
            )
            continue

        logger.debug(f"Instance {instance_type_name} - Added as valid_instance_types")
        valid_instance_types_dict[instance_type_name] = instance_info

    logger.debug(f"Returning valid_instance_types: {valid_instance_types_dict.keys()}")
    return valid_instance_types_dict
