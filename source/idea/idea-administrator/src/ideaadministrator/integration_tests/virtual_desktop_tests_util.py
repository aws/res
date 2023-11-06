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
from enum import Enum
import ideaadministrator
from ideasdk.utils import Utils
from ideadatamodel import (
    VirtualDesktopBaseOS,
    Project,
    VirtualDesktopSession,
    VirtualDesktopSoftwareStack,
    VirtualDesktopServer,
    SocaMemory,
    SocaMemoryUnit,
    VirtualDesktopSessionScreenshot,
    VirtualDesktopGPU,
    VirtualDesktopSessionConnectionInfo,
    VirtualDesktopSessionPermission,
    GetSessionScreenshotRequest,
    GetSessionScreenshotResponse,
    CreateSoftwareStackResponse,
    CreateSoftwareStackRequest,
    UpdateSoftwareStackRequest,
    UpdateSoftwareStackResponse,
    UpdateSessionPermissionRequest,
    UpdateSessionPermissionResponse,
    CreateSoftwareStackFromSessionRequest,
    CreateSoftwareStackFromSessionResponse,
    UpdateSessionRequest,
    UpdateSessionResponse,
    StopSessionRequest,
    StopSessionResponse,
    ResumeSessionsRequest,
    ResumeSessionsResponse,
    RebootSessionRequest,
    RebootSessionResponse,
    DeleteSessionRequest,
    DeleteSessionResponse,
    GetSoftwareStackInfoRequest,
    GetSoftwareStackInfoResponse,
    GetSessionConnectionInfoRequest,
    GetSessionConnectionInfoResponse,
    ListPermissionsRequest,
    ListPermissionsResponse,
    ListAllowedInstanceTypesForSessionRequest,
    ListAllowedInstanceTypesForSessionResponse,
    VirtualDesktopSessionState,
    VirtualDesktopPermissionProfile,
    VirtualDesktopPermission,
    CreatePermissionProfileRequest,
    CreatePermissionProfileResponse,
    UpdatePermissionProfileRequest,
    UpdatePermissionProfileResponse,
    ListSoftwareStackRequest,
    ListSoftwareStackResponse,
    ListSessionsRequest,
    ListSessionsResponse,
    ReIndexUserSessionsRequest,
    ReIndexUserSessionsResponse,
    ReIndexSoftwareStacksRequest,
    ReIndexSoftwareStacksResponse,
    ListSupportedOSRequest,
    ListSupportedOSResponse,
    ListSupportedGPURequest,
    ListSupportedGPUResponse,
    ListScheduleTypesRequest,
    ListScheduleTypesResponse,
    ListAllowedInstanceTypesRequest,
    ListAllowedInstanceTypesResponse,
    ListPermissionProfilesRequest,
    ListPermissionProfilesResponse,
    GetPermissionProfileRequest,
    GetPermissionProfileResponse,
    GetBasePermissionsRequest,
    GetBasePermissionsResponse,
    DescribeServersRequest,
    DescribeServersResponse,
    DescribeSessionsRequest,
    DescribeSessionsResponse,
    GetUserProjectsRequest,
    GetUserProjectsResult,
    BatchCreateSessionRequest,
    CreateSessionRequest,
    GetSessionInfoRequest
)
from ideaadministrator.integration_tests.test_context import TestContext
import time
from defusedxml import cElementTree
from defusedxml.ElementTree import parse
from ideadatamodel import (
    exceptions
)

import os
from typing import Dict, List, Optional

__new_created_session__: VirtualDesktopSession = None
__new_software_stack__: VirtualDesktopSoftwareStack = None
__is_test_results_report_created__ = False
__vdc_test_results__ = {}


class VirtualDesktopSessionTestcases(str, Enum):
    CREATE_SESSION = 'CREATE'
    STOP_SESSION = 'STOP'
    RESUME_SESSION = 'RESUME'
    REBOOT_SESSION = 'REBOOT'
    DELETE_SESSION = 'DELETE'


class VirtualDesktopSessionTestResults(str, Enum):
    PASS = 'PASS'
    FAILED = 'FAIL'
    SKIP = 'SKIP'


class SessionsTestResultMap:
    def __init__(self, test_case_name: str):
        self.__test_case_name = test_case_name
        self.test_results: List = []
        self.__test_results_map = {}

    def update_test_result_map(self, test_case_status: str, test_case_error_message: str = ''):
        self.__test_results_map['test_case_name'] = self.__test_case_name
        self.__test_results_map['test_case_status'] = test_case_status
        self.__test_results_map['test_case_error_message'] = test_case_error_message
        self.test_results.append(self.__test_results_map)

    def get_test_results(self) -> [Dict]:
        return self.test_results


class TestReportHelper:
    def __init__(self, context: TestContext, test_case_id: str, test_results_file):
        self.context = context
        self.test_case_id = test_case_id
        self.test_results_file = test_results_file

    def create_test_suites_element(self) -> cElementTree:
        """Create a <test_suites> </test_suites> element in test results file"""
        test_suites = cElementTree.Element('testsuites', name='Test_Run' + self.context.test_run_id)
        return test_suites

    def create_test_suite_element(self, test_suites) -> cElementTree:
        """Create a <test_suit></test_suite> element in test results file """
        test_results_summary = _get_test_summary_for_testsuite(self.test_case_id)
        test_suite = cElementTree.SubElement(test_suites, 'testsuite', name=self.test_case_id, tests=test_results_summary['total_tests'], failures=test_results_summary['total_tests_failed'], skips=test_results_summary['total_tests_skipped'])
        return test_suite

    def create_test_cases_in_a_test_suite(self, test_cases_results: Dict, test_suite: cElementTree):
        """Create a <testcase></testcase> element in test results file """
        for test_info in test_cases_results[self.test_case_id]:
            test_case_name = test_info['test_case_name']
            test_case_status = test_info['test_case_status']
            test_case_error_message = test_info['test_case_error_message']
            test_case = cElementTree.SubElement(test_suite, 'testcase', name=test_case_name)
            if test_case_status == VirtualDesktopSessionTestResults.FAILED:
                cElementTree.SubElement(test_case, 'failure', message=test_case_error_message)

    def write_to_xml_file(self, test_report_tree: cElementTree):
        test_report_tree.write(self.test_results_file,
                               xml_declaration=True, encoding='utf-8',
                               method='xml')

    def parse_file_and_return_tree_element(self) -> cElementTree:
        test_result_tree = parse(self.test_results_file)
        return test_result_tree

    @staticmethod
    def append_test_suites_to_test_report_tree(test_result_tree: cElementTree):
        test_suites = test_result_tree.getroot()
        return test_suites


class SessionPayload:

    def __init__(self, context: TestContext, session_data: Dict, username: str, access_token: str):
        self.name = session_data.get('name')
        self.base_os = VirtualDesktopBaseOS(session_data.get('base_os'))
        self.software_stack_id = session_data.get('software_stack_id')
        self.hibernation_enabled = session_data.get('hibernation_enabled')
        self.instance_type = session_data.get('instance_type')
        self.value = session_data.get('storage_size')
        self.context = context
        self.project: Project
        self.username = username
        self.access_token = access_token

        projects_list = _get_user_projects_list(self.context, self.username, self.access_token)
        for project in projects_list:
            if 'default' in project.name:
                self.project = project

    def get_session_payload(self) -> List[VirtualDesktopSession]:
        try:
            session_payload = [VirtualDesktopSession(
                name=self.name, owner=self.username,
                software_stack=VirtualDesktopSoftwareStack(
                    base_os=self.base_os,
                    stack_id=self.software_stack_id,
                ), hibernation_enabled=self.hibernation_enabled,
                project=self.project,
                server=VirtualDesktopServer(
                    instance_type=self.instance_type,
                    root_volume_size=SocaMemory(
                        value=self.value,
                        unit=SocaMemoryUnit.GB
                    )
                ))]
            return session_payload
        except exceptions.SocaException as e:
            self.context.info(f'Failed to get Session payload.Error : {e}')


class SessionsTestHelper:

    def __init__(self, context: TestContext, session: VirtualDesktopSession, username: str, access_token: str):
        self.context = context
        self.session = session
        self.session_list: List[VirtualDesktopSession] = [self.session]
        self.prefix_text = 'TEST STATUS : '
        self.session_id = self.session.idea_session_id
        self.access_token = access_token
        self.ami_id = self.session.software_stack.ami_id
        self.stack_id = self.session.software_stack.stack_id
        self.image_type = self.session.type
        self.dcv_session_id = self.session.dcv_session_id
        self.idea_session_id = self.session.idea_session_id
        self.idea_session_owner = self.session.owner
        self.create_time = self.session.created_on.ctime()
        self.failure_reason = self.session.failure_reason
        self.projects_list: [Project]
        self.username = username

        self.projects_list = _get_user_projects_list(self.context, self.username, self.access_token)

    def _get_session_screenshot_payload(self) -> List[VirtualDesktopSessionScreenshot]:
        try:
            session_payload = [VirtualDesktopSessionScreenshot(
                image_type=self.image_type,
                dcv_session_id=self.dcv_session_id,
                idea_session_id=self.idea_session_id,
                idea_session_owner=self.idea_session_owner,
                create_time=self.create_time,
                failure_reason=self.failure_reason,
            )]
            return session_payload

        except exceptions.SocaException as e:
            self.context.info(f'Failed to get Session Screenshot payload. Error : {e}')

    def _get_session_software_stack_payload(self) -> VirtualDesktopSoftwareStack:
        software_stack_name = 'VDC_Tests'
        try:
            session_payload = VirtualDesktopSoftwareStack(base_os=VirtualDesktopBaseOS.WINDOWS,
                                                          ami_id=self.ami_id,
                                                          description="Integration Tests",
                                                          name=software_stack_name,
                                                          min_storage=SocaMemory(
                                                              value=10,
                                                              unit=SocaMemoryUnit.GB
                                                          ), min_ram=SocaMemory(value=2,
                                                                                unit=SocaMemoryUnit.GB),
                                                          gpu=VirtualDesktopGPU.NO_GPU,
                                                          failure_reason=self.failure_reason,
                                                          projects=self.projects_list
                                                          )
            return session_payload

        except exceptions.SocaException as e:
            self.context.info(f'Failed to get Software Stack Payload. Error : {e}')

    def _get_session_connection_info_payload(self) -> List[VirtualDesktopSessionConnectionInfo]:

        try:
            session_payload = [VirtualDesktopSessionConnectionInfo(
                dcv_session_id=self.dcv_session_id,
                idea_session_id=self.idea_session_id,
                idea_session_owner=self.idea_session_owner,
                failure_reason=self.failure_reason,
            )]
            return session_payload

        except exceptions.SocaException as e:
            self.context.info(f'Failed to get Session payload. Error : {e}')

    def _get_session_permission_payload(self) -> [VirtualDesktopSessionPermission]:
        permission_profile = VirtualDesktopPermissionProfile()
        try:
            session_permission_payload = [VirtualDesktopSessionPermission(
                actor_name='clusteradmin',
                idea_session_id=self.idea_session_id,
                idea_session_owner=self.session.owner,
                idea_session_name=self.session.name,
                idea_session_state=self.session.state,
                idea_session_base_os=self.session.base_os,
                idea_session_created_on=self.session.created_on,
                idea_session_hibernation_enabled=self.session.hibernation_enabled,
                permission_profile=permission_profile.get_permission('admin_profile'))]
            return session_permission_payload

        except exceptions.SocaException as e:
            self.context.error(f'Failed to get Session Permission payload. Error : {e}')

    def get_session_screenshot(self, namespace: str) -> GetSessionScreenshotResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=GetSessionScreenshotRequest(screenshots=self._get_session_screenshot_payload()),
                result_as=GetSessionScreenshotResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Get Session Screenshot. Error : {e}')

    def create_software_stack(self) -> CreateSoftwareStackResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopAdmin.CreateSoftwareStack',
                payload=CreateSoftwareStackRequest(software_stack=self._get_session_software_stack_payload()),
                result_as=CreateSoftwareStackResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Create Software Stack. Error : {e}')

    def update_software_stack(self, software_stack: VirtualDesktopSoftwareStack) -> UpdateSoftwareStackResponse:
        try:

            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopAdmin.UpdateSoftwareStack',
                payload=UpdateSoftwareStackRequest(software_stack=software_stack),
                result_as=UpdateSoftwareStackResponse,
                access_token=self.access_token)
            return response

        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Update Software Stack. Error : {e}')

    def update_session_permissions(self, namespace: str) -> UpdateSessionPermissionResponse:
        try:

            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=UpdateSessionPermissionRequest(create=self._get_session_permission_payload()),
                result_as=UpdateSessionPermissionResponse,
                access_token=self.access_token)
            return response

        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Update Session Permissions. Error : {e}')

    def create_software_stack_from_session(self) -> CreateSoftwareStackFromSessionResponse:
        try:
            software_stack_payload = self._get_session_software_stack_payload()
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopAdmin.CreateSoftwareStackFromSession',
                payload=CreateSoftwareStackFromSessionRequest(session=self.session, new_software_stack=software_stack_payload),
                result_as=CreateSoftwareStackFromSessionResponse,
                access_token=self.access_token)
            return response

        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Create Software Stack from Session. Error : {e}')

    def update_session(self, namespace: str) -> UpdateSessionResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=UpdateSessionRequest(session=self.session),
                result_as=UpdateSessionResponse,
                access_token=self.access_token)
            return response

        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Update Session.Session Name: {self.session.name} Error : {e}')

    def stop_sessions(self, namespace: str) -> StopSessionResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=StopSessionRequest(sessions=self.session_list),
                access_token=self.access_token)
            time.sleep(20)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Stop Session.Session Name: {self.session.name} Error : {e}')

    def resume_sessions(self, namespace: str) -> ResumeSessionsResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=ResumeSessionsRequest(sessions=self.session_list),
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Resume Sessions.Session Name: {self.session.name} Error : {e}')

    def reboot_sessions(self, namespace: str) -> RebootSessionResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=RebootSessionRequest(sessions=self.session_list),
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Reboot Sessions.Session Name: {self.session.name} Error : {e}')

    def delete_session(self, namespace: str) -> DeleteSessionResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=DeleteSessionRequest(sessions=self.session_list),
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Delete Session.Session Name: {self.session.name} Error : {e}')

    def get_session_info(self, namespace: str) -> VirtualDesktopSession:
        try:
            time.sleep(10)
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(namespace=namespace,
                                                                                                   payload=GetSessionInfoRequest(session=self.session),
                                                                                                   access_token=self.access_token)
            session_info: VirtualDesktopSession = VirtualDesktopSession(**response.session)
            return session_info
        except Exception as e:
            self.context.error(f'Failed to get Session Info. Session Name: {self.session.name} Error : {e}')

    def get_software_stack_info(self) -> GetSoftwareStackInfoResponse:
        try:
            time.sleep(10)
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(namespace='VirtualDesktopAdmin.GetSoftwareStackInfo',
                                                                                                   payload=GetSoftwareStackInfoRequest(stack_id=self.stack_id),
                                                                                                   access_token=self.access_token)
            return response
        except Exception as e:
            self.context.error(f'Failed to Get Software Stack Info. Error : {e}')

    def get_session_connection_info(self, namespace: str) -> GetSessionConnectionInfoResponse:
        try:
            connection_info = self._get_session_connection_info_payload()
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(namespace=namespace,
                                                                                                   payload=GetSessionConnectionInfoRequest(connection_info=connection_info[0]),
                                                                                                   result_as=GetSessionConnectionInfoResponse,
                                                                                                   access_token=self.access_token)
            return response
        except Exception as e:
            self.context.error(f'Failed to Get Session Connection Info. Error : {e}')

    def update_user_session(self) -> UpdateSessionResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopAdmin.UpdateUserSession',
                payload=UpdateSessionRequest(session=self.session),
                result_as=UpdateSessionResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Update User Session. Error : {e}')

    def list_session_permissions(self, namespace: str) -> ListPermissionsResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=ListPermissionsRequest(idea_session_id=self.idea_session_id, username=self.context.admin_username),
                result_as=ListPermissionsResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Session Permissions. Error : {e}')

    def list_shared_permissions(self, namespace: str) -> ListPermissionsResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=ListPermissionsRequest(idea_session_id=self.idea_session_id, username=self.context.admin_username),
                result_as=ListPermissionsResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Shared Permissions. Error : {e}')

    def list_allowed_instances_type_for_session(self) -> ListAllowedInstanceTypesForSessionResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopUtils.ListAllowedInstanceTypesForSession',
                payload=ListAllowedInstanceTypesForSessionRequest(session=self.session),
                result_as=ListAllowedInstanceTypesForSessionResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Allowed Instances Type for Session. Session Name: {self.session.name} Error : {e}')

    def wait_and_verify_session_state_matches(self, expected_state: VirtualDesktopSessionState, get_session_info_namespace: str) -> Dict:
        session_state = {'session_state_matches': bool, 'error_log': ''}
        sleep_timer = 30
        try:
            wait_counter = 0
            current_session = self.get_session_info(get_session_info_namespace)

            while current_session.state != expected_state and current_session.state != VirtualDesktopSessionState.ERROR:
                self.context.info(f'Session Status: Session Name {current_session.name} is in {current_session.state} State')
                time.sleep(sleep_timer)
                current_session = self.get_session_info(get_session_info_namespace)
                wait_counter += 1
                if wait_counter >= 40:
                    break
            current_session = self.get_session_info(get_session_info_namespace)

            if current_session.state == expected_state:
                session_state_log = f'Session Status: Session Name {current_session.name} is in {current_session.state} State'
                self.context.info(session_state_log)
                session_state.update({'session_state_matches': True, 'error_log': ''})
                return session_state

            session_state_log = f'Exceeded maximum wait time for State to change.Expected State {expected_state} and Current State is {current_session.state}'
            self.context.error(session_state_log)
            session_state.update({'session_state_matches': False, 'error_log': session_state_log})
            return session_state

        except Exception as e:
            session_state_log = f'Failed to verify session state. Error : {e}'
            self.context.error(session_state_log)
            session_state.update({'session_state_matches': False, 'error_log': session_state_log})


class VirtualDesktopApiHelper:

    def __init__(self, context: TestContext, access_token: str, username: str):
        self.context = context
        self.access_token = access_token
        projects_list = _get_user_projects_list(context, username, access_token)

        if projects_list is not None:
            for project in projects_list:
                if 'default' in project.name:
                    self.project = project

        self.project_id = self.project.project_id

    def _get_virtual_desktop_permission_payload(self) -> List[VirtualDesktopPermission]:
        try:
            permission_payload = [VirtualDesktopPermission(
                key='builtin',
                name='Built In',
                description='All features',
                enabled=False)]
            return permission_payload

        except exceptions.SocaException as e:
            self.context.error(f'Failed to get Virtual Desktop Permission Payload. Error : {e}')

    def _get_permission_profile_payload(self) -> VirtualDesktopPermissionProfile:
        test_profile = 'VDC_Test_Profile'

        try:
            session_payload = VirtualDesktopPermissionProfile(
                profile_id=test_profile,
                title=test_profile,
                description=test_profile,
                permissions=self._get_virtual_desktop_permission_payload()
            )
            return session_payload

        except exceptions.SocaException as e:
            self.context.error(f'Failed to Get Permission Profile Payload. Error : {e}')

    def create_permissions_profile(self) -> CreatePermissionProfileResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopAdmin.CreatePermissionProfile',
                payload=CreatePermissionProfileRequest(profile=self._get_permission_profile_payload()),
                result_as=CreatePermissionProfileResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Create Permissions Profile. Error : {e}')

    def update_permission_profile(self, namespace: str) -> UpdatePermissionProfileResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=UpdatePermissionProfileRequest(profile=self._get_permission_profile_payload()),
                result_as=UpdatePermissionProfileResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Update Permissions Profile. Error : {e}')

    def list_software_stacks(self, namespace: str) -> ListSoftwareStackResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=ListSoftwareStackRequest(
                    disabled_also=True,
                    project_id=self.project_id
                ),
                result_as=ListSoftwareStackResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Software Stack. Error : {e}')

    def list_sessions(self, namespace: str) -> ListSessionsResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace=namespace,
                payload=ListSessionsRequest(),
                result_as=ListSessionsResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Sessions. Error : {e}')

    def reindex_user_session(self) -> ReIndexUserSessionsResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopAdmin.ReIndexUserSessions',
                payload=ReIndexUserSessionsRequest(),
                result_as=ReIndexUserSessionsResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Reindex User Session. Error : {e}')

    def reindex_software_stacks(self) -> ReIndexSoftwareStacksResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopAdmin.ReIndexSoftwareStacks',
                payload=ReIndexSoftwareStacksRequest(),
                result_as=ReIndexSoftwareStacksResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Reindex Software Stacks. Error : {e}')

    # VDC Utils
    def list_supported_os(self) -> ListSupportedOSResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopUtils.ListSupportedOS',
                payload=ListSupportedOSRequest(),
                result_as=ListSupportedOSResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Supported OS. Error : {e}')

    def list_supported_gpu(self) -> ListSupportedGPUResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopUtils.ListSupportedGPU',
                payload=ListSupportedGPURequest(),
                result_as=ListSupportedGPUResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Supported GPU. Error : {e}')

    def list_schedule_types(self) -> ListScheduleTypesResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopUtils.ListScheduleTypes',
                payload=ListScheduleTypesRequest(),
                result_as=ListScheduleTypesResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Schedule Types. Error : {e}')

    def list_allowed_instance_types(self) -> ListAllowedInstanceTypesResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopUtils.ListAllowedInstanceTypes',
                payload=ListAllowedInstanceTypesRequest(),
                result_as=ListAllowedInstanceTypesResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Allowed Instances Types. Error : {e}')

    def list_permission_profiles(self) -> ListPermissionProfilesResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopUtils.ListPermissionProfiles',
                payload=ListPermissionProfilesRequest(),
                result_as=ListPermissionProfilesResponse,
                access_token=self.access_token
            )
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to List Permission Profiles. Error : {e}')

    def get_permission_profile(self) -> GetPermissionProfileResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopUtils.GetPermissionProfile',
                payload=GetPermissionProfileRequest(profile_id='observer_profile'),
                result_as=GetPermissionProfileResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Get Permission Profile. Error : {e}')

    def get_base_permissions(self) -> GetBasePermissionsResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopUtils.GetBasePermissions',
                payload=GetBasePermissionsRequest(),
                result_as=GetBasePermissionsResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Get Base Permissions. Error : {e}')

    # Virtual Desktop DCV
    def describe_servers(self) -> DescribeServersResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopDCV.DescribeServers',
                payload=DescribeServersRequest(),
                result_as=DescribeServersResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Describe Servers. Error : {e}')

    def describe_sessions(self) -> DescribeSessionsResponse:
        try:
            response = self.context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
                namespace='VirtualDesktopDCV.DescribeSessions',
                payload=DescribeSessionsRequest(),
                result_as=DescribeSessionsResponse,
                access_token=self.access_token)
            return response
        except (exceptions.SocaException, Exception) as e:
            self.context.error(f'Failed to Describe Sessions. Error : {e}')


class SessionWorkflow:
    def __init__(self, context: TestContext, session: VirtualDesktopSession, test_case_id: str, username: str, access_token: str, get_session_info_namespace: str):
        self.context = context
        self.session = session
        self.test_case_id = test_case_id
        self.access_token = access_token
        self.get_session_info_namespace = get_session_info_namespace
        self.username = username
        self.session_helper = SessionsTestHelper(self.context, self.session, self.username, self.access_token)

    def _test_stop_session(self, test_case_name: str, stop_session_namespace: str) -> [VirtualDesktopSessionTestResults, str]:
        test_results_list = []

        try:
            self._on_session_test_start(VirtualDesktopSessionTestcases.STOP_SESSION)
            session_status = self.session_helper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.READY, self.get_session_info_namespace)
            if session_status.get('session_state_matches'):
                stop_session_response = self.session_helper.stop_sessions(stop_session_namespace)
                if stop_session_response.success:
                    time.sleep(20)
                    self.session = self.session_helper.get_session_info(self.get_session_info_namespace)
                    session_status = self.session_helper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.STOPPED, self.get_session_info_namespace)
                    if session_status.get('session_state_matches'):
                        return self._on_session_test_pass(test_case_name, test_results_list, VirtualDesktopSessionTestcases.STOP_SESSION)
                else:
                    return self._on_session_response_failed(test_case_name, test_results_list, VirtualDesktopSessionTestcases.STOP_SESSION)

            return self._on_session_state_mismatch(test_case_name, test_results_list, session_status, VirtualDesktopSessionTestcases.STOP_SESSION)

        except (exceptions.SocaException, Exception) as error:
            return self._on_session_in_exception(test_case_name, test_results_list, error, VirtualDesktopSessionTestcases.STOP_SESSION)

    def _test_resume_session(self, test_case_name: str, stop_session_namespace: str, resume_session_namespace: str) -> [VirtualDesktopSessionTestResults, str]:
        test_results_list = []
        sleep_timer = 30
        try:
            self._on_session_test_start(VirtualDesktopSessionTestcases.RESUME_SESSION)
            self.session = self.session_helper.get_session_info(self.get_session_info_namespace)

            if self.session.state != VirtualDesktopSessionState.STOPPED:
                self.session_helper.stop_sessions(stop_session_namespace)

            self.session = self.session_helper.get_session_info(self.get_session_info_namespace)
            session_status = self.session_helper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.STOPPED, self.get_session_info_namespace)

            if session_status.get('session_state_matches'):
                self.context.info(self.session_helper.prefix_text + f'Initiating {VirtualDesktopSessionTestcases.RESUME_SESSION} test for {self.session.name}')

                resume_session_response = self.session_helper.resume_sessions(resume_session_namespace)
                time.sleep(sleep_timer)

                if resume_session_response.success:
                    self.session = self.session_helper.get_session_info(self.get_session_info_namespace)
                    session_status = self.session_helper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.READY, self.get_session_info_namespace)

                    if session_status.get('session_state_matches'):
                        return self._on_session_test_pass(test_case_name, test_results_list, VirtualDesktopSessionTestcases.RESUME_SESSION)

            else:
                return self._on_session_state_mismatch(test_case_name, test_results_list, session_status, VirtualDesktopSessionTestcases.RESUME_SESSION)

            return self._on_session_response_failed(test_case_name, test_results_list, VirtualDesktopSessionTestcases.RESUME_SESSION)

        except exceptions.SocaException as error:
            return self._on_session_in_exception(test_case_name, test_results_list, error, VirtualDesktopSessionTestcases.RESUME_SESSION)

    def _test_reboot_session(self, test_case_name: str, reboot_session_namespace: str) -> [VirtualDesktopSessionTestResults, str]:
        test_results_list = []
        sleep_timer = 10
        try:
            self._on_session_test_start(VirtualDesktopSessionTestcases.REBOOT_SESSION)
            session_status = self.session_helper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.READY, self.get_session_info_namespace)

            if session_status.get('session_state_matches'):
                reboot_session_response = self.session_helper.reboot_sessions(reboot_session_namespace)
                if reboot_session_response.success:
                    time.sleep(sleep_timer)

                    self.session = self.session_helper.get_session_info(self.get_session_info_namespace)
                    session_status = self.session_helper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.READY, self.get_session_info_namespace)

                    if session_status.get('session_state_matches'):
                        return self._on_session_test_pass(test_case_name, test_results_list, VirtualDesktopSessionTestcases.REBOOT_SESSION)
                else:
                    return self._on_session_response_failed(test_case_name, test_results_list, VirtualDesktopSessionTestcases.REBOOT_SESSION)

            return self._on_session_state_mismatch(test_case_name, test_results_list, session_status, VirtualDesktopSessionTestcases.REBOOT_SESSION)

        except exceptions.SocaException as error:
            return self._on_session_in_exception(test_case_name, test_results_list, error, VirtualDesktopSessionTestcases.REBOOT_SESSION)

    def _test_delete_session(self, test_case_name: str, delete_session_namespace: str) -> [VirtualDesktopSessionTestResults, str]:
        test_results_list = []
        try:
            self._on_session_test_start(VirtualDesktopSessionTestcases.DELETE_SESSION)
            session_status = self.session_helper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.READY, self.get_session_info_namespace)

            if session_status.get('session_state_matches'):
                delete_session_response = self.session_helper.delete_session(delete_session_namespace)
                if delete_session_response is not None:
                    return self._on_session_test_pass(test_case_name, test_results_list, VirtualDesktopSessionTestcases.DELETE_SESSION)
                else:
                    return self._on_session_response_failed(test_case_name, test_results_list, VirtualDesktopSessionTestcases.DELETE_SESSION)
            else:
                return self._on_session_state_mismatch(test_case_name, test_results_list, session_status, VirtualDesktopSessionTestcases.DELETE_SESSION)

        except exceptions.SocaException as error:
            return self._on_session_in_exception(test_case_name, test_results_list, error, VirtualDesktopSessionTestcases.DELETE_SESSION)

    def test_session_workflow(self, user_type: Optional = 'admin'):
        stop_session_namespace = 'VirtualDesktopAdmin.StopSessions'
        resume_session_namespace = 'VirtualDesktopAdmin.ResumeSessions'
        reboot_session_namespace = 'VirtualDesktopAdmin.RebootSessions'
        delete_session_namespace = 'VirtualDesktopAdmin.DeleteSessions'
        if user_type == 'user':
            stop_session_namespace = 'VirtualDesktop.StopSessions'
            resume_session_namespace = 'VirtualDesktop.ResumeSessions'
            reboot_session_namespace = 'VirtualDesktop.RebootSessions'
            delete_session_namespace = 'VirtualDesktop.DeleteSessions'

        session_tests_result: List = []

        test_case_results = {'test_case_name': '', 'test_case_status': '', 'test_case_error_message': ''}

        session_helper = SessionsTestHelper(self.context, self.session, self.username, self.access_token)
        session_response = session_helper.get_session_info(self.get_session_info_namespace)
        wait_counter = 0
        sleep_timer = 30

        try:
            while session_response.state not in VirtualDesktopSessionState.ERROR:
                session_response = session_helper.get_session_info(self.get_session_info_namespace)
                time.sleep(sleep_timer)
                self.context.info(f'SESSION STATUS : SESSION NAME {session_response.name} is in {session_response.state} STATE')
                self.context.info('-' * 80)
                session_response = session_helper.get_session_info(self.get_session_info_namespace)

                if session_response.state == VirtualDesktopSessionState.READY:
                    # Test 1 : Stop Session
                    time.sleep(sleep_timer)
                    test_case_results['test_case_name'] = f'Test {VirtualDesktopSessionTestcases.STOP_SESSION} Session for {self.session.name}'

                    stop_session_test_case_results = self._test_stop_session(test_case_results['test_case_name'], stop_session_namespace)
                    session_tests_result.append(stop_session_test_case_results)

                    # Test 2 : Resume Session
                    time.sleep(sleep_timer)
                    test_case_results['test_case_name'] = f'Test {VirtualDesktopSessionTestcases.RESUME_SESSION} Session for {self.session.name}'

                    resume_session_test_case_results = self._test_resume_session(test_case_results['test_case_name'], stop_session_namespace, resume_session_namespace)
                    session_tests_result.append(resume_session_test_case_results)

                    # Test 3 : Reboot Session
                    time.sleep(sleep_timer)
                    test_case_results['test_case_name'] = f'Test {VirtualDesktopSessionTestcases.REBOOT_SESSION} Session for {self.session.name}'

                    reboot_session_test_case_results = self._test_reboot_session(test_case_results['test_case_name'], reboot_session_namespace)
                    session_tests_result.append(reboot_session_test_case_results)

                    # Test 4 : Delete Session
                    time.sleep(sleep_timer)
                    test_case_results['test_case_name'] = f'Test {VirtualDesktopSessionTestcases.DELETE_SESSION} Session for {self.session.name}'

                    terminate_session_test_case_results = self._test_delete_session(test_case_results['test_case_name'], delete_session_namespace)
                    session_tests_result.append(terminate_session_test_case_results)
                    break
                wait_counter += 1
                time.sleep(sleep_timer)
                session_response = session_helper.get_session_info(self.get_session_info_namespace)

                if wait_counter >= 60:
                    testcase_error_message = f'TEST STATUS: Exceeded maximum wait time for State to change. Session Name {session_response.name} is in {session_response.state} State.Marking tests as Skip status'
                    self.context.error(testcase_error_message)
                    test_case_results['test_case_status'] = VirtualDesktopSessionTestResults.SKIP.value
                    test_case_results['test_case_error_message'] = testcase_error_message
                    session_tests_result.append(test_case_results)
                    break
                session_response = session_helper.get_session_info(self.get_session_info_namespace)

                if session_response.state == VirtualDesktopSessionState.ERROR:
                    testcase_error_message = f'TEST STATUS: Failed to execute tests. Session Name {session_response.name} is in {session_response.state} State.Marking tests as Skip status'
                    self.context.error(testcase_error_message)
                    test_case_results['test_case_status'] = VirtualDesktopSessionTestResults.SKIP.value
                    test_case_results['test_case_error_message'] = testcase_error_message
                    session_tests_result.append(test_case_results)

        except (exceptions.SocaException, Exception) as e:
            testcase_error_message = f'Failed to execute tests for {self.session.name}, Error:{e}'
            self.context.error(testcase_error_message)
            test_case_results['test_case_status'] = VirtualDesktopSessionTestResults.FAILED.value
            test_case_results['test_case_error_message'] = testcase_error_message
            session_tests_result.append(test_case_results)

        finally:
            _update_test_results(self.test_case_id, session_tests_result)
            _create_or_update_test_report_xml(self.context, self.test_case_id)

    def _on_session_test_start(self, test_type: VirtualDesktopSessionTestcases):
        self.context.info(self.session_helper.prefix_text + f'Initiating {test_type} test for {self.session.name}')

    def _on_session_test_pass(self, test_case_name: str, test_results_list: List, test_type: VirtualDesktopSessionTestcases):
        test_failure_reason = ''
        self.session = self.session_helper.get_session_info(self.get_session_info_namespace)
        self.context.info(self.session_helper.prefix_text + f'Completed {test_type} test for {self.session.name}')
        test_results_list.extend([VirtualDesktopSessionTestResults.PASS, test_failure_reason])
        return self._get_session_test_result(test_case_name, test_results_list, test_type)

    def _on_session_response_failed(self, test_case_name: str, test_results_list: List, test_type: VirtualDesktopSessionTestcases):
        test_failure_reason = f'{test_type} Response Status : Failed.'
        self.context.error(test_failure_reason)
        test_results_list.extend([VirtualDesktopSessionTestResults.FAILED, test_failure_reason])
        return self._get_session_test_result(test_case_name, test_results_list, test_type)

    def _on_session_state_mismatch(self, test_case_name: str, test_results_list: List, session_status: Dict, test_type: VirtualDesktopSessionTestcases):
        self.session = self.session_helper.get_session_info(self.get_session_info_namespace)
        test_failure_reason = self.session_helper.prefix_text + f'Failed to execute {test_type} test.Session Name : {self.session.name}, Session ID : {self.session.idea_session_id} is in invalid State : {self.session.state}. ' + session_status.get('error_log')
        self.context.error(test_failure_reason)
        test_results_list.extend([VirtualDesktopSessionTestResults.FAILED, test_failure_reason])
        return self._get_session_test_result(test_case_name, test_results_list, test_type)

    def _on_session_in_exception(self, test_case_name, test_results_list, error: exceptions.SocaException, test_type: VirtualDesktopSessionTestcases):
        self.session = self.session_helper.get_session_info(self.get_session_info_namespace)
        test_failure_reason = self.session_helper.prefix_text + f'Failed to execute Test {test_type}.Session Name : {self.session.name}, Session ID : {self.session.idea_session_id} - Error: {error}'
        self.context.error(test_failure_reason)
        test_results_list.extend([VirtualDesktopSessionTestResults.FAILED, test_failure_reason])
        return self._get_session_test_result(test_case_name, test_results_list, test_type)

    def _get_session_test_result(self, test_case_name: str, test_result_list: List, test_type: VirtualDesktopSessionTestcases) -> Dict:
        time.sleep(30)
        session_test_case_item = {'test_case_name': test_case_name, 'test_case_status': '', 'test_case_error_message': ''}

        if not test_result_list:
            test_case_error_message = self.context.error(f'Test Status : Test Results list is empty for session name {self.session.name}, testcase {test_type}. Marking test as Skip.')
            session_test_case_item['test_case_status'] = VirtualDesktopSessionTestResults.SKIP.value
            session_test_case_item['test_cases_error_message'] = test_case_error_message

        else:
            session_test_case_item['test_case_status'] = test_result_list[0]
            session_test_case_item['test_cases_error_message'] = test_result_list[1]

        return session_test_case_item


class VirtualDesktopTestHelper:

    def __init__(self, context: TestContext):
        self.context = context

    @staticmethod
    def set_new_session(session: VirtualDesktopSession):
        global __new_created_session__
        __new_created_session__ = session

    @staticmethod
    def set_new_software_stack(software_stack: VirtualDesktopSoftwareStack):
        global __new_software_stack__
        __new_software_stack__ = software_stack

    @staticmethod
    def is_new_session_created() -> bool:
        global __new_created_session__
        if __new_created_session__ is not None:
            return True
        return False

    @staticmethod
    def get_new_session() -> VirtualDesktopSession:
        global __new_created_session__
        return __new_created_session__

    @staticmethod
    def get_new_software_stack() -> VirtualDesktopSoftwareStack:
        global __new_software_stack__
        return __new_software_stack__

    def before_test(self, test_case_name):
        self.context.info(f'Test Status : Starting {test_case_name}')

    def on_test_pass(self, test_case_name, test_results_map: SessionsTestResultMap):
        self.context.info(f'{test_case_name} : PASS')
        testcase_error_message = ''
        test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.PASS, testcase_error_message)

    def on_test_fail(self, test_case_name, response, test_results_map: SessionsTestResultMap):
        self.context.error(f'{test_case_name} : FAILED')
        testcase_error_message = f'Failed : {test_case_name}. Response data: {response}'
        test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
        assert False

    def on_test_exception(self, test_case_name, error: exceptions.SocaException, test_results_map: SessionsTestResultMap):
        self.context.error(f'{test_case_name} : FAILED')
        test_case_error_message = f'Failed to Execute {test_case_name}.Error : {error}'
        test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, test_case_error_message)
        assert False

    def after_test(self, test_case_name, test_results_map: SessionsTestResultMap, test_case_id):
        _update_test_results(test_case_id, test_results_map.get_test_results())
        _create_or_update_test_report_xml(self.context, test_case_id)
        self.context.info(f'Test Status : Completed {test_case_name}')


def _read_session_test_case_config(context: TestContext):
    input_yml_file_name = 'session_test_cases.yml'
    try:
        resources_dir = ideaadministrator.props.resources_dir
        test_cases_file = os.path.join(resources_dir, 'integration_tests', input_yml_file_name)
        with open(test_cases_file, 'r') as f:
            return Utils.from_yaml(f.read())
    except (FileNotFoundError, Exception) as e:
        context.error(f'Failed to read file {input_yml_file_name}. Error : {e}')


def _get_user_projects_list(context: TestContext, username: str, access_token: str) -> List[Project]:
    try:
        list_projects_result = context.get_cluster_manager_client().invoke_alt(
            namespace='Projects.GetUserProjects',
            payload=GetUserProjectsRequest(username=username),
            result_as=GetUserProjectsResult,
            access_token=access_token
        )
        return list_projects_result.projects
    except exceptions.SocaException as e:
        context.error(f'Failed to Get User Projects List. Error : {e}')


def _update_test_results(test_case_id: str, test_cases_result: List[Dict]):
    global __vdc_test_results__
    for testcase_element in test_cases_result:
        if test_case_id not in testcase_element:
            __vdc_test_results__[test_case_id] = test_cases_result
        else:
            __vdc_test_results__[test_case_id].extend(test_cases_result)


def _get_test_summary_for_testsuite(test_case_id: str) -> Dict:
    """returns test run summary for each test suite"""

    global __vdc_test_results__
    test_results_summary = {'total_tests': '', 'total_tests_failed': '', 'total_tests_skipped': ''}
    total_tests = len(__vdc_test_results__[test_case_id])
    test_results_summary['total_tests'] = str(total_tests)
    total_tests_failed = 0
    total_tests_skipped = 0
    for test_info in __vdc_test_results__[test_case_id]:
        test_case_status = test_info['test_case_status']
        if test_case_status == VirtualDesktopSessionTestResults.FAILED:
            total_tests_failed += 1
        elif test_case_status == VirtualDesktopSessionTestResults.SKIP:
            total_tests_skipped += 1
    test_results_summary['total_tests_failed'] = str(total_tests_failed)
    test_results_summary['total_tests_skipped'] = str(total_tests_skipped)
    return test_results_summary


def _create_or_update_test_report_xml(context: TestContext, test_case_id: str):
    global __is_test_results_report_created__
    global __vdc_test_results__
    test_results_path = os.path.join(ideaadministrator.props.dev_mode_project_root_dir, 'integration-test-results', context.test_run_id)
    if not os.path.exists(test_results_path):
        os.makedirs(test_results_path)
    try:
        sessions_test_report = 'vdc_test_report.xml'
        test_results_file = os.path.join(test_results_path, sessions_test_report)

        test_report_helper = TestReportHelper(context, test_case_id, test_results_file)

        # Create New Test report
        if not __is_test_results_report_created__:
            # 1. Create <testsuites></testsuites>
            test_suites = test_report_helper.create_test_suites_element()

            # 2. Create <testsuite> </testsuite>
            test_suite = test_report_helper.create_test_suite_element(test_suites)

            # 3. Create <testcases></testcases> in <testsuite> element
            test_report_helper.create_test_cases_in_a_test_suite(__vdc_test_results__, test_suite)
            test_results_tree = cElementTree.ElementTree(test_suites)

            # 4. Write to Test report
            test_report_helper.write_to_xml_file(test_results_tree)
            __is_test_results_report_created__ = True

        # Update Existing Test Report
        else:
            # 1. Parse test results file
            test_results_tree = test_report_helper.parse_file_and_return_tree_element()

            # 2. Append <test suite> to existing <test_suites>
            test_suites = test_report_helper.append_test_suites_to_test_report_tree(test_results_tree)

            # 3. Create <testsuite> </testsuite>
            test_suite = test_report_helper.create_test_suite_element(test_suites)

            # 4. Create <testcases></testcases> in <testsuite> element
            test_report_helper.create_test_cases_in_a_test_suite(__vdc_test_results__, test_suite)

            # 5. Write to Test report
            test_report_helper.write_to_xml_file(test_results_tree)

    except Exception as e:
        context.error(f'Failed to create Test Results XML file {e}')


def get_sessions_test_cases_list(context: TestContext, username: str, access_token: str) -> List[VirtualDesktopSession]:
    try:
        session_test_data = _read_session_test_case_config(context)
        param_test_case_name = context.extra_params.get('session_test_cases')
        param_base_os = context.extra_params.get('base_os')
        sessions_test_cases_list = []

        # Create testcases list based on input parameter as base_os
        if param_base_os is not None:
            context.info(f'Creating testcases list for test case name : {param_base_os}')
            param_base_os_list = param_base_os.split(',')
            for session_values in session_test_data.values():
                for session_data in session_values:
                    session_data_base_os = session_data.get('base_os')
                    if session_data_base_os in param_base_os_list:
                        new_session_payload = SessionPayload(context, session_data, username, access_token)
                        sessions_test_cases_list.extend(new_session_payload.get_session_payload())

        # Create testcases list based on input parameter as testcase name
        if param_test_case_name is not None:
            context.info(f'Creating testcases list for test case name : {param_test_case_name}')
            param_test_case_name_list = param_test_case_name.split(',')
            for session_values in session_test_data.values():
                for session_data in session_values:
                    if session_data.get('name') in param_test_case_name_list:
                        new_session_payload = SessionPayload(context, session_data, username, access_token)
                        sessions_test_cases_list.extend(new_session_payload.get_session_payload())

        # Create all the default testcases
        else:
            context.info('Creating default testcases list')
            for session_values in session_test_data.values():
                for session_data in session_values:
                    new_session_payload = SessionPayload(context, session_data, username, access_token)
                    sessions_test_cases_list.extend(new_session_payload.get_session_payload())
        return sessions_test_cases_list
    except exceptions.SocaException as e:
        context.error(f'Failed to Get Sessions Testcases List.Error : {e}')


def create_batch_sessions(context: TestContext, sessions: List[VirtualDesktopSession]) -> List[VirtualDesktopSession]:
    try:
        created_sessions: List[VirtualDesktopSession] = []
        batch_create_session_response = context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
            namespace='VirtualDesktopAdmin.BatchCreateSessions',
            payload=BatchCreateSessionRequest(sessions=sessions),
            access_token=context.get_admin_access_token()
        )
        context.info(f'Test Status : Submitted {len(sessions)} session request(s).')

        if not batch_create_session_response.success:
            context.error(f'Failed to Create Batch Sessions. API response log :{batch_create_session_response}')
            assert False
        for session_response in batch_create_session_response.success:
            created_sessions.append(VirtualDesktopSession(**session_response))
        return created_sessions
    except exceptions.SocaException as e:
        context.error(f'Failed to Create Batch Sessions. Error : {e}')


def create_session(context: TestContext, session: VirtualDesktopSession, access_token: str, namespace: str) -> VirtualDesktopSession:
    try:
        context.info(f'Create Session Status : Initiating Create Session for {session.name}')
        session_response = context.get_virtual_desktop_controller_client(timeout=7200).invoke_alt(
            namespace=namespace,
            payload=CreateSessionRequest(session=session),
            access_token=access_token)
        session: VirtualDesktopSession = VirtualDesktopSession(**session_response.session)
        context.info(f'Create Session Status : Completed Create Session for {session.name}')
        return session
    except (exceptions.SocaException, Exception) as e:
        context.error(f'Failed to Create Session for {session.name}. Error : {e}')
