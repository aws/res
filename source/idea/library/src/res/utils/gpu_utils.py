#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.resources import cluster_settings


def is_gpu_instance_type(instance_type: str) -> bool:
    instance_family = instance_type.split(".")[0]
    gpu_instance_families = cluster_settings.get_setting(
        "global-settings.gpu_settings.instance_families"
    )
    return instance_family in gpu_instance_families


def is_nvidia_gpu(instance_type: str) -> bool:
    instance_family = instance_type.split(".")[0]
    try:
        cluster_settings.get_setting(
            f"global-settings.gpu_settings.nvidia_public_driver_versions.{instance_family}"
        )
        return True
    except Exception:
        return False


def is_amd_gpu(instance_type: str) -> bool:
    return is_gpu_instance_type(instance_type) and not is_nvidia_gpu(instance_type)
