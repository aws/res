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
from ideasdk.analytics.analytics_service import AnalyticsEntry, EntryAction, EntryContent
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

    def create_software_stack_from_session_when_ready(self, session: VirtualDesktopSession, new_software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        pass

    def delete_software_stack_entry_from_opensearch(self, software_stack_id: str):
        index_name = f"{self.context.config().get_string('virtual-desktop-controller.opensearch.software_stack.alias', required=True)}-{self.context.software_stack_template_version}"
        self.context.analytics_service().post_entry(AnalyticsEntry(
            entry_id=software_stack_id,
            entry_action=EntryAction.DELETE_ENTRY,
            entry_content=EntryContent(
                index_id=index_name
            )
        ))

    def update_software_stack_entry_to_opensearch(self, software_stack: VirtualDesktopSoftwareStack):
        index_name = f"{self.context.config().get_string('virtual-desktop-controller.opensearch.software_stack.alias', required=True)}-{self.context.software_stack_template_version}"
        self.context.analytics_service().post_entry(AnalyticsEntry(
            entry_id=software_stack.stack_id,
            entry_action=EntryAction.UPDATE_ENTRY,
            entry_content=EntryContent(
                index_id=index_name,
                entry_record=self._software_stack_db.convert_software_stack_object_to_index_dict(software_stack)
            )
        ))

    def index_software_stack_entry_to_opensearch(self, software_stack: VirtualDesktopSoftwareStack):
        index_name = f"{self.context.config().get_string('virtual-desktop-controller.opensearch.software_stack.alias', required=True)}-{self.context.software_stack_template_version}"
        index_dict = self._software_stack_db.convert_software_stack_object_to_index_dict(software_stack)
        self.context.analytics_service().post_entry(AnalyticsEntry(
            entry_id=software_stack.stack_id,
            entry_action=EntryAction.CREATE_ENTRY,
            entry_content=EntryContent(
                index_id=index_name,
                entry_record=index_dict
            )
        ))
