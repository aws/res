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
from abc import ABC

import ideavirtualdesktopcontroller
from ideadatamodel import (
    VirtualDesktopSession,
    Notification
)
from ideavirtualdesktopcontroller.app.events.handlers.base_event_handler import BaseVirtualDesktopControllerEventHandler
from ideavirtualdesktopcontroller.app.permission_profiles.virtual_desktop_permission_profile_db import VirtualDesktopPermissionProfileDB
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_db import VirtualDesktopScheduleDB
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_utils import VirtualDesktopScheduleUtils
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_db import VirtualDesktopServerDB
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_utils import VirtualDesktopServerUtils
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_db import VirtualDesktopSessionPermissionDB
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_utils import VirtualDesktopSessionPermissionUtils
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_db import VirtualDesktopSessionDB
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_utils import VirtualDesktopSessionUtils
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_db import VirtualDesktopSoftwareStackDB
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_utils import VirtualDesktopSoftwareStackUtils


class BaseDBEventHandler(BaseVirtualDesktopControllerEventHandler, ABC):
    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, logger_prefix: str):
        self.context = context
        super().__init__(context, logger_prefix)
        self.software_stack_db: VirtualDesktopSoftwareStackDB = VirtualDesktopSoftwareStackDB(context=self.context)
        self.server_db: VirtualDesktopServerDB = VirtualDesktopServerDB(context=self.context)
        self.schedule_db: VirtualDesktopScheduleDB = VirtualDesktopScheduleDB(context=self.context)
        self.session_db: VirtualDesktopSessionDB = VirtualDesktopSessionDB(
            context=self.context,
            server_db=self.server_db,
            software_stack_db=self.software_stack_db,
            schedule_db=self.schedule_db)
        self.permission_profile_db: VirtualDesktopPermissionProfileDB = VirtualDesktopPermissionProfileDB(context=self.context)
        self.session_permissions_db: VirtualDesktopSessionPermissionDB = VirtualDesktopSessionPermissionDB(context=self.context)
        self.software_stack_utils: VirtualDesktopSoftwareStackUtils = VirtualDesktopSoftwareStackUtils(context=self.context, db=self.software_stack_db)
        self.server_utils: VirtualDesktopServerUtils = VirtualDesktopServerUtils(context=self.context, db=self.server_db)
        self.schedule_utils: VirtualDesktopScheduleUtils = VirtualDesktopScheduleUtils(context=self.context, db=self.schedule_db)
        self.session_permission_utils: VirtualDesktopSessionPermissionUtils = VirtualDesktopSessionPermissionUtils(
            context=self.context,
            db=self.session_permissions_db,
            permission_profile_db=self.permission_profile_db
        )
        self.session_utils: VirtualDesktopSessionUtils = VirtualDesktopSessionUtils(
            context=self.context,
            db=self.session_db,
            session_permission_db=self.session_permissions_db,
            permission_profile_db=self.permission_profile_db
        )

    def _notify_session_owner_of_state_update(self, session: VirtualDesktopSession, deleted=False):
        if deleted:
            template_name = self.context.config().get_string('virtual-desktop-controller.dcv_session.notifications.deleted.email_template', required=True)
            enabled = self.context.config().get_bool('virtual-desktop-controller.dcv_session.notifications.deleted.enabled', required=True)
        else:
            template_name = self.context.config().get_string(f'virtual-desktop-controller.dcv_session.notifications.{session.state.value.lower()}.email_template', required=True)
            enabled = self.context.config().get_bool(f'virtual-desktop-controller.dcv_session.notifications.{session.state.value.lower()}.enabled', required=True)

        if not enabled:
            self._logger.debug(f'Notification NOT sent for {session.idea_session_id} | {session.name} to {session.owner} because notification is not enabled. deleted={deleted}')
            return

        self._logger.info(f'Sending notification for {session.name} to {session.owner} at {template_name}')
        self.context.notification_async_client.send_notification(Notification(
            username=session.owner,
            template_name=template_name,
            params={
                'cluster_name': self.context.cluster_name(),
                'session': session
            }
        ))
