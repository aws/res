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
from ideadatamodel import VirtualDesktopSoftwareStack, VirtualDesktopSession
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_db import VirtualDesktopSoftwareStackDB
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_db import VirtualDesktopSSMCommandsDB
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import VirtualDesktopControllerUtils


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
        return self._software_stack_db.create(software_stack)

    def delete_software_stack(self, software_stack: VirtualDesktopSoftwareStack):
        self._software_stack_db.delete(software_stack)

    def create_software_stack_from_session_when_ready(self, session: VirtualDesktopSession, new_software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        pass
