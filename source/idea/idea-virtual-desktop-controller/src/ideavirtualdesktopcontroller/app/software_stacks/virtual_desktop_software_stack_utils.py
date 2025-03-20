#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopArchitecture, VirtualDesktopSoftwareStack, VirtualDesktopSession, VirtualDesktopTenancy, VirtualDesktopAffinity, VirtualDesktopPlacement
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_db import VirtualDesktopSoftwareStackDB
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_db import VirtualDesktopSSMCommandsDB
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import VirtualDesktopControllerUtils
from res.resources import software_stacks


class VirtualDesktopSoftwareStackUtils:

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, db: VirtualDesktopSoftwareStackDB):
        self.context = context
        self._software_stack_db = db
        self._controller_utils = VirtualDesktopControllerUtils(self.context)
        self._ssm_commands_db = VirtualDesktopSSMCommandsDB(self.context)
        self.events_utils = EventsUtils(context=self.context)
        self._logger = context.logger('virtual-desktop-software-stack-utils')

    def create_software_stack(self, software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        software_stack.stack_id = Utils.uuid()
        software_stack_dict = self._software_stack_db.convert_software_stack_object_to_db_dict(software_stack)
        created_software_stack_dict = software_stacks.create_software_stack(software_stack_dict)
        created_software_stack = self._software_stack_db.convert_db_dict_to_software_stack_object(created_software_stack_dict)
        return created_software_stack

    def delete_software_stack(self, software_stack: VirtualDesktopSoftwareStack):
        self._software_stack_db.delete(software_stack)

    def create_software_stack_from_session_when_ready(self, session: VirtualDesktopSession, new_software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        pass

    @staticmethod
    def validate_placement(software_stack: VirtualDesktopSoftwareStack) -> bool:
        placement = software_stack.placement
        if placement:
            if placement.tenancy == VirtualDesktopTenancy.HOST:
                if not placement.affinity:
                    software_stack.placement.affinity = VirtualDesktopAffinity.DEFAULT
                if not placement.host_id and not placement.host_resource_group_arn:
                    software_stack.failure_reason = 'Either software_stack.placement.host_id or placement.host_resource_group_arn is required'
                    return False
                if placement.host_id and placement.host_resource_group_arn:
                    software_stack.failure_reason = 'Both software_stack.placement.host_id and placement.host_resource_group_arn are provided'
                    return False
        else:
            software_stack.placement = VirtualDesktopPlacement(
                tenancy=VirtualDesktopTenancy.DEFAULT,
            )

        return True

    def validate_software_stack_fields(self, software_stack: VirtualDesktopSoftwareStack) -> (VirtualDesktopSoftwareStack, bool):
        if software_stack is None:
            software_stack = VirtualDesktopSoftwareStack()
            software_stack.failure_reason = 'software_stack missing'
            return software_stack, False
        
        fields = {
            'name': 'software_stack.name missing',
            'description': 'software_stack.description missing',
            'ami_id': 'software_stack.ami_id missing',
            'base_os': 'software_stack.base_os missing',
            'gpu': 'software_stack.gpu missing',
            'min_ram': 'software_stack.min_ram missing',
            'min_storage': 'software_stack.min_storage missing'
        }
        
        for field, error_message in fields.items():
            if getattr(software_stack, field) is None:
                software_stack.failure_reason = error_message
                return software_stack, False

        for project in software_stack.projects:
            if project.project_id is None:
                software_stack.failure_reason = 'software_stack.project.project_id missing'
                return software_stack, False

        image_description = self._controller_utils.describe_image_id(software_stack.ami_id)
        if image_description is None or image_description.get('ImageId') != software_stack.ami_id:
            software_stack.failure_reason = f'Invalid software_stack.ami_id: {software_stack.ami_id}'
            return software_stack, False

        if (software_stack.architecture is not None and image_description.get('Architecture') != software_stack.architecture.value):
            software_stack.failure_reason = f'Invalid software_stack.ami_id: {software_stack.ami_id} with architecture: {software_stack.architecture.value}'
            return software_stack, False

        if software_stack.architecture is None:
            software_stack.architecture = VirtualDesktopArchitecture(image_description.get('Architecture'))

        if not self.validate_placement(software_stack):
            return software_stack, False

        return software_stack, True
