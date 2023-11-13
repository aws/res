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
from typing import List, Union

import ideavirtualdesktopcontroller
from ideadatamodel import VirtualDesktopSessionPermission, VirtualDesktopSession, VirtualDesktopBaseOS, UpdateSessionPermissionRequest, UpdateSessionPermissionResponse
from ideasdk.analytics.analytics_service import AnalyticsEntry, EntryAction, EntryContent
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.permission_profiles.virtual_desktop_permission_profile_db import VirtualDesktopPermissionProfileDB
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_db import VirtualDesktopSessionPermissionDB
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import VirtualDesktopControllerUtils


class VirtualDesktopSessionPermissionUtils:
    WINDOWS_POWERSHELL_NEW_LINE = '`r`n'
    LINUX_CMD_NEW_LINE = '\n'

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext, db: VirtualDesktopSessionPermissionDB, permission_profile_db: VirtualDesktopPermissionProfileDB):
        self.context = context
        self._logger = self.context.logger('virtual-desktop-session-permission-utils')
        self._session_permission_db = db
        self._permission_profile_db = permission_profile_db
        self.events_utils: EventsUtils = EventsUtils(context=self.context)
        self.controller_utils: VirtualDesktopControllerUtils = VirtualDesktopControllerUtils(self.context)

    @staticmethod
    def _generate_entry_id(session_permission: VirtualDesktopSessionPermission) -> str:
        return f'permission-{session_permission.idea_session_id}-{session_permission.actor_name}'

    def index_session_permission_to_opensearch(self, session_permission: VirtualDesktopSessionPermission):
        index_name = f"{self.context.config().get_string('virtual-desktop-controller.opensearch.session_permission.alias', required=True)}-{self.context.session_permission_template_version}"
        self.context.analytics_service().post_entry(AnalyticsEntry(
            entry_id=self._generate_entry_id(session_permission),
            entry_action=EntryAction.CREATE_ENTRY,
            entry_content=EntryContent(
                index_id=index_name,
                entry_record=self._session_permission_db.convert_session_permission_object_to_db_dict(session_permission)
            )
        ))

    def delete_session_entry_from_opensearch(self, session_permission: VirtualDesktopSessionPermission):
        index_name = f"{self.context.config().get_string('virtual-desktop-controller.opensearch.session_permission.alias', required=True)}-{self.context.session_permission_template_version}"
        self.context.analytics_service().post_entry(AnalyticsEntry(
            entry_id=self._generate_entry_id(session_permission),
            entry_action=EntryAction.DELETE_ENTRY,
            entry_content=EntryContent(
                index_id=index_name
            )
        ))

    def update_session_entry_to_opensearch(self, session_permission: VirtualDesktopSessionPermission):
        index_name = f"{self.context.config().get_string('virtual-desktop-controller.opensearch.session_permission.alias', required=True)}-{self.context.session_permission_template_version}"
        self.context.analytics_service().post_entry(AnalyticsEntry(
            entry_id=self._generate_entry_id(session_permission),
            entry_action=EntryAction.UPDATE_ENTRY,
            entry_content=EntryContent(
                index_id=index_name,
                entry_record=self._session_permission_db.convert_session_permission_object_to_db_dict(session_permission)
            )
        ))

    def _retrieve_permission_profile_values(self, profile_id) -> (List[str], List[str]):
        allow_permissions: List[str] = []
        deny_permissions: List[str] = []

        permission_profile = self._permission_profile_db.get(profile_id=profile_id)

        builtin_permission = permission_profile.get_permission('builtin')
        if Utils.is_not_empty(builtin_permission) and builtin_permission.enabled:
            allow_permissions.append('builtin')
        else:
            for permission in self._permission_profile_db.permission_types:
                permission_entry = permission_profile.get_permission(permission.key)
                if permission_entry.enabled:
                    allow_permissions.append(permission.key.replace('_', '-'))
                else:
                    deny_permissions.append(permission.key.replace('_', '-'))

        return allow_permissions, deny_permissions

    def generate_permissions_for_session(self, session: VirtualDesktopSession, for_broker: bool) -> Union[str, None]:
        admin_username = self.context.config().get_string('cluster.administrator_username', required=True) if session.software_stack.base_os != VirtualDesktopBaseOS.WINDOWS else 'Administrator'

        if for_broker or session.software_stack.base_os != VirtualDesktopBaseOS.WINDOWS:
            new_line_char = self.LINUX_CMD_NEW_LINE
        else:
            new_line_char = self.WINDOWS_POWERSHELL_NEW_LINE

        permission = f'[groups]{new_line_char}'
        if session.software_stack.base_os == VirtualDesktopBaseOS.WINDOWS:
            permission += f'group:ideaadmin=user:{admin_username}{new_line_char}'
        else:
            permission += f'group:ideaadmin=user:{admin_username}, osgroup:{self.controller_utils.get_virtual_desktop_admin_group()}{new_line_char}'
        permission += f'[aliases]{new_line_char}'

        permission_profiles = set()
        profile_cache = {}

        admin_profile = self.context.config().get_string('virtual-desktop-controller.dcv_session.default_profiles.admin', required=True)
        permission_profiles.add(admin_profile)

        session_permissions = self._session_permission_db.get_for_session(session.idea_session_id)
        for session_permission in session_permissions:
            permission_profiles.add(session_permission.permission_profile.profile_id)

        for profile in permission_profiles:
            allow_permissions, deny_permissions = self._retrieve_permission_profile_values(profile)
            if Utils.is_not_empty(allow_permissions):
                permission += f'{profile}-allow={", ".join(allow_permissions)}{new_line_char}'
            if Utils.is_not_empty(deny_permissions):
                permission += f'{profile}-deny={", ".join(deny_permissions)}{new_line_char}'

            profile_cache[profile] = {
                'allow': allow_permissions,
                'deny': deny_permissions
            }

        permission += f'[permissions]{new_line_char}'

        # Apply guest permissions
        for session_permission in session_permissions:
            profile_id = session_permission.permission_profile.profile_id
            if Utils.is_not_empty(profile_cache[profile_id]['allow']):
                permission += f'{session_permission.actor_name} allow {profile_id}-allow{new_line_char}'
            if Utils.is_not_empty(profile_cache[admin_profile]['deny']):
                permission += f'{session_permission.actor_name} deny {profile_id}-deny{new_line_char}'

        # Apply admin permission
        if Utils.is_not_empty(profile_cache[admin_profile]['allow']):
            permission += f'group:ideaadmin allow {admin_profile}-allow{new_line_char}'
        if Utils.is_not_empty(profile_cache[admin_profile]['deny']):
            permission += f'group:ideaadmin deny {admin_profile}-deny{new_line_char}'

        # Apply owner permission
        if Utils.is_not_empty(profile_cache[admin_profile]['allow']):
            permission += f'%owner% allow {admin_profile}-allow{new_line_char}'
        if Utils.is_not_empty(profile_cache[admin_profile]['deny']):
            permission += f'%owner% deny {admin_profile}-deny{new_line_char}'

        return permission

    def update_permission_for_sessions(self, request: UpdateSessionPermissionRequest) -> UpdateSessionPermissionResponse:
        response = []
        sessions_info = set()
        for session_permission in request.create:
            response.append(self._session_permission_db.create(session_permission))
            sessions_info.add((session_permission.idea_session_id, session_permission.idea_session_owner))
        for session_permission in request.update:
            response.append(self._session_permission_db.update(session_permission))
            sessions_info.add((session_permission.idea_session_id, session_permission.idea_session_owner))
        for session_permission in request.delete:
            self._session_permission_db.delete(session_permission)
            sessions_info.add((session_permission.idea_session_id, session_permission.idea_session_owner))

        for session_info in sessions_info:
            self.events_utils.publish_enforce_session_permissions_event(
                idea_session_id=session_info[0],
                idea_session_owner=session_info[1],
            )

        return UpdateSessionPermissionResponse(
            permissions=response
        )

    def delete_permissions_for_session(self, session: VirtualDesktopSession):
        session_permissions = self._session_permission_db.get_for_session(session.idea_session_id)
        if Utils.is_empty(session_permissions):
            return
        for session_permission in session_permissions:
            self._session_permission_db.delete(session_permission)
