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

import logging
from typing import Type

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver

from ideadatamodel import (  # type: ignore
    BatchDeleteRoleAssignmentRequest,
    BatchDeleteRoleAssignmentResponse,
    BatchPutRoleAssignmentRequest,
    BatchPutRoleAssignmentResponse,
    CreateProjectRequest,
    CreateProjectResult,
    CreateSessionRequest,
    CreateSessionResponse,
    CreateSoftwareStackRequest,
    CreateSoftwareStackResponse,
    DeleteProjectRequest,
    DeleteProjectResult,
    DeleteSessionRequest,
    DeleteSessionResponse,
    DeleteSoftwareStackRequest,
    DeleteSoftwareStackResponse,
    GetSessionConnectionInfoRequest,
    GetSessionConnectionInfoResponse,
    GetSessionInfoRequest,
    GetSessionInfoResponse,
    GetUserRequest,
    GetUserResult,
    ListAllowedInstanceTypesRequest,
    ListAllowedInstanceTypesResponse,
    ListRoleAssignmentsRequest,
    ListRoleAssignmentsResponse,
    ListSessionsRequest,
    ListSessionsResponse,
    ListSoftwareStackRequest,
    ListSoftwareStackResponse,
    ModifyUserRequest,
    ModifyUserResult,
    RoleAssignment,
    SocaEnvelope,
    SocaHeader,
    SocaPayload,
    SocaPayloadType,
    UpdateModuleSettingsRequest,
    UpdateModuleSettingsResult,
    UpdateSessionRequest,
    UpdateSessionResponse,
    VirtualDesktopSession,
    VirtualDesktopSessionConnectionInfo,
)
from tests.integration.framework.api_invoker.api_invoker_base import ResApiInvokerBase
from tests.integration.framework.api_invoker.http_api_invoker import HttpApiInvoker
from tests.integration.framework.fixtures.res_environment import ResEnvironment
from tests.integration.framework.model.api_invocation_context import (
    ApiInvocationContext,
)
from tests.integration.framework.model.client_auth import ClientAuth

logger = logging.getLogger(__name__)


class ResClient:
    """
    RES client for invoking service APIs
    """

    def __init__(
        self,
        res_environment: ResEnvironment,
        client_auth: ClientAuth,
        api_invoker_type: str,
    ):
        self._client_auth = client_auth
        self._api_invoker = self._get_api_invoker(api_invoker_type)

        self._endpoint = f"https://{res_environment.web_app_domain_name}"

    def create_project(self, request: CreateProjectRequest) -> CreateProjectResult:
        logger.info(f"creating project {request.project.name}...")

        return self._invoke(
            "Projects.CreateProject",
            "cluster-manager",
            request,
            CreateProjectResult,
        )

    def delete_project(self, request: DeleteProjectRequest) -> DeleteProjectResult:
        project = request.project_name if request.project_name else request.project_id
        logger.info(f"deleting project {project}...")

        return self._invoke(
            "Projects.DeleteProject",
            "cluster-manager",
            request,
            DeleteProjectResult,
        )

    def get_user(self, request: GetUserRequest) -> GetUserResult:
        logger.info(f"getting user {request.username}...")

        return self._invoke(
            "Accounts.GetUser",
            "cluster-manager",
            request,
            GetUserResult,
        )

    def modify_user(self, request: ModifyUserRequest) -> ModifyUserResult:
        logger.info(f"modifying user {request.user.username}...")

        return self._invoke(
            "Accounts.ModifyUser",
            "cluster-manager",
            request,
            ModifyUserResult,
        )

    def create_software_stack(
        self, request: CreateSoftwareStackRequest
    ) -> CreateSoftwareStackResponse:
        logger.info(f"creating software stack {request.software_stack.name}...")

        return self._invoke(
            "VirtualDesktopAdmin.CreateSoftwareStack",
            "vdc",
            request,
            CreateSoftwareStackResponse,
        )

    def delete_software_stack(
        self, request: DeleteSoftwareStackRequest
    ) -> DeleteSoftwareStackResponse:
        logger.info(f"deleting software stack {request.software_stack.name}...")

        return self._invoke(
            "VirtualDesktopAdmin.DeleteSoftwareStack",
            "vdc",
            request,
            DeleteSoftwareStackResponse,
        )

    def list_software_stacks(
        self, request: ListSoftwareStackRequest
    ) -> ListSoftwareStackResponse:
        logger.info(f"listing software stacks...")

        return self._invoke(
            "VirtualDesktopAdmin.ListSoftwareStacks",
            "vdc",
            request,
            ListSoftwareStackResponse,
        )

    def list_allowed_instance_types(
        self, request: ListAllowedInstanceTypesRequest
    ) -> ListAllowedInstanceTypesResponse:
        logger.info(f"listing allowed instance types...")

        return self._invoke(
            "VirtualDesktopUtils.ListAllowedInstanceTypes",
            "vdc",
            request,
            ListAllowedInstanceTypesResponse,
        )

    def create_session(self, request: CreateSessionRequest) -> CreateSessionResponse:
        logger.info(f"creating session {request.session.name}...")

        return self._invoke(
            "VirtualDesktop.CreateSession",
            "vdc",
            request,
            CreateSessionResponse,
        )

    def batch_put_role_assignment(
        self, request: BatchPutRoleAssignmentRequest
    ) -> BatchPutRoleAssignmentResponse:
        logger.info(f"entering role assignments {request.items}...")

        return self._invoke(
            "Authz.BatchPutRoleAssignment",
            "cluster-manager",
            request,
            BatchPutRoleAssignmentResponse,
        )

    def batch_delete_role_assignment(
        self, request: BatchDeleteRoleAssignmentRequest
    ) -> BatchDeleteRoleAssignmentResponse:
        logger.info(f"deleting role assignments {request.items}...")

        return self._invoke(
            "Authz.BatchDeleteRoleAssignment",
            "cluster-manager",
            request,
            BatchDeleteRoleAssignmentResponse,
        )

    def list_role_assignments(
        self, request: ListRoleAssignmentsRequest
    ) -> ListRoleAssignmentsResponse:
        logger.info(f"listing role assignments {request.items}...")

        return self._invoke(
            "Authz.ListRoleAssignments",
            "cluster-manager",
            request,
            ListRoleAssignmentsResponse,
        )

    def get_session_info(
        self, request: GetSessionInfoRequest
    ) -> GetSessionInfoResponse:
        logger.info(f"getting session info for {request.session.name}...")

        return self._invoke(
            "VirtualDesktop.GetSessionInfo",
            "vdc",
            request,
            GetSessionInfoResponse,
        )

    def get_session_connection_info(
        self, request: GetSessionConnectionInfoRequest
    ) -> GetSessionConnectionInfoResponse:
        logger.info(
            f"getting connection info for session {request.connection_info.dcv_session_id}..."
        )

        return self._invoke(
            "VirtualDesktop.GetSessionConnectionInfo",
            "vdc",
            request,
            GetSessionConnectionInfoResponse,
        )

    def list_sessions(self, request: ListSessionsRequest) -> ListSessionsResponse:
        logger.info("listing sessions...")

        return self._invoke(
            "VirtualDesktop.ListSessions",
            "vdc",
            request,
            ListSessionsResponse,
        )

    def update_session(self, request: UpdateSessionRequest) -> UpdateSessionResponse:
        logger.info(f"updating session {request.session.dcv_session_id}...")

        return self._invoke(
            "VirtualDesktop.UpdateSession",
            "vdc",
            request,
            UpdateSessionResponse,
        )

    def join_session(self, session: VirtualDesktopSession) -> WebDriver:
        get_session_connection_info_request = GetSessionConnectionInfoRequest(
            connection_info=VirtualDesktopSessionConnectionInfo(
                dcv_session_id=session.dcv_session_id,
            )
        )
        get_session_connection_info_response = self.get_session_connection_info(
            get_session_connection_info_request
        )
        connection_info = get_session_connection_info_response.connection_info
        logger.info(f"joining session {connection_info.dcv_session_id}...")

        # Open the session connection URL from a Chrome browser and keep the connection active.
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--no-sandbox")
        options.binary_location = "/usr/bin/chrome"
        driver = webdriver.Chrome(options=options)

        connection_url = f"{connection_info.endpoint}{connection_info.web_url_path}?authToken={connection_info.access_token}#{connection_info.dcv_session_id}"
        driver.get(connection_url)

        return driver

    def delete_sessions(self, request: DeleteSessionRequest) -> DeleteSessionResponse:
        session_names = [session.name for session in request.sessions]
        logger.info(f"deleting sessions {session_names}...")

        return self._invoke(
            "VirtualDesktop.DeleteSessions",
            "vdc",
            request,
            DeleteSessionResponse,
        )

    def update_module_settings(
        self, request: UpdateModuleSettingsRequest
    ) -> UpdateModuleSettingsResult:
        logger.info(f"updating module settings...")

        return self._invoke(
            "ClusterSettings.UpdateModuleSettings",
            "cluster-manager",
            request,
            UpdateModuleSettingsResult,
        )

    def _invoke(
        self,
        namespace: str,
        component: str,
        request: SocaPayload,
        response_type: Type[SocaPayloadType],
    ) -> SocaPayloadType:
        header = SocaHeader()
        header.namespace = namespace
        header.version = 1

        envelope = SocaEnvelope()
        envelope.header = header
        envelope.payload = request

        context = ApiInvocationContext(
            endpoint=f"{self._endpoint}/{component}",
            request=envelope,
            auth=self._client_auth,
        )

        self._api_invoker.invoke(context)

        assert (
            context.response_is_success()
        ), f'error code: {context.response.get("error_code")} message: {context.response.get("message")}'

        return context.get_response_payload_as(response_type)

    @staticmethod
    def _get_api_invoker(api_invoker_type: str) -> ResApiInvokerBase:
        if api_invoker_type == "http":
            return HttpApiInvoker()
        else:
            raise Exception(f"Invalid API invoker type {api_invoker_type}")
