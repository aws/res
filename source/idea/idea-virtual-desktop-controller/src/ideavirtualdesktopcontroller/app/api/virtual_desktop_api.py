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
import random
from abc import abstractmethod
from typing import List, Optional

import ideavirtualdesktopcontroller
from ideadatamodel import (
    ListSoftwareStackRequest,
    ListSoftwareStackResponse,
    ListPermissionsRequest,
    ListPermissionsResponse,
    Project,
    UpdateSessionPermissionRequest,
    VirtualDesktopSessionState,
    VirtualDesktopSessionType,
    VirtualDesktopServer,
    VirtualDesktopSession,
    VirtualDesktopSessionScreenshot,
    VirtualDesktopSessionConnectionInfo,
    VirtualDesktopBaseOS,
    VirtualDesktopSoftwareStack,
    VirtualDesktopSessionPermission,
    SocaMemory,
    SocaMemoryUnit,
    SocaFilter,
    VirtualDesktopGPU,
    VirtualDesktopArchitecture
)
from ideadatamodel import exceptions
from ideadatamodel import constants
from ideasdk.api import (
    ApiInvocationContext,
    BaseAPI
)
from ideasdk.context import ArnBuilder
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.events.events_utils import EventsUtils
from ideavirtualdesktopcontroller.app.permission_profiles.virtual_desktop_permission_profile_db import VirtualDesktopPermissionProfileDB
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_db import VirtualDesktopScheduleDB
from ideavirtualdesktopcontroller.app.schedules.virtual_desktop_schedule_utils import VirtualDesktopScheduleUtils
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_db import VirtualDesktopServerDB
from ideavirtualdesktopcontroller.app.servers.virtual_desktop_server_utils import VirtualDesktopServerUtils
from ideavirtualdesktopcontroller.app.session_permissions.constants import SESSION_PERMISSIONS_FILTER_SESSION_ID_KEY, SESSION_PERMISSIONS_FILTER_ACTOR_KEY
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_db import VirtualDesktopSessionPermissionDB
from ideavirtualdesktopcontroller.app.session_permissions.virtual_desktop_session_permission_utils import VirtualDesktopSessionPermissionUtils
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_db import VirtualDesktopSessionDB
from ideavirtualdesktopcontroller.app.sessions.virtual_desktop_session_utils import VirtualDesktopSessionUtils
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_db import VirtualDesktopSoftwareStackDB
from ideavirtualdesktopcontroller.app.software_stacks.virtual_desktop_software_stack_utils import VirtualDesktopSoftwareStackUtils
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_db import VirtualDesktopSSMCommandsDB
from ideavirtualdesktopcontroller.app.ssm_commands.virtual_desktop_ssm_commands_utils import VirtualDesktopSSMCommandsUtils
from ideavirtualdesktopcontroller.app.virtual_desktop_controller_utils import VirtualDesktopControllerUtils


class VirtualDesktopAPI(BaseAPI):
    TEMP_IMAGE_ID = 'TEMP_IMAGE_ID'

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        self.context = context
        self._logger = context.logger('virtual-desktop-api')
        self.events_utils: EventsUtils = EventsUtils(context=self.context)
        self.controller_utils: VirtualDesktopControllerUtils = VirtualDesktopControllerUtils(context=self.context)
        self.software_stack_db: VirtualDesktopSoftwareStackDB = VirtualDesktopSoftwareStackDB(context=self.context)
        self.server_db: VirtualDesktopServerDB = VirtualDesktopServerDB(context=self.context)
        self.schedule_db: VirtualDesktopScheduleDB = VirtualDesktopScheduleDB(context=self.context)
        self.permission_profile_db: VirtualDesktopPermissionProfileDB = VirtualDesktopPermissionProfileDB(context=self.context)
        self.session_db: VirtualDesktopSessionDB = VirtualDesktopSessionDB(
            context=self.context,
            server_db=self.server_db,
            software_stack_db=self.software_stack_db,
            schedule_db=self.schedule_db)
        self.ssm_commands_db: VirtualDesktopSSMCommandsDB = VirtualDesktopSSMCommandsDB(context=self.context)
        self.session_permissions_db: VirtualDesktopSessionPermissionDB = VirtualDesktopSessionPermissionDB(self.context)

        self.software_stack_utils: VirtualDesktopSoftwareStackUtils = VirtualDesktopSoftwareStackUtils(context=self.context, db=self.software_stack_db)
        self.server_utils: VirtualDesktopServerUtils = VirtualDesktopServerUtils(context=self.context, db=self.server_db)
        self.schedule_utils: VirtualDesktopScheduleUtils = VirtualDesktopScheduleUtils(context=self.context, db=self.schedule_db)
        self.ssm_commands_utils: VirtualDesktopSSMCommandsUtils = VirtualDesktopSSMCommandsUtils(context=self.context, db=self.ssm_commands_db)
        self.session_permissions_utils: VirtualDesktopSessionPermissionUtils = VirtualDesktopSessionPermissionUtils(
            context=context,
            db=self.session_permissions_db,
            permission_profile_db=self.permission_profile_db
        )
        self.session_utils: VirtualDesktopSessionUtils = VirtualDesktopSessionUtils(
            context=self.context,
            db=self.session_db,
            session_permission_db=self.session_permissions_db,
            permission_profile_db=self.permission_profile_db
        )

        self.DEFAULT_ROOT_VOL_IOPS = '100'
        self.arn_builder = ArnBuilder(self.context.config())

    def get_session_if_owner(self, username: str, idea_session_id: str) -> Optional[VirtualDesktopSession]:
        return self.session_db.get_from_db(idea_session_id=idea_session_id, idea_session_owner=username)

    @staticmethod
    def _validate_actors_for_session_permission_requests(session_permissions: List[VirtualDesktopSessionPermission]) -> (bool, str):
        if Utils.is_empty(session_permissions):
            return False, 'Invalid session_permissions'

        actors_seen = set()
        duplicate_actors = set()
        is_valid = True
        for session_permission in session_permissions:
            if session_permission.actor_name not in actors_seen:
                actors_seen.add(session_permission.actor_name)
            else:
                duplicate_actors.add(session_permission.actor_name)
                is_valid = False

        message = ''
        if not is_valid:
            message = f'actors: {duplicate_actors} not unique'
        return is_valid, message

    def _validate_session_for_session_permission_request(self, session: VirtualDesktopSession) -> (bool, str):
        if Utils.is_empty(session):
            return False, 'Invalid session'

        if session.base_os == VirtualDesktopBaseOS.WINDOWS and not self.controller_utils.is_active_directory():
            return False, 'Windows sessions do not support sessions permissions for OpenLDAP'
        return True, ''

    @staticmethod
    def _validate_session_permission_update_request(permission: VirtualDesktopSessionPermission) -> (VirtualDesktopSession, bool):
        is_valid = True
        if Utils.is_empty(permission.idea_session_id):
            permission.failure_reason = 'missing res_session_id'
            is_valid = False
        return permission, is_valid

    def _validate_session_permission_create_request(self, permission: VirtualDesktopSessionPermission) -> (VirtualDesktopSession, bool):
        is_valid, message = self.validate_create_session_permission_request(permission)
        if not is_valid:
            permission.failure_reason = message

        return permission, is_valid

    def validate_update_session_permission_request(self, request: UpdateSessionPermissionRequest) -> (bool, UpdateSessionPermissionRequest):
        is_valid_request = True
        if Utils.is_not_empty(request.create):
            for permission in request.create:
                permission, is_valid = self._validate_session_permission_create_request(permission)
                if is_valid:
                    session = self.get_session_if_owner(username=permission.idea_session_owner, idea_session_id=permission.idea_session_id)
                    is_valid, message = self._validate_session_for_session_permission_request(session)
                    if not is_valid:
                        permission.failure_reason = message
                is_valid_request = is_valid_request and is_valid

        if Utils.is_not_empty(request.update):
            for permission in request.update:
                permission, is_valid = self._validate_session_permission_update_request(permission)
                if is_valid:
                    session = self.get_session_if_owner(username=permission.idea_session_owner, idea_session_id=permission.idea_session_id)
                    is_valid, message = self._validate_session_for_session_permission_request(session)
                    if not is_valid:
                        permission.failure_reason = message
                is_valid_request = is_valid_request and is_valid

        '''
        for permission in request.delete:
            pass
        '''

        if is_valid_request:
            is_valid, message = self._validate_actors_for_session_permission_requests(request.create + request.update + request.delete)
            is_valid_request = is_valid_request and is_valid

        if not is_valid_request:
            for permission in request.create:
                if Utils.is_empty(permission.failure_reason):
                    permission.failure_reason = 'Invalid request. Rejecting all permissions'
            for permission in request.update:
                if Utils.is_empty(permission.failure_reason):
                    permission.failure_reason = 'Invalid request. Rejecting all permissions'
            for permission in request.delete:
                if Utils.is_empty(permission.failure_reason):
                    permission.failure_reason = 'Invalid request. Rejecting all permissions'
        return is_valid_request, request

    @staticmethod
    def validate_create_session_permission_request(permission: VirtualDesktopSessionPermission) -> (bool, str):
        if Utils.is_empty(permission):
            return False, 'missing permission object'
        if Utils.is_empty(permission.idea_session_id):
            return False, 'missing res_session_id'
        if Utils.is_empty(permission.idea_session_owner):
            return False, 'missing res_session_owner'
        if Utils.is_empty(permission.idea_session_name):
            return False, 'missing res_session_name'
        if Utils.is_empty(permission.idea_session_instance_type):
            return False, 'missing res_session_instance_type'
        if Utils.is_empty(permission.idea_session_state):
            return False, 'missing res_session_state'
        if Utils.is_empty(permission.idea_session_base_os):
            return False, 'missing res_session_base_os'
        if Utils.is_empty(permission.idea_session_created_on):
            return False, 'missing res_session_created_on'
        if Utils.is_empty(permission.idea_session_type):
            return False, 'missing res_session_type'
        if Utils.is_empty(permission.permission_profile) or Utils.is_empty(permission.permission_profile.profile_id):
            return False, 'missing permission_profile.profile_id'
        if Utils.is_empty(permission.actor_type):
            return False, 'missing actor_type'
        if Utils.is_empty(permission.actor_name):
            return False, 'missing actor_name'
        if Utils.is_empty(permission.expiry_date):
            return False, 'missing expiry_date'
        return True, ''

    @staticmethod
    def validate_reboot_session_request(session: VirtualDesktopSession) -> bool:
        if Utils.is_empty(session):
            exceptions.invalid_params('missing session')

        if Utils.is_empty(session.idea_session_id):
            exceptions.invalid_params('missing session.res_session_id')
        return True

    @staticmethod
    def validate_stop_session_request(session: VirtualDesktopSession) -> bool:
        if Utils.is_empty(session):
            exceptions.invalid_params('missing session')

        if Utils.is_empty(session.idea_session_id):
            exceptions.invalid_params('missing session.res_session_id')
        return True

    @staticmethod
    def validate_get_session_info_request(session: VirtualDesktopSession) -> bool:
        if Utils.is_empty(session):
            exceptions.invalid_params('missing session')

        if Utils.is_empty(session.idea_session_id):
            exceptions.invalid_params('missing session.res_session_id')
        return True
    
    # Get a list of projects where the current user is linked
    def get_user_projects(self, username: str) -> List[Project]:
        return self.context.projects_client.get_user_projects(username=username)
    
    def validate_create_session_request(self, session: VirtualDesktopSession) -> (VirtualDesktopSession, bool):
        if Utils.is_empty(session.project) or Utils.is_empty(session.project.project_id):
            session.failure_reason = 'missing session.project.project_id'
            return session, False

        # validate if the user belongs to this project
        is_user_part_of_project = False
        user_projects = self.get_user_projects(username=session.owner)
        for project in user_projects:
            if project.project_id == session.project.project_id:
                is_user_part_of_project = True
                session.project = project
                break

        if not is_user_part_of_project:
            session.failure_reason = f'User {session.owner} does not belong in the selected project.'
            return session, False

        # Validate Software Stack Object
        if Utils.is_empty(session.software_stack):
            session.failure_reason = 'missing session.software_stack'
            return session, False

        # Missing information in Software Stack
        if Utils.is_empty(session.software_stack.stack_id) or Utils.is_empty(session.software_stack.base_os):
            session.failure_reason = 'missing session.software_stack.stack_id and/or session.software_stack.base_os'
            return session, False

        software_stack = self.software_stack_db.get(stack_id=session.software_stack.stack_id, base_os=session.software_stack.base_os)
        if Utils.is_empty(software_stack):
            session.failure_reason = f'Invalid session.software_stack.stack_id: {session.software_stack.stack_id} and/or session.software_stack.base_os: {session.software_stack.base_os}'
            return session, False

        # validate software stack part of the same project
        is_software_stack_part_of_project = False
        for project in software_stack.projects:
            if project.project_id == session.project.project_id:
                is_software_stack_part_of_project = True
                break

        if not is_software_stack_part_of_project:
            session.failure_reason = f'session.software_stack.stack_id: {session.software_stack.stack_id} is not part of session.project.project_id: {session.project.project_id}'
            return session, False

        # Check the Project budget if we are enabled for budget enforcement
        if self.context.config().get_bool('vdc.controller.enforce_project_budgets', default=True):
            self._logger.info(f"eVDI Project budgets is enabled. Checking budgets.")

            if not session.project.is_budgets_enabled():
                self._logger.info(f"Project budget disabled or not configured for {session.project.name}")
            else:
                project_budget_name = Utils.get_as_string(session.project.budget.budget_name, default=None)

                if project_budget_name:
                    self._logger.debug(f"Found Budget name: {project_budget_name}")
                    project_budget = self.context.aws_util().budgets_get_budget(budget_name=project_budget_name)

                    if Utils.is_not_empty(project_budget):
                        self._logger.debug(f"Budget details: {project_budget}")

                        if project_budget.actual_spend > project_budget.budget_limit:
                            self._logger.error(f"Budget exceeded. Denying session request")
                            session.failure_reason = f"Project {project_budget_name} budget has been exceeded. Unable to start session. Contact your Administrator."
                            return session, False

                        else:
                            self._logger.debug(f"Budget usage is acceptable. Proceeding")
        else:
            self._logger.info(f"VDI Project budgets are disabled (vdc.controller.enforce_project_budgets). Not checking budgets.")

        session.software_stack = software_stack

        # Validate hibernation value
        if Utils.is_empty(session.hibernation_enabled):
            session.failure_reason = 'missing session.hibernation_enabled'
            return session, False

        # Instance Type validation
        if Utils.is_empty(session.server) or Utils.is_empty(session.server.instance_type):
            session.failure_reason = 'missing session.server.instance_type'
            return session, False

        is_instance_type_valid = False
        allowed_instance_types = self.controller_utils.get_valid_instance_types(session.hibernation_enabled, session.software_stack)
        for allowed_instance_type in allowed_instance_types:
            is_instance_type_valid = session.server.instance_type == Utils.get_value_as_string('InstanceType', allowed_instance_type, '')
            if is_instance_type_valid:
                break

        if not is_instance_type_valid:
            session.failure_reason = f'Invalid session.server.instance_type: {session.server.instance_type}. Not allowed for current configuration'
            return session, False

        # Technical Validation for Hibernation.
        if session.hibernation_enabled and session.software_stack.base_os in {VirtualDesktopBaseOS.RHEL8, VirtualDesktopBaseOS.RHEL9}:
            session.failure_reason = f'OS {session.software_stack.base_os} does not support Instance Hibernation'
            return session, False
        elif session.hibernation_enabled and session.software_stack.base_os is VirtualDesktopBaseOS.WINDOWS:
            ram = self.controller_utils.get_instance_ram(session.server.instance_type).as_unit(SocaMemoryUnit.GiB)
            if ram.value > 16:
                session.failure_reason = f'OS {session.software_stack.base_os} does not support Instance Hibernation for instances with RAM greater than 16GiB.'
                return session, False
        else:
            # amazonlinux2 supports hibernation
            pass

        # Technical Validations for Session Type
        # // https://docs.aws.amazon.com/dcv/latest/adminguide/servers.html - AMD GPU, Windows support Console sessions only
        if session.type is VirtualDesktopSessionType.VIRTUAL and session.software_stack.base_os is VirtualDesktopBaseOS.WINDOWS:
            session.failure_reason = f'{session.software_stack.base_os} does not support Virtual Sessions'
            return session, False

        gpu_manufacturer = self.controller_utils.get_gpu_manufacturer(session.server.instance_type)
        if session.type is VirtualDesktopSessionType.VIRTUAL and gpu_manufacturer is VirtualDesktopGPU.AMD:
            session.failure_reason = f'Instance type: {session.server.instance_type} with GPU {gpu_manufacturer} does not support Virtual Sessions'
            return session, False

        architecture = self.controller_utils.get_architecture(session.server.instance_type)
        if session.type is VirtualDesktopSessionType.CONSOLE and architecture is VirtualDesktopArchitecture.ARM64:
            session.failure_reason = f'Instance type: {session.server.instance_type} does not support Console Sessions'
            return session, False

        # Validate Root Volume Size
        if Utils.is_empty(session.server) or Utils.is_empty(session.server.root_volume_size):
            session.failure_reason = 'missing session.server.root_volume_size'
            return session, False

        # Business Validation for MAX Root Volume
        max_root_volume_size = self.context.config().get_int('virtual-desktop-controller.dcv_session.max_root_volume_memory', required=True)
        if session.server.root_volume_size > max_root_volume_size:
            session.failure_reason = f'root volume size: {session.server.root_volume_size} is greater than maximum allowed root volume size: {max_root_volume_size}GB.'
            return session, False

        # Technical Validation for Root Volume
        min_root_volume: SocaMemory = software_stack.min_storage
        if session.hibernation_enabled:
            min_root_volume = software_stack.min_storage + self.controller_utils.get_instance_ram(session.server.instance_type)

        if session.server.root_volume_size < min_root_volume:
            session.failure_reason = f'root volume size: {session.server.root_volume_size} is less than the minimum required root volume size: {min_root_volume} when hibernation is {"enabled" if session.hibernation_enabled else "disabled"}.'
            return session, False

        return session, True

    @staticmethod
    def validate_delete_session_request(session: VirtualDesktopSession) -> (VirtualDesktopSession, bool):
        is_valid = True
        if Utils.is_empty(session.idea_session_id):
            session.failure_reason = "missing session.res_session_id"
            is_valid = False

        return session, is_valid

    @staticmethod
    def complete_delete_session_request(session: VirtualDesktopSession, context: ApiInvocationContext) -> VirtualDesktopSession:
        if Utils.is_empty(session.owner):
            session.owner = context.get_username()

        return session

    def _get_software_stack_info(self, software_stack_id: str, software_stack_base_os: str) -> VirtualDesktopSoftwareStack:
        software_stack_response = self.software_stack_db.get_with_project_info(stack_id=software_stack_id, base_os=software_stack_base_os)
        if Utils.is_empty(software_stack_response):
            software_stack = VirtualDesktopSoftwareStack(
                stack_id=software_stack_id,
                failure_reason=f'invalid stack_id: {software_stack_id}'
            )
        else:
            software_stack = software_stack_response
        return software_stack

    @staticmethod
    def validate_resume_session_request(session: VirtualDesktopSession) -> (VirtualDesktopSession, bool):
        if Utils.is_empty(session.idea_session_id):
            session.failure_reason = "missing session.res_session_id"
            return session, False
        return session, True

    @staticmethod
    def validate_create_software_stack_request(software_stack: VirtualDesktopSoftwareStack) -> (VirtualDesktopSoftwareStack, bool):
        if Utils.is_empty(software_stack):
            software_stack = VirtualDesktopSoftwareStack()
            software_stack.failure_reason = 'missing software_stack'
            return software_stack, False

        if Utils.is_empty(software_stack.min_storage):
            software_stack.failure_reason = 'missing software_stack.min_storage'
            return software_stack, False

        if Utils.is_empty(software_stack.name):
            software_stack.failure_reason = 'missing software_stack.name'
            return software_stack, False

        return software_stack, True

    @staticmethod
    def validate_get_connection_info_request(connection_info: VirtualDesktopSessionConnectionInfo) -> (str, bool):
        if Utils.is_not_empty(connection_info.dcv_session_id):
            return '', True

        if Utils.is_not_empty(connection_info.idea_session_owner) and Utils.is_not_empty(connection_info.idea_session_id):
            return '', True

        return 'Need to provide either (res_session_id and res_session_owner) or dcv_session_id', False

    @staticmethod
    def validate_get_session_screenshot_request(screenshot: VirtualDesktopSessionScreenshot) -> (VirtualDesktopSessionScreenshot, bool):
        if Utils.is_empty(screenshot.idea_session_id) and Utils.is_empty(screenshot.dcv_session_id):
            screenshot.failure_reason = 'Provide either res_session_id or dcv_session_id'
            return screenshot, False
        return screenshot, True

    @staticmethod
    def complete_get_session_info_request(session: VirtualDesktopSession, context: ApiInvocationContext) -> VirtualDesktopSession:
        if Utils.is_empty(session.owner):
            session.owner = context.get_username()
        return session

    @staticmethod
    def complete_get_session_screenshots_request(screenshots: List[VirtualDesktopSessionScreenshot], context: ApiInvocationContext) -> List[VirtualDesktopSessionScreenshot]:
        for screenshot in screenshots:
            if Utils.is_empty(screenshot.idea_session_owner):
                screenshot.idea_session_owner = context.get_username()
        return screenshots

    @staticmethod
    def complete_resume_session_request(session: VirtualDesktopSession, context: ApiInvocationContext):
        if Utils.is_empty(session.owner):
            session.owner = context.get_username()

    @staticmethod
    def complete_reboot_session_request(session: VirtualDesktopSession, context: ApiInvocationContext):
        if Utils.is_empty(session.owner):
            session.owner = context.get_username()

    @staticmethod
    def complete_stop_session_request(session: VirtualDesktopSession, context: ApiInvocationContext):
        if Utils.is_empty(session.owner):
            session.owner = context.get_username()

    @staticmethod
    def complete_update_session_request(session: VirtualDesktopSession, context: ApiInvocationContext):
        if Utils.is_empty(session.owner):
            session.owner = context.get_username()

    def complete_create_session_request(self, session: VirtualDesktopSession, context: ApiInvocationContext) -> VirtualDesktopSession:
        if Utils.is_empty(session.name):
            session.name = Utils.uuid()

        gpu_manufacturer = self.controller_utils.get_gpu_manufacturer(session.server.instance_type)
        if Utils.is_empty(session.type):
            if session.software_stack.base_os is VirtualDesktopBaseOS.WINDOWS or gpu_manufacturer is VirtualDesktopGPU.AMD:
                session.type = VirtualDesktopSessionType.CONSOLE
            else:
                session.type = VirtualDesktopSessionType.VIRTUAL

        if Utils.is_empty(session.owner):
            session.owner = context.get_username()

        if Utils.is_empty(session.server):
            session.server = VirtualDesktopServer()

        if Utils.is_empty(session.server.root_volume_iops):
            session.server.root_volume_iops = self.DEFAULT_ROOT_VOL_IOPS

        if Utils.is_empty(session.server.instance_profile_arn):
            if Utils.is_empty(session.project.policy_arns):
                session.server.instance_profile_arn = self.context.config().get_string(
                    'virtual-desktop-controller.dcv_host_instance_profile_arn', required=True)
            else:
                session.server.instance_profile_arn = self.arn_builder.get_vdi_iam_instance_profile_arn(project_name=session.project.name)

            # self.default_instance_profile_arn = self.context.app_config.virtual_desktop_dcv_host_profile_arn
            # self.default_security_group = self.context.app_config.virtual_desktop_dcv_host_security_group_id

        if Utils.is_empty(session.server.key_pair_name):
            session.server.key_pair_name = self.context.config().get_string('cluster.network.ssh_key_pair', required=True)

        if Utils.is_empty(session.server.security_groups):
            session.server.security_groups = []

        security_group_ids = set()
        security_group_ids.update(session.server.security_groups)
        security_group_ids.add(self.context.config().get_string('virtual-desktop-controller.dcv_host_security_group_id', required=True))
        additional_security_groups = self.context.config().get_list('virtual-desktop-controller.dcv_session.additional_security_groups', default=[])
        security_group_ids.update(additional_security_groups)
        if Utils.is_not_empty(session.project.security_groups):
            security_group_ids.update(session.project.security_groups)
        session.server.security_groups = list(security_group_ids)
        session.idea_session_id = Utils.uuid()

        return session

    def _get_session_screenshots(self, screenshots: List[VirtualDesktopSessionScreenshot]) -> (List[VirtualDesktopSessionScreenshot], List[VirtualDesktopSessionScreenshot]):
        if Utils.is_empty(screenshots):
            return [], []

        failed_requests = []
        valid_screenshots = []
        for screenshot in screenshots:
            if Utils.is_empty(screenshot.dcv_session_id):
                session = self.session_db.get_from_db(idea_session_owner=screenshot.idea_session_owner, idea_session_id=screenshot.idea_session_id)
                if Utils.is_empty(session):
                    screenshot.failure_reason = f'invalid RES session id: {screenshot.idea_session_id} for user: {screenshot.idea_session_owner}'
                    self._logger.error(screenshot.failure_reason)
                    failed_requests.append(screenshot)
                    continue

                if Utils.is_empty(session.dcv_session_id):
                    screenshot.failure_reason = f'DCV session does not yet exist for RES session id: {screenshot.idea_session_id} for user: {screenshot.idea_session_owner}'
                    self._logger.error(screenshot.failure_reason)
                    failed_requests.append(screenshot)
                    continue

                screenshot.dcv_session_id = session.dcv_session_id
                valid_screenshots.append(screenshot)
            else:
                valid_screenshots.append(screenshot)

        success_response, fail_response = self.context.dcv_broker_client.get_session_screenshots(valid_screenshots)
        fail_response.extend(failed_requests)
        return success_response, fail_response

    def _update_session(self, new_session: VirtualDesktopSession) -> VirtualDesktopSession:
        old_session = self.session_db.get_from_db(idea_session_id=new_session.idea_session_id, idea_session_owner=new_session.owner)

        if Utils.is_empty(old_session):
            new_session.failure_reason = f'invalid RES session id: {new_session.idea_session_id}:{new_session.name} or owner {new_session.owner}. Not updating the session.'
            self._logger.error(new_session.failure_reason)
            return new_session

        operation_failed = False
        is_session_updated = False
        is_server_updated = False

        if not operation_failed and Utils.is_not_empty(new_session.name) and new_session.name != old_session.name:
            is_session_updated = True
            old_session.name = new_session.name

        if not operation_failed and Utils.is_not_empty(new_session.description) and new_session.description != old_session.description:
            is_session_updated = True
            old_session.description = new_session.description

        if not operation_failed and Utils.is_not_empty(new_session.server) and Utils.is_not_empty(new_session.server.instance_type):
            old_server = self.server_db.get(instance_id=new_session.server.instance_id)
            if Utils.is_not_empty(old_server) and old_server.instance_type != new_session.server.instance_type:
                if old_session.hibernation_enabled:
                    error = f'Not allowed to change Instance type for session: {new_session.idea_session_id} because hibernation is enabled'
                    success = False
                else:
                    error, success = self.controller_utils.change_instance_type(instance_id=new_session.server.instance_id, instance_type_name=new_session.server.instance_type)

                if not success:
                    new_session.failure_reason = error
                    operation_failed = True
                else:
                    old_session.server.instance_type = new_session.server.instance_type
                    is_server_updated = True
                    is_session_updated = True

        if not operation_failed and Utils.is_not_empty(new_session.schedule):
            old_session = self.schedule_utils.update_schedule_for_session(new_session.schedule, old_session)
            is_session_updated = True

        if not operation_failed and is_server_updated:
            _ = self.server_db.update(old_session.server)

        if not operation_failed and is_session_updated:
            new_session = self.session_db.update(old_session)
            self.controller_utils.create_tag(new_session.server.instance_id, constants.IDEA_TAG_NAME, f'{self.context.cluster_name()}-{new_session.name}-{new_session.owner}')

        return new_session

    def _reboot_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        if Utils.is_empty(sessions):
            return [], []

        return self.session_utils.reboot_sessions(sessions)

    def _stop_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        if Utils.is_empty(sessions):
            return [], []

        return self.session_utils.stop_sessions(sessions)

    def _resume_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        if Utils.is_empty(sessions):
            return [], []

        return self.session_utils.resume_sessions(sessions)

    def _create_software_stack(self, software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        return self.software_stack_utils.create_software_stack(software_stack)

    def _create_software_stack_from_session(self, session: VirtualDesktopSession, new_software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        self._logger.info(f'creating new software for session: {session.idea_session_id}, owner: {session.owner}')
        new_software_stack, is_valid = self.validate_create_software_stack_request(new_software_stack)
        if not is_valid:
            self._logger.error(new_software_stack.failure_reason)
            return new_software_stack

        session = self.session_db.get_from_db(idea_session_id=session.idea_session_id, idea_session_owner=session.owner)
        if Utils.is_empty(session):
            new_software_stack = VirtualDesktopSoftwareStack(
                failure_reason=f'Failed to create Software Stack because of invalid RES Session {session.idea_session_id}:{session.name} for owner: {session.owner}'
            )
            self._logger.error(new_software_stack.failure_reason)
            return new_software_stack

        if session.base_os == VirtualDesktopBaseOS.WINDOWS:
            image_id = self.TEMP_IMAGE_ID
        else:
            response = self.controller_utils.create_image_for_instance_id(session.server.instance_id, new_software_stack.name, new_software_stack.description)
            image_id = Utils.get_value_as_string('ImageId', response, None)

            if Utils.is_empty(image_id):
                new_software_stack.failure_reason = f'Unable to create AMI for InstanceID: {session.server.instance_id} for some reason. Please contact Administrators.'
                self._logger.error(new_software_stack.failure_reason)
                return new_software_stack

        new_software_stack.base_os = VirtualDesktopBaseOS(session.base_os)
        new_software_stack.ami_id = image_id
        new_software_stack.architecture = session.software_stack.architecture
        new_software_stack.gpu = self.controller_utils.get_gpu_manufacturer(session.server.instance_type)
        new_software_stack.projects = [session.project]
        new_software_stack.min_ram = SocaMemory(
            value=self.controller_utils.get_instance_ram(session.server.instance_type).gb(),
            unit=SocaMemoryUnit.GB
        )
        new_software_stack = self._create_software_stack(new_software_stack)

        if session.base_os == VirtualDesktopBaseOS.WINDOWS:
            _ = self.ssm_commands_utils.submit_ssm_command_to_enable_userdata_execution_on_windows(
                instance_id=session.server.instance_id,
                idea_session_id=session.idea_session_id,
                idea_session_owner=session.owner,
                software_stack_id=new_software_stack.stack_id
            )
        else:
            self.events_utils.publish_validate_software_stack_creation_event(
                software_stack_id=new_software_stack.stack_id,
                base_os=new_software_stack.base_os,
                instance_id=session.server.instance_id,
                idea_session_id=session.idea_session_id,
                idea_session_owner=session.owner
            )

        session.locked = True
        session.server.locked = True
        _ = self.server_db.update(session.server)
        _ = self.session_db.update(session)

        return new_software_stack

    def _delete_software_stack(self, software_stack: VirtualDesktopSoftwareStack):
        self.software_stack_utils.delete_software_stack(software_stack)

    def _list_session_permissions(self, idea_session_id: str, request: ListPermissionsRequest) -> ListPermissionsResponse:
        session_filter_found = False
        if Utils.is_empty(request.filters):
            request.filters = []

        for listing_filter in request.filters:
            if listing_filter.key == SESSION_PERMISSIONS_FILTER_SESSION_ID_KEY:
                listing_filter.value = idea_session_id
                session_filter_found = True

        if not session_filter_found:
            request.add_filter(SocaFilter(
                key=SESSION_PERMISSIONS_FILTER_SESSION_ID_KEY,
                value=idea_session_id
            ))

        return self.session_permissions_db.list_session_permissions(request)

    def _list_shared_permissions(self, username: str, request: ListPermissionsRequest) -> ListPermissionsResponse:
        actor_filter_found = False
        if Utils.is_empty(request.filters):
            request.filters = []

        for listing_filter in request.filters:
            if listing_filter.key == SESSION_PERMISSIONS_FILTER_ACTOR_KEY:
                listing_filter.value = username
                actor_filter_found = True

        if not actor_filter_found:
            request.add_filter(SocaFilter(
                key=SESSION_PERMISSIONS_FILTER_ACTOR_KEY,
                value=username
            ))

        return self.session_permissions_db.list_session_permissions(request)

    def _list_software_stacks(self, request: ListSoftwareStackRequest) -> ListSoftwareStackResponse:
        return self.software_stack_db.list_all_from_db(request)

    def _get_session_connection_info(self, connection_info_request: VirtualDesktopSessionConnectionInfo, context: ApiInvocationContext) -> VirtualDesktopSessionConnectionInfo:
        connection_info = VirtualDesktopSessionConnectionInfo()

        is_valid_idea_session = True
        session = None

        if Utils.is_empty(connection_info_request.dcv_session_id):
            session = self.session_db.get_from_db(idea_session_id=connection_info_request.idea_session_id, idea_session_owner=connection_info_request.idea_session_owner)
            if Utils.is_empty(session):
                connection_info.failure_reason = f'Invalid RES session id: {connection_info_request.idea_session_id} for user: {context.get_username()}.'
                is_valid_idea_session = False
            elif VirtualDesktopSessionState[session.state] != VirtualDesktopSessionState.READY:
                connection_info.failure_reason = f'session {connection_info_request.idea_session_id} status is {session.state}'
                is_valid_idea_session = False
            else:
                connection_info_request.dcv_session_id = session.dcv_session_id

        if is_valid_idea_session:
            connection_info = self.context.dcv_broker_client.get_session_connection_data(dcv_session_id=connection_info_request.dcv_session_id, username=connection_info_request.username)
            if Utils.is_not_empty(connection_info.failure_reason):
                # Invalid connection
                self._logger.error(f'Error in getting connection info data for DCV Session: {connection_info_request.dcv_session_id}, Trying to switch to error state.')
                if Utils.is_empty(session) and Utils.is_not_empty(connection_info_request.idea_session_id):
                    self._logger.error(f'We have RES session ID {connection_info_request.idea_session_id}, using it to get session db entry...')
                    session = self.session_db.get_from_db(idea_session_id=connection_info_request.idea_session_id, idea_session_owner=connection_info_request.idea_session_owner)

                if Utils.is_not_empty(session):
                    # we had a valid session, but we were unable to connect because DCV Broker denied. Need to error the session out.
                    self._logger.error('Identified the DB entry, error-ing it out.')
                    session.state = VirtualDesktopSessionState.ERROR
                    _ = self.session_db.update(session)
            else:
                # Valid connection
                custom_certificate_provided = self.context.config().get_bool('virtual-desktop-controller.dcv_connection_gateway.certificate.provided', default=False)
                if custom_certificate_provided:
                    connection_info.endpoint = f'https://{self.context.config().get_string("virtual-desktop-controller.dcv_connection_gateway.certificate.custom_dns_name", required=True)}'
                else:
                    connection_info.endpoint = f'https://{self.context.config().get_string("virtual-desktop-controller.external_nlb.load_balancer_dns_name", required=True)}'

        return connection_info

    @abstractmethod
    def invoke(self, context: ApiInvocationContext):
        ...
