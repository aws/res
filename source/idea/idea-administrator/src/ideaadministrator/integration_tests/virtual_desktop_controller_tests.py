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

from ideaadministrator.integration_tests.virtual_desktop_tests_util import (
    get_sessions_test_cases_list,
    create_batch_sessions,
    create_session,
    SessionsTestResultMap,
    VirtualDesktopSessionTestResults,
    SessionsTestHelper,
    VirtualDesktopTestHelper,
    VirtualDesktopApiHelper,
    SessionWorkflow
)
from ideaadministrator.integration_tests import test_constants
from ideaadministrator.integration_tests.test_context import TestContext
import time
from ideadatamodel import (
    exceptions,
    VirtualDesktopSessionState
)


# VDC Admin Tests
def test_admin_batch_session_workflow(context: TestContext):
    try:
        testcase_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_BATCH_SESSION_WORKFLOW
        admin_access_token = context.get_admin_access_token()
        # 1. Get Sessions list from the testdata file
        sessions = get_sessions_test_cases_list(context, context.admin_username, admin_access_token)
        # 2. Create Batch Sessions
        batch_sessions = create_batch_sessions(context, sessions)
        # 3. Execute Tests
        for session in batch_sessions:
            admin_access_token = context.get_admin_access_token()
            session_workflow = SessionWorkflow(context, session, testcase_id, context.admin_username, admin_access_token, 'VirtualDesktopAdmin.GetSessionInfo')
            session_workflow.test_session_workflow()

    except exceptions.SocaException as e:
        context.error(f'Failed to execute test admin session workflow. Error Code : {e.error_code} Error: {e.message}')


def test_admin_create_session(context: TestContext):
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_CREATE_SESSION
    test_case_name = 'Test Admin Create Session'
    sleep_timer = 30
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        sessions = get_sessions_test_cases_list(context, context.admin_username, admin_access_token)

        new_session = create_session(context, sessions[6], admin_access_token, 'VirtualDesktop.CreateSession')
        sessionHelper = SessionsTestHelper(context, new_session, context.admin_username, admin_access_token)
        time.sleep(sleep_timer)
        session_status = sessionHelper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.READY, 'VirtualDesktopAdmin.GetSessionInfo')

        if session_status.get('session_state_matches'):
            vdc_test_helper.set_new_session(new_session)
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            session = sessionHelper.get_session_info('VirtualDesktopAdmin.GetSessionInfo')
            testcase_error_message = f'Failed to execute {test_case_name}.Session Name : {session.name}. Session is in invalid State : {session.state}. Session ID : {session.idea_session_id}' + session_status.get('error_log')
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            assert False

    except (exceptions.SocaException, Exception) as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_get_session_screenshot(context: TestContext):
    test_case_name = 'Test Admin Get Session Screenshot'
    test_results_map = SessionsTestResultMap(test_case_name)
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_GET_SESSION_SCREENSHOT
    admin_access_token = context.get_admin_access_token()
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.get_session_screenshot('VirtualDesktopAdmin.GetSessionScreenshot')

            if response.success is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_update_session(context: TestContext):
    test_case_name = 'Test Admin Update Session'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_UPDATE_SESSION
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.update_session('VirtualDesktopAdmin.UpdateSession')

            if response.session is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_get_session_info(context: TestContext):
    test_case_name = 'Test Admin Get Session Info'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_GET_SESSION_INFO
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.get_session_info('VirtualDesktopAdmin.GetSessionInfo')

            if response.base_os is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_get_software_stack_info(context: TestContext):
    test_case_name = 'Test Admin Get Software Stack Info'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_GET_SOFTWARE_STACK_INFO
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.get_software_stack_info()

            if response is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_get_session_connection_info(context: TestContext):
    test_case_name = 'Test Admin Get Session Connection Info'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_GET_SESSION_CONNECTION_INFO
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.get_session_connection_info('VirtualDesktopAdmin.GetSessionConnectionInfo')

            if response is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)

def test_admin_create_permission_profile(context: TestContext):
    test_case_name = 'Test Admin Create Permission Profile'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_CREATE_PERMISSION_PROFILE
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.create_permissions_profile()

        if response is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_update_permission_profile(context: TestContext):
    test_case_name = 'Test Admin Update Permission Profile'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_UPDATE_PERMISSION_PROFILE
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.update_permission_profile('VirtualDesktopAdmin.UpdatePermissionProfile')

        if response is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_list_session_permissions(context: TestContext):
    test_case_name = 'Test Admin List Session Permissions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_LIST_SESSION_PERMISSIONS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.list_session_permissions('VirtualDesktopAdmin.ListSessionPermissions')

            if response is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_list_shared_permissions(context: TestContext):
    test_case_name = 'Test Admin List Shared Permissions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_LIST_SHARED_PERMISSIONS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.list_shared_permissions('VirtualDesktopAdmin.ListSharedPermissions')

            if response is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_list_sessions(context: TestContext):
    test_case_name = 'Test Admin List Sessions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_LIST_SESSIONS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_sessions('VirtualDesktopAdmin.ListSessions')

        if response.listing is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_list_software_stacks(context: TestContext):
    test_case_name = 'Test Admin List Software Stacks'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_LIST_SOFTWARE_STACKS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_software_stacks('VirtualDesktopAdmin.ListSoftwareStacks')

        if response.listing is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_create_software_stack(context: TestContext):
    test_case_name = 'Test Admin Create Software Stack'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_CREATE_SOFTWARE_STACK
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.create_software_stack()

            if response.software_stack is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)
                vdc_test_helper.set_new_software_stack(response.software_stack)
            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_create_software_stack_from_session(context: TestContext):
    test_case_name = 'Test Admin Create Software Stack from Session'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_CREATE_SOFTWARE_STACK_FROM_SESSION
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.create_software_stack_from_session()

            if response.software_stack is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)
                vdc_test_helper.set_new_software_stack(response.software_stack)
            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_update_software_stack(context: TestContext):
    test_case_name = 'Test Admin Update Software Stack'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_UPDATE_SOFTWARE_STACK
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.update_software_stack(vdc_test_helper.get_new_software_stack())

            if response.software_stack is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)
            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_update_session_permissions(context: TestContext):
    test_case_name = 'Test Admin Update Session Permission'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_UPDATE_SESSION_PERMISSIONS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.update_session_permissions('VirtualDesktopAdmin.UpdateSessionPermissions')

            if response.permissions is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)
            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


# VDC Utils Tests
def test_list_supported_os(context: TestContext):
    test_case_name = 'Test Supported OS'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_LIST_SUPPORTED_OS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_supported_os()

        if response.listing is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_list_supported_gpu(context: TestContext):
    test_case_name = 'Test List Supported GPU'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_LIST_SUPPORTED_GPU
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_supported_gpu()

        if response.listing is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)
        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_list_schedule_types(context: TestContext):
    test_case_name = 'Test List Schedule Types'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_LIST_SCHEDULE_TYPES
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_schedule_types()

        if response.listing is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)
        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_list_allowed_instance_types(context: TestContext):
    test_case_name = 'Test List Allowed Instance Types'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_LIST_ALLOWED_INSTANCE_TYPES
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_allowed_instance_types()

        if response.listing is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)
        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_list_allowed_instance_types_for_session(context: TestContext):
    test_case_name = 'Test List Allowed Instance Types for Session'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_LIST_ALLOWED_INSTANCE_TYPES_FOR_SESSION
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.list_allowed_instances_type_for_session()

            if response.listing is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)
            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_list_permission_profiles(context: TestContext):
    test_case_name = 'Test List Permission Profiles'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_LIST_PERMISSION_PROFILES
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_permission_profiles()

        if response.listing is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)
        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_get_permission_profile(context: TestContext):
    test_case_name = 'Test Get Permission Profile'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_GET_PERMISSION_PROFILE
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.get_permission_profile()

        if response is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)
        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_get_base_permissions(context: TestContext):
    test_case_name = 'Test Get Base Permissions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_GET_BASE_PERMISSIONS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.get_base_permissions()

        if response is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)
        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


# DCV Tests
def test_describe_servers(context: TestContext):
    test_case_name = 'Test Describe Servers'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_DESCRIBE_SERVERS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.describe_servers()

        if response is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)
        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_describe_sessions(context: TestContext):
    test_case_name = 'Test Describe Sessions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_DESCRIBE_SESSIONS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_api_helper = VirtualDesktopApiHelper(context, admin_access_token, context.admin_username)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.describe_sessions()

        if response is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)
        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_delete_software_stack(context: TestContext):
    test_case_name = 'Test Admin Delete Software Stack'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_DELETE_SOFTWARE_STACK
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.delete_software_stack(vdc_test_helper.get_new_software_stack())

            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_admin_delete_sessions(context: TestContext):
    test_case_name = 'Test Admin Delete Sessions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_DELETE_SESSIONS
    admin_access_token = context.get_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.admin_username, admin_access_token)
            response = session_helper.delete_session('VirtualDesktopAdmin.DeleteSessions')

            if response.success:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


# User tests

def test_user_create_session(context: TestContext):
    namespace = 'VirtualDesktop.CreateSession'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_CREATE_SESSION
    test_case_name = 'Test User Create Session'
    sleep_timer = 30
    user_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        sessions = get_sessions_test_cases_list(context, context.non_admin_username, user_access_token)

        new_session = create_session(context, sessions[7], user_access_token, namespace)

        sessionHelper = SessionsTestHelper(context, new_session, context.non_admin_username, user_access_token)
        time.sleep(sleep_timer)
        session_status = sessionHelper.wait_and_verify_session_state_matches(VirtualDesktopSessionState.READY, 'VirtualDesktop.GetSessionInfo')

        if session_status.get('session_state_matches'):
            vdc_test_helper.set_new_session(new_session)
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            session = sessionHelper.get_session_info('VirtualDesktop.GetSessionInfo')
            testcase_error_message = f'Failed to execute {test_case_name}.Session Name : {session.name}. Session is in invalid State : {session.state}. Session ID : {session.idea_session_id}' + session_status.get('error_log')
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)

    except (exceptions.SocaException, Exception) as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_get_session_screenshot(context: TestContext):
    test_case_name = 'Test User Get Session Screenshot'
    test_results_map = SessionsTestResultMap(test_case_name)
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_GET_SESSION_SCREENSHOT
    user_access_token = context.get_non_admin_access_token()
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.non_admin_username, user_access_token)
            response = session_helper.get_session_screenshot('VirtualDesktop.GetSessionScreenshot')

            if response.success is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)
            assert False

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_update_session(context: TestContext):
    test_case_name = 'Test User Update Session'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_UPDATE_SESSION
    user_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.non_admin_username, user_access_token)
            response = session_helper.update_session('VirtualDesktop.UpdateSession')

            if response.session is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)
            assert False

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_get_session_connection_info(context: TestContext):
    test_case_name = 'Test User Get Session Connection Info'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_GET_SESSION_CONNECTION_INFO
    user_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.non_admin_username, user_access_token)
            response = session_helper.get_session_connection_info('VirtualDesktop.GetSessionConnectionInfo')

            if response is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)
            assert False

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_get_session_info(context: TestContext):
    test_case_name = 'Test User Get Session Info'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_GET_SESSION_INFO
    user_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.non_admin_username, user_access_token)
            response = session_helper.get_session_info('VirtualDesktop.GetSessionInfo')

            if response.base_os is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)
            assert False

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_session_workflow(context: TestContext):
    testcase_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_SESSION_WORKFLOW
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        if vdc_test_helper.is_new_session_created():
            user_access_token = context.get_non_admin_access_token()
            session_workflow = SessionWorkflow(context, vdc_test_helper.get_new_session(), testcase_id, context.non_admin_username, user_access_token, 'VirtualDesktop.GetSessionInfo')
            session_workflow.test_session_workflow('user')
        else:
            testcase_error_message = f'Created session is None. Skipping {testcase_id}.'
            context.error(testcase_error_message)
    except exceptions.SocaException as e:
        context.error(f'Failed to execute test user session workflow. Error Code : {e.error_code} Error: {e.message}')


def test_user_list_sessions(context: TestContext):
    test_case_name = 'Test User List Sessions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_LIST_SESSIONS
    non_admin_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_api_helper = VirtualDesktopApiHelper(context, non_admin_access_token, context.non_admin_username)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_sessions('VirtualDesktop.ListSessions')

        if response.listing is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_list_software_stacks(context: TestContext):
    test_case_name = 'Test User List Software Stacks'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_LIST_SOFTWARE_STACKS
    user_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_api_helper = VirtualDesktopApiHelper(context, user_access_token, context.non_admin_username)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        response = vdc_api_helper.list_software_stacks('VirtualDesktop.ListSoftwareStacks')

        if response is not None:
            vdc_test_helper.on_test_pass(test_case_name, test_results_map)

        else:
            vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_update_session_permissions(context: TestContext):
    test_case_name = 'Test User Update Session Permission'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_UPDATE_SESSION_PERMISSIONS
    user_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.non_admin_username, user_access_token)
            response = session_helper.update_session_permissions('VirtualDesktop.UpdateSessionPermissions')

            if response is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)
            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}.'
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)
            assert False

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_list_session_permissions(context: TestContext):
    test_case_name = 'Test User List Session Permissions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_LIST_SESSION_PERMISSIONS
    user_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)

    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.non_admin_username, user_access_token)
            response = session_helper.list_session_permissions('VirtualDesktop.ListSessionPermissions')

            if response is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)
            assert False

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


def test_user_list_shared_permissions(context: TestContext):
    test_case_name = 'Test User List Shared Permissions'
    test_case_id = test_constants.VIRTUAL_DESKTOP_TEST_USER_LIST_SHARED_PERMISSIONS
    user_access_token = context.get_non_admin_access_token()
    test_results_map = SessionsTestResultMap(test_case_name)
    vdc_test_helper = VirtualDesktopTestHelper(context)
    try:
        vdc_test_helper.before_test(test_case_name)

        if vdc_test_helper.is_new_session_created():
            session_helper = SessionsTestHelper(context, vdc_test_helper.get_new_session(), context.non_admin_username, user_access_token)
            response = session_helper.list_shared_permissions('VirtualDesktop.ListSharedPermissions')

            if response is not None:
                vdc_test_helper.on_test_pass(test_case_name, test_results_map)

            else:
                vdc_test_helper.on_test_fail(test_case_name, response, test_results_map)

        else:
            testcase_error_message = f'Created session is None. Skipping {test_case_name}. '
            test_results_map.update_test_result_map(VirtualDesktopSessionTestResults.FAILED, testcase_error_message)
            context.error(testcase_error_message)
            assert False

    except exceptions.SocaException as error:
        vdc_test_helper.on_test_exception(test_case_name, error, test_results_map)

    finally:
        vdc_test_helper.after_test(test_case_name, test_results_map, test_case_id)


TEST_CASES = [
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_BATCH_SESSION_WORKFLOW,
        'test_case': test_admin_batch_session_workflow
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_CREATE_SESSION,
        'test_case': test_admin_create_session
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_GET_SESSION_SCREENSHOT,
        'test_case': test_admin_get_session_screenshot
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_UPDATE_SESSION,
        'test_case': test_admin_update_session
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_GET_SESSION_INFO,
        'test_case': test_admin_get_session_info
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_LIST_SESSIONS,
        'test_case': test_admin_list_sessions
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_LIST_SOFTWARE_STACKS,
        'test_case': test_admin_list_software_stacks
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_CREATE_SOFTWARE_STACK,
        'test_case': test_admin_create_software_stack
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_UPDATE_SOFTWARE_STACK,
        'test_case': test_admin_update_software_stack
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_CREATE_SOFTWARE_STACK_FROM_SESSION,
        'test_case': test_admin_create_software_stack_from_session
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_GET_SESSION_CONNECTION_INFO,
        'test_case': test_admin_get_session_connection_info
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_CREATE_PERMISSION_PROFILE,
        'test_case': test_admin_create_permission_profile
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_LIST_SESSION_PERMISSIONS,
        'test_case': test_admin_list_session_permissions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_LIST_SHARED_PERMISSIONS,
        'test_case': test_admin_list_shared_permissions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_UPDATE_PERMISSION_PROFILE,
        'test_case': test_admin_update_permission_profile
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_UPDATE_SESSION_PERMISSIONS,
        'test_case': test_admin_update_session_permissions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_GET_SOFTWARE_STACK_INFO,
        'test_case': test_admin_get_software_stack_info
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_LIST_SUPPORTED_OS,
        'test_case': test_list_supported_os
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_LIST_SUPPORTED_GPU,
        'test_case': test_list_supported_gpu
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_LIST_SCHEDULE_TYPES,
        'test_case': test_list_schedule_types
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_LIST_ALLOWED_INSTANCE_TYPES,
        'test_case': test_list_allowed_instance_types
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_LIST_ALLOWED_INSTANCE_TYPES_FOR_SESSION,
        'test_case': test_list_allowed_instance_types_for_session
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_GET_BASE_PERMISSIONS,
        'test_case': test_get_base_permissions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_LIST_PERMISSION_PROFILES,
        'test_case': test_list_permission_profiles
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_GET_PERMISSION_PROFILE,
        'test_case': test_get_permission_profile
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_DESCRIBE_SERVERS,
        'test_case': test_describe_servers
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_DESCRIBE_SERVERS,
        'test_case': test_describe_sessions
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_CREATE_SESSION,
        'test_case': test_user_create_session
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_GET_SESSION_SCREENSHOT,
        'test_case': test_user_get_session_screenshot
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_UPDATE_SESSION,
        'test_case': test_user_update_session
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_GET_SESSION_CONNECTION_INFO,
        'test_case': test_user_get_session_connection_info
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_GET_SESSION_INFO,
        'test_case': test_user_get_session_info
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_SESSION_WORKFLOW,
        'test_case': test_user_session_workflow
    },

    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_LIST_SESSIONS,
        'test_case': test_user_list_sessions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_LIST_SOFTWARE_STACKS,
        'test_case': test_user_list_software_stacks
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_UPDATE_SESSION_PERMISSIONS,
        'test_case': test_user_update_session_permissions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_LIST_SESSION_PERMISSIONS,
        'test_case': test_user_list_session_permissions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_USER_LIST_SHARED_PERMISSIONS,
        'test_case': test_user_list_shared_permissions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_DELETE_SESSIONS,
        'test_case': test_admin_delete_sessions
    },
    {
        'test_case_id': test_constants.VIRTUAL_DESKTOP_TEST_ADMIN_DELETE_SOFTWARE_STACK,
        'test_case': test_admin_delete_software_stack
    }
]
