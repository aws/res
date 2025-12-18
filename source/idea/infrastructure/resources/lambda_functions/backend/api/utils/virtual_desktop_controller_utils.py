#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from threading import RLock
from typing import Any, Dict, List, Optional

from api.exceptions import BadRequestException
from api.models.res_memory import ResMemory
from api.models.virtual_desktop_architecture import VirtualDesktopArchitecture
from api.models.virtual_desktop_base_os import VirtualDesktopBaseOs
from api.models.virtual_desktop_gpu import VirtualDesktopGpu
from api.models.virtual_desktop_session import VirtualDesktopSession
from api.models.virtual_desktop_software_stack import VirtualDesktopSoftwareStack
from api.models.virtual_desktop_tenancy import VirtualDesktopTenancy
from api.utils import res_memory_utils
from botocore.exceptions import ClientError
from res.clients.aws.aws_provider import AwsClientProvider
from res.resources import cluster_settings
from res.utils import logging_utils

# Global AWS client provider and cache for instance type information
_aws_client_provider = AwsClientProvider()
_instance_types_cache = {}
_instance_types_lock = RLock()

logger = logging_utils.get_logger(__name__)


def _add_instance_data_to_cache(cache_dict: Dict):
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

    if instance_info_key not in _instance_types_cache:
        _add_instance_data_to_cache(_instance_types_cache)

    return _instance_types_cache[instance_info_key][instance_type]


def get_instance_ram(instance_type: str) -> ResMemory:
    """Get instance RAM information"""
    instance_info = get_instance_type_info(instance_type)
    return ResMemory(
        value=float(instance_info.get("MemoryInfo", {}).get("SizeInMiB", 0)), unit="MiB"
    )


def get_architecture(instance_type: str) -> Optional[VirtualDesktopArchitecture]:
    """Get architecture for instance type"""
    instance_info = get_instance_type_info(instance_type)
    supported_archs = instance_info.get("ProcessorInfo", {}).get(
        "SupportedArchitectures", []
    )
    for supported_arch in supported_archs:
        if supported_arch == VirtualDesktopArchitecture.ARM64.value:
            return VirtualDesktopArchitecture.ARM64
        if supported_arch == VirtualDesktopArchitecture.X86_64.value:
            return VirtualDesktopArchitecture.X86_64
    return None


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


def dedicated_hosts_supported(instance_type: str) -> bool:
    """Check if instance type supports dedicated hosts"""
    instance_info = get_instance_type_info(instance_type)
    return instance_info.get("DedicatedHostsSupported", False)


def validate_min_ram(
    instance_type_name: str, software_stack: Optional[VirtualDesktopSoftwareStack]
) -> bool:
    """Validate minimum RAM requirements"""
    if software_stack and res_memory_utils.is_greater_than(
        software_stack.min_ram, get_instance_ram(instance_type_name)
    ):
        logger.debug(
            f"Software stack ({software_stack.name}) restrictions on RAM ({software_stack.min_ram}): Instance {instance_type_name} lacks enough ({get_instance_ram(instance_type_name)}). Skipped."
        )
        return False
    return True


def get_valid_instance_types_by_allowed_list(
    hibernation_support: bool,
    allowed_instance_types: List[str],
) -> Dict:
    """Get valid instance types based on allowed/denied lists"""
    instance_type_names_key = "aws.ec2.all-instance-types-names-list"
    instance_info_key = "aws.ec2.all-instance-types-data"

    if (
        instance_type_names_key not in _instance_types_cache
        or instance_info_key not in _instance_types_cache
    ):
        _add_instance_data_to_cache(_instance_types_cache)

    instance_types_names = _instance_types_cache[instance_type_names_key]
    instance_info_data = _instance_types_cache[instance_info_key]

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


def get_valid_instance_types_by_software_stack(
    hibernation_support: bool,
    software_stack: VirtualDesktopSoftwareStack = None,
    gpu: VirtualDesktopGpu = None,
) -> List[Dict]:
    """Get valid instance types filtered by software stack requirements"""
    # Get allowed/denied instance types from cluster settings
    allowed_instance_types = (
        cluster_settings.get_setting("vdc.dcv_session.instance_types.allow") or []
    )

    valid_instance_types_dict = get_valid_instance_types_by_allowed_list(
        hibernation_support,
        allowed_instance_types,
    )

    if software_stack and software_stack.base_os == VirtualDesktopBaseOs.WINDOWS:
        image_info = describe_image_id(software_stack.ami_id)

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
            and software_stack.base_os == VirtualDesktopBaseOs.RHEL8
            and instance_type_family == "g4dn"
        ):
            logger.debug(f"g4dn instances are disabled for RHEL8 instances")
            continue

        if not validate_min_ram(instance_type_name, software_stack):
            continue

        supported_archs = instance_info.get("ProcessorInfo", {}).get(
            "SupportedArchitectures", []
        )
        if software_stack and software_stack.architecture.value not in supported_archs:
            logger.debug(
                f"Software Stack arch ({software_stack.architecture.value}) != Instance {instance_type_name} ({supported_archs}) Skipped."
            )
            continue

        if software_stack and software_stack.base_os == VirtualDesktopBaseOs.WINDOWS:
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
            gpu_to_check_against = software_stack.gpu

        if gpu_to_check_against == VirtualDesktopGpu.NO_GPU:
            if len(supported_gpus) > 0:
                logger.debug(
                    f"Instance {instance_type_name} Should not have GPU ({supported_gpus}) but it does."
                )
                continue
        elif gpu_to_check_against is not None:
            gpu_found = False
            for supported_gpu in supported_gpus:
                gpu_found = (
                    gpu_to_check_against.value.lower()
                    == str(supported_gpu.get("Manufacturer", "")).lower()
                )
                if gpu_found:
                    break

            if not gpu_found:
                logger.debug(
                    f"Instance {instance_type_name} - Needed a GPU but didn't find one."
                )
                continue

        if software_stack and software_stack.placement:
            if (
                software_stack.placement.tenancy == VirtualDesktopTenancy.HOST
                and not dedicated_hosts_supported(instance_type_name)
            ):
                logger.debug(
                    f"Instance {instance_type_name} doesn't support tenancy {software_stack.placement.tenancy}. Skipped."
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


def set_software_stack_architecture(
    software_stack: VirtualDesktopSoftwareStack,
) -> None:
    image_description = describe_image_id(software_stack.ami_id)
    if not image_description:
        raise BadRequestException(
            f"Invalid software_stack.ami_id: {software_stack.ami_id}"
        )

    if (
        software_stack.architecture is not None
        and image_description.get("Architecture") != software_stack.architecture.value
    ):
        raise BadRequestException(
            f"Invalid software_stack.ami_id: {software_stack.ami_id} with architecture: {software_stack.architecture.value}"
        )

    if not software_stack.architecture:
        software_stack.architecture = VirtualDesktopArchitecture(
            image_description.get("Architecture")
        )
