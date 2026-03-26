#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import html

from api.exceptions import BadRequestException
from datamodel.models.virtual_desktop_architecture import VirtualDesktopArchitecture
from datamodel.models.virtual_desktop_software_stack import VirtualDesktopSoftwareStack
from datamodel.models.virtual_desktop_tenancy import VirtualDesktopTenancy

from res.resources import (
    software_stacks as res_software_stacks,
)
from res.utils import logging_utils

from res.resources import (
    projects as res_projects,
)
from res.utils import ec2_utils
from datamodel.models.virtual_desktop_affinity import (
    VirtualDesktopAffinity,
)  # noqa: E501
from datamodel.models.virtual_desktop_placement import (
    VirtualDesktopPlacement,
)  # noqa: E501

logger = logging_utils.get_logger(__name__)


def set_software_stack_architecture(
    software_stack: VirtualDesktopSoftwareStack,
) -> None:
    image_description = ec2_utils.describe_image_id(software_stack.ami_id)
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


def validate_software_stack_fields(
    software_stack: VirtualDesktopSoftwareStack,
) -> tuple[VirtualDesktopSoftwareStack, bool]:

    existing_software_stack = res_software_stacks.get_software_stack_by_name(
        software_stack.name
    )
    if existing_software_stack:
        sanitized_name = html.escape(software_stack.name)
        if not software_stack.stack_id:
            software_stack.failure_reason = (
                f'Software stack with name "{sanitized_name}" already exists'
            )
            return software_stack, False
        elif (
            software_stack.stack_id
            and software_stack.stack_id != existing_software_stack.get("stack_id")
        ):
            software_stack.failure_reason = (
                f'Another Software stack with name "{sanitized_name}" already exists'
            )
            return software_stack, False

    set_software_stack_architecture(software_stack)

    for project in software_stack.projects:
        if project.project_id is None or project.project_id == "":
            software_stack.failure_reason = "software_stack.project.project_id missing"
            return software_stack, False
        else:
            project_db_entry = res_projects._get_project_by_id(project.project_id)
            if not project_db_entry:
                software_stack.failure_reason = (
                    f"Invalid software_stack.project.project_id: {project.project_id}"
                )
                return software_stack, False

    if not validate_placement(software_stack):
        return software_stack, False

    return software_stack, True


def validate_placement(software_stack: VirtualDesktopSoftwareStack) -> bool:
    placement = software_stack.placement
    if placement:
        if placement.tenancy == VirtualDesktopTenancy.HOST:
            if not placement.affinity:
                software_stack.placement.affinity = VirtualDesktopAffinity.DEFAULT
            if not placement.host_id and not placement.host_resource_group_arn:
                software_stack.failure_reason = "Either software_stack.placement.host_id or placement.host_resource_group_arn is required"
                return False
            if placement.host_id and placement.host_resource_group_arn:
                software_stack.failure_reason = "Both software_stack.placement.host_id and placement.host_resource_group_arn are provided"
                return False
    else:
        software_stack.placement = VirtualDesktopPlacement(
            tenancy=VirtualDesktopTenancy.DEFAULT,
        )

    return True
