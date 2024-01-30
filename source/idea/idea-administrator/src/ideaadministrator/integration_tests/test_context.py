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

from ideasdk.client import SocaClient, SocaClientOptions
from ideasdk.context import SocaCliContext
from ideasdk.utils import Utils
from ideadatamodel import (
    AuthResult,
    InitiateAuthRequest,
    InitiateAuthResult
)
from ideadatamodel import exceptions, constants
from ideasdk.config.cluster_config import ClusterConfig

from typing import Optional, Dict, List
import arrow


class TestContext:

    def __init__(self, cluster_name: str,
                 aws_region: str,
                 admin_username: str,
                 admin_password: str,
                 module_set: str,
                 aws_profile: Optional[str] = None,
                 debug: bool = False,
                 extra_params: Optional[Dict] = None,
                 test_case_ids: Optional[List[str]] = None,
                 module_ids: Optional[List] = None):

        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.module_ids = module_ids
        self.non_admin_username = None
        self.non_admin_password = None

        self.debug = debug
        self.extra_params = extra_params if extra_params else {}
        self.filter_test_case_ids = test_case_ids if Utils.is_not_empty(test_case_ids) else None
        self.module_set = module_set

        self.cluster_config = ClusterConfig(
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            module_set=module_set
        )
        self.virtual_desktop_controller_active_module_id = self.cluster_config.get_module_id(constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)

        self.cluster_endpoint = self.cluster_config.get_cluster_external_endpoint()

        self.idea_context = SocaCliContext()
        self.test_run_id = Utils.file_system_friendly_timestamp()

        # initialize admin authentication
        # create internal http client to disable admin password exposed in integration test logs
        cluster_manager_module_id = self.cluster_config.get_module_id(constants.MODULE_CLUSTER_MANAGER)
        self._admin_http_client = SocaClient(context=self.idea_context,
                                             options=SocaClientOptions(
                                                 enable_logging=False,
                                                 endpoint=f'{self.cluster_endpoint}/{cluster_manager_module_id}/api/v1',
                                                 verify_ssl=False
                                             ))
        self.admin_auth_expires_on: Optional[arrow.arrow] = None
        self.non_admin_auth_expires_on: Optional[arrow.arrow] = None
        self.admin_auth: Optional[AuthResult] = None
        self.non_admin_auth: Optional[AuthResult] = None
        self.initialize_admin_auth()
        if self.set_non_admin_user_account(extra_params):
            self.initialize_non_admin_auth()
        self.module_ids = module_ids

        # test clients map module_id => SocaClient
        self.clients: Dict[str, SocaClient] = {}

        self.test_cases = {}

    def get_client(self, module_name: str, timeout: Optional[int] = 10) -> SocaClient:

        module_id = self.cluster_config.get_module_id(module_name=module_name)

        if module_id in self.clients:
            return self.clients[module_id]

        module_info = self.cluster_config.db.get_module_info(module_id)
        if module_info is None:
            raise exceptions.general_exception(f'module not found for module id: {module_id}')

        api_path = f'/{module_id}/api/v1'

        if Utils.is_empty(api_path):
            raise exceptions.general_exception(f'could not find api context path for module: {module_id}')

        client = SocaClient(context=self.idea_context, options=SocaClientOptions(enable_logging=self.debug,
                                                                                 endpoint=f'{self.cluster_endpoint}{api_path}',
                                                                                 verify_ssl=False,
                                                                                 timeout=timeout))
        self.clients[module_id] = client
        return client

    def set_non_admin_user_account(self, extra_params) -> bool:
        if self.virtual_desktop_controller_active_module_id in self.module_ids:
            if 'test_username' in extra_params and 'test_password' in extra_params:
                if Utils.is_not_empty(extra_params.get('test_username')) and Utils.is_not_empty(extra_params.get('test_password')):
                    self.non_admin_username = extra_params.get('test_username')
                    self.non_admin_password = extra_params.get('test_password')
                    return True
                else:
                    raise exceptions.general_exception(f'Invalid \'test_username\' or \'test_password\' value. Required parameter to execute {self.virtual_desktop_controller_active_module_id} tests')
            else:
                raise exceptions.general_exception(f'Missing Parameter \'test_username\' or \'test_password\'. Required parameter to execute {self.virtual_desktop_controller_active_module_id} tests.')

    def get_virtual_desktop_controller_client(self, timeout: Optional[int] = 10) -> SocaClient:
        return self.get_client(constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER, timeout)

    def get_scheduler_client(self) -> SocaClient:
        return self.get_client(constants.MODULE_SCHEDULER)

    def get_cluster_manager_client(self) -> SocaClient:
        return self.get_client(constants.MODULE_CLUSTER_MANAGER)

    def initialize_admin_auth(self):
        if self.admin_auth is None:
            self.idea_context.info('Initializing Admin Authentication ...')
            result = self._admin_http_client.invoke_alt('Auth.InitiateAuth', InitiateAuthRequest(
                auth_flow='USER_PASSWORD_AUTH',
                cognito_username=self.admin_username,
                password=self.admin_password
            ), result_as=InitiateAuthResult)
            admin_auth = result.auth
            if Utils.is_empty(admin_auth.access_token):
                raise exceptions.general_exception('access_token not found')
            if Utils.is_empty(admin_auth.refresh_token):
                raise exceptions.general_exception('refresh_token not found')
        else:
            self.idea_context.info('Renewing Admin Authentication Access Token ...')
            result = self._admin_http_client.invoke_alt('Auth.InitiateAuth', InitiateAuthRequest(
                auth_flow='REFRESH_TOKEN_AUTH',
                cognito_username=self.admin_username,
                refresh_token=self.admin_auth.refresh_token
            ), result_as=InitiateAuthResult)

            admin_auth = result.auth
            if Utils.is_empty(admin_auth.access_token):
                raise exceptions.general_exception('access_token not found')
            # set refresh token from previous auth
            admin_auth.refresh_token = self.admin_auth.refresh_token

        self.admin_auth = admin_auth
        self.admin_auth_expires_on = arrow.get().shift(seconds=admin_auth.expires_in)

    def initialize_non_admin_auth(self):
        if self.non_admin_auth is None:
            self.idea_context.info('Initializing Non-Admin Authentication ...')
            result = self._admin_http_client.invoke_alt('Auth.InitiateAuth', InitiateAuthRequest(
                auth_flow='USER_PASSWORD_AUTH',
                cognito_username=self.non_admin_username,
                password=self.non_admin_password
            ), result_as=InitiateAuthResult)
            non_admin_auth = result.auth
            if Utils.is_empty(non_admin_auth.access_token):
                raise exceptions.general_exception('access_token not found')
            if Utils.is_empty(non_admin_auth.refresh_token):
                raise exceptions.general_exception('refresh_token not found')
        else:
            self.idea_context.info('Renewing Non-Admin Authentication Access Token ...')
            result = self._admin_http_client.invoke_alt('Auth.InitiateAuth', InitiateAuthRequest(
                auth_flow='REFRESH_TOKEN_AUTH',
                cognito_username=self.non_admin_username,
                refresh_token=self.non_admin_auth.refresh_token
            ), result_as=InitiateAuthResult)

            non_admin_auth = result.auth
            if Utils.is_empty(non_admin_auth.access_token):
                raise exceptions.general_exception('access_token not found')

        self.non_admin_auth = non_admin_auth
        self.non_admin_auth_expires_on = arrow.get().shift(seconds=non_admin_auth.expires_in)

    def get_admin_access_token(self) -> str:
        if self.admin_auth is None:
            raise exceptions.general_exception('admin authentication not initialized')
        if self.admin_auth_expires_on > arrow.get().shift(minutes=15):
            return self.admin_auth.access_token
        self.initialize_admin_auth()
        return self.admin_auth.access_token

    def get_non_admin_access_token(self):
        if self.non_admin_auth is None:
            raise exceptions.general_exception('non admin authentication not initialized')
        if self.non_admin_auth_expires_on > arrow.get().shift(minutes=15):
            return self.non_admin_auth.access_token
        self.initialize_non_admin_auth()
        return self.non_admin_auth.access_token

    def begin_test_case(self, test_case_id: str):
        self.idea_context.print(f'{test_case_id}   [STARTED]')
        self.test_cases[test_case_id] = 'IN_PROGRESS'

    def end_test_case(self, test_case_id: str, success: bool):
        if success:
            self.idea_context.success(f'{test_case_id}   [PASS]')
            self.test_cases[test_case_id] = 'PASS'
        else:
            self.idea_context.error(f'{test_case_id}   [FAIL]')
            self.test_cases[test_case_id] = 'FAIL'

    def is_test_case_passed(self, test_case_id: str) -> bool:
        if test_case_id in self.test_cases:
            return self.test_cases.get(test_case_id) == 'PASS'
        return False

    def info(self, message: str):
        self.idea_context.info(message)

    def warning(self, message: str):
        self.idea_context.warning(message)

    def success(self, message: str):
        self.idea_context.success(message)

    def error(self, message: str):
        self.idea_context.error(message)
