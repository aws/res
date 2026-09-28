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
import time
from typing import Any, Optional, Type

from ideadatamodel import (  # type: ignore
    AddFileSystemToProjectRequest,
    AddFileSystemToProjectResult,
    BatchDeleteRoleAssignmentRequest,
    BatchDeleteRoleAssignmentResponse,
    BatchPutRoleAssignmentRequest,
    BatchPutRoleAssignmentResponse,
    CreateFileRequest,
    CreateFileResult,
    CreateProjectRequest,
    CreateProjectResult,
    DeleteFilesRequest,
    DeleteFilesResult,
    DeleteProjectRequest,
    DeleteProjectResult,
    DisableGroupRequest,
    DisableProjectRequest,
    DisableUserRequest,
    DownloadFilesRequest,
    DownloadFilesResult,
    EnableGroupRequest,
    EnableProjectRequest,
    EnableUserRequest,
    GetGroupRequest,
    GetGroupResult,
    GetModuleSettingsRequest,
    GetModuleSettingsResult,
    GetProjectRequest,
    GetProjectResult,
    GetUserRequest,
    GetUserResult,
    ListEmailTemplatesRequest,
    ListEmailTemplatesResult,
    ListFilesRequest,
    ListFilesResult,
    ListOnboardedFileSystemsRequest,
    ListOnboardedFileSystemsResult,
    ListRoleAssignmentsRequest,
    ListRoleAssignmentsResponse,
    ModifyUserRequest,
    ModifyUserResult,
    OnboardS3BucketRequest,
    OnboardS3BucketResult,
    ReadFileRequest,
    ReadFileResult,
    RemoveFileSystemFromProjectRequest,
    RemoveFileSystemFromProjectResult,
    RemoveFileSystemRequest,
    RemoveFileSystemResult,
    RoleAssignment,
    SaveFileRequest,
    SaveFileResult,
    SocaEnvelope,
    SocaHeader,
    SocaPayload,
    SocaPayloadType,
    TailFileRequest,
    TailFileResult,
    UpdateModuleSettingsRequest,
    UpdateModuleSettingsResult,
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
        self._res_environment = res_environment
        self._client_auth = client_auth
        self._api_invoker = self._get_api_invoker(api_invoker_type)

        self._endpoint = f"https://{res_environment.web_app_domain_name}"

    def create_project(
        self, request: CreateProjectRequest, should_succeed: bool = True
    ) -> CreateProjectResult:
        logger.info(f"creating project {request.project.name}...")

        return self._invoke(
            "Projects.CreateProject",
            "cluster-manager",
            request,
            CreateProjectResult,
            should_succeed,
        )

    def delete_project(
        self, request: DeleteProjectRequest, should_succeed: bool = True
    ) -> DeleteProjectResult:
        project = request.project_name if request.project_name else request.project_id
        logger.info(f"deleting project {project}...")

        return self._invoke(
            "Projects.DeleteProject",
            "cluster-manager",
            request,
            DeleteProjectResult,
            should_succeed,
        )

    def get_user(
        self,
        request: GetUserRequest,
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
    ) -> GetUserResult:
        logger.info(f"getting user {request.username}...")

        return self._invoke(
            "Accounts.GetUser",
            "cluster-manager",
            request,
            GetUserResult,
            should_succeed,
            expected_error_code,
        )

    def modify_user(
        self, request: ModifyUserRequest, should_succeed: bool = True
    ) -> ModifyUserResult:
        logger.info(f"modifying user {request.user.username}...")

        return self._invoke(
            "Accounts.ModifyUser",
            "cluster-manager",
            request,
            ModifyUserResult,
            should_succeed,
        )

    def enable_user(self, username: str, should_succeed: bool = True) -> None:
        logger.info(f"enabling user {username}...")
        self._invoke(
            "Accounts.EnableUser",
            "cluster-manager",
            EnableUserRequest(username=username),
            type(None),
            should_succeed,
        )

    def disable_user(self, username: str, should_succeed: bool = True) -> None:
        logger.info(f"disabling user {username}...")
        self._invoke(
            "Accounts.DisableUser",
            "cluster-manager",
            DisableUserRequest(username=username),
            type(None),
            should_succeed,
        )

    def enable_group(self, group_name: str, should_succeed: bool = True) -> None:
        logger.info(f"enabling group {group_name}...")
        self._invoke(
            "Accounts.EnableGroup",
            "cluster-manager",
            EnableGroupRequest(group_name=group_name),
            type(None),
            should_succeed,
        )

    def disable_group(self, group_name: str, should_succeed: bool = True) -> None:
        logger.info(f"disabling group {group_name}...")
        self._invoke(
            "Accounts.DisableGroup",
            "cluster-manager",
            DisableGroupRequest(group_name=group_name),
            type(None),
            should_succeed,
        )

    def get_group(self, group_name: str, should_succeed: bool = True) -> GetGroupResult:
        logger.info(f"getting group {group_name}...")
        return self._invoke(
            "Accounts.GetGroup",
            "cluster-manager",
            GetGroupRequest(group_name=group_name),
            GetGroupResult,
            should_succeed,
        )

    def enable_project(self, project_name: str, should_succeed: bool = True) -> None:
        logger.info(f"enabling project {project_name}...")
        self._invoke(
            "Projects.EnableProject",
            "cluster-manager",
            EnableProjectRequest(project_name=project_name),
            type(None),
            should_succeed,
        )

    def disable_project(self, project_name: str, should_succeed: bool = True) -> None:
        logger.info(f"disabling project {project_name}...")
        self._invoke(
            "Projects.DisableProject",
            "cluster-manager",
            DisableProjectRequest(project_name=project_name),
            type(None),
            should_succeed,
        )

    def get_project(
        self,
        project_name: str,
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
    ) -> GetProjectResult:
        logger.info(f"getting project {project_name}...")
        return self._invoke(
            "Projects.GetProject",
            "cluster-manager",
            GetProjectRequest(project_name=project_name),
            GetProjectResult,
            should_succeed,
            expected_error_code,
        )

    def batch_put_role_assignment(
        self, request: BatchPutRoleAssignmentRequest, should_succeed: bool = True
    ) -> BatchPutRoleAssignmentResponse:
        logger.info(f"entering role assignments {request.items}...")

        return self._invoke(
            "Authz.BatchPutRoleAssignment",
            "cluster-manager",
            request,
            BatchPutRoleAssignmentResponse,
            should_succeed,
        )

    def batch_delete_role_assignment(
        self, request: BatchDeleteRoleAssignmentRequest, should_succeed: bool = True
    ) -> BatchDeleteRoleAssignmentResponse:
        logger.info(f"deleting role assignments {request.items}...")

        return self._invoke(
            "Authz.BatchDeleteRoleAssignment",
            "cluster-manager",
            request,
            BatchDeleteRoleAssignmentResponse,
            should_succeed,
        )

    def list_role_assignments(
        self, request: ListRoleAssignmentsRequest, should_succeed: bool = True
    ) -> ListRoleAssignmentsResponse:
        logger.info("listing role assignments...")

        return self._invoke(
            "Authz.ListRoleAssignments",
            "cluster-manager",
            request,
            ListRoleAssignmentsResponse,
            should_succeed,
        )

    def get_module_settings(
        self, request: GetModuleSettingsRequest, should_succeed: bool = True
    ) -> GetModuleSettingsResult:
        logger.info(f"getting module settings...")

        return self._invoke(
            "ClusterSettings.GetModuleSettings",
            "cluster-manager",
            request,
            GetModuleSettingsResult,
            should_succeed,
        )

    def update_module_settings(
        self, request: UpdateModuleSettingsRequest, should_succeed: bool = True
    ) -> UpdateModuleSettingsResult:
        logger.info(f"updating module settings...")

        return self._invoke(
            "ClusterSettings.UpdateModuleSettings",
            "cluster-manager",
            request,
            UpdateModuleSettingsResult,
            should_succeed,
        )

    def list_files(
        self,
        request: ListFilesRequest,
        should_succeed: bool = True,
    ) -> ListFilesResult:
        logger.info(f"listing files...")

        return self._invoke(
            "FileBrowser.ListFiles",
            "cluster-manager",
            request,
            ListFilesResult,
            should_succeed,
        )

    def read_file(
        self,
        request: ReadFileRequest,
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
    ) -> ReadFileResult:
        logger.info(f"reading file...")

        return self._invoke(
            "FileBrowser.ReadFile",
            "cluster-manager",
            request,
            ReadFileResult,
            should_succeed,
            expected_error_code,
        )

    def tail_file(
        self,
        request: TailFileRequest,
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
    ) -> TailFileResult:
        logger.info(f"tailing file...")

        return self._invoke(
            "FileBrowser.TailFile",
            "cluster-manager",
            request,
            TailFileResult,
            should_succeed,
            expected_error_code,
        )

    def save_file(
        self,
        request: SaveFileRequest,
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
    ) -> SaveFileResult:
        logger.info(f"saving file...")

        return self._invoke(
            "FileBrowser.SaveFile",
            "cluster-manager",
            request,
            SaveFileResult,
            should_succeed,
            expected_error_code,
        )

    def download_files(
        self,
        request: DownloadFilesRequest,
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
    ) -> DownloadFilesResult:
        logger.info(f"downloading files...")

        return self._invoke(
            "FileBrowser.DownloadFiles",
            "cluster-manager",
            request,
            DownloadFilesResult,
            should_succeed,
            expected_error_code,
        )

    def create_file(
        self,
        request: CreateFileRequest,
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
    ) -> CreateFileResult:
        logger.info(f"creating file...")

        return self._invoke(
            "FileBrowser.CreateFile",
            "cluster-manager",
            request,
            CreateFileResult,
            should_succeed,
            expected_error_code,
        )

    def delete_files(
        self,
        request: DeleteFilesRequest,
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
    ) -> DeleteFilesResult:
        logger.info(f"deleting files...")

        return self._invoke(
            "FileBrowser.DeleteFiles",
            "cluster-manager",
            request,
            DeleteFilesResult,
            should_succeed,
            expected_error_code,
        )

    def list_email_templates(
        self, request: ListEmailTemplatesRequest, should_succeed: bool = True
    ) -> ListEmailTemplatesResult:
        logger.info("getting list of email templates...")

        return self._invoke(
            "EmailTemplates.ListEmailTemplates",
            "cluster-manager",
            request,
            ListEmailTemplatesResult,
            should_succeed,
        )

    def onboard_s3_bucket(
        self, request: OnboardS3BucketRequest, should_succeed: bool = True
    ) -> OnboardS3BucketResult:
        logger.info(
            f"onboarding S3 bucket {request.bucket_arn} "
            f"at {request.mount_directory}..."
        )

        return self._invoke(
            "FileSystem.OnboardS3Bucket",
            "cluster-manager",
            request,
            OnboardS3BucketResult,
            should_succeed,
        )

    def add_filesystem_to_project(
        self,
        request: AddFileSystemToProjectRequest,
        should_succeed: bool = True,
    ) -> AddFileSystemToProjectResult:
        logger.info(
            f"adding filesystem {request.filesystem_name} "
            f"to project {request.project_name}..."
        )

        return self._invoke(
            "FileSystem.AddFileSystemToProject",
            "cluster-manager",
            request,
            AddFileSystemToProjectResult,
            should_succeed,
        )

    def remove_filesystem(
        self, request: RemoveFileSystemRequest, should_succeed: bool = True
    ) -> RemoveFileSystemResult:
        logger.info(f"removing filesystem {request.filesystem_name}...")

        return self._invoke(
            "FileSystem.RemoveFileSystem",
            "cluster-manager",
            request,
            RemoveFileSystemResult,
            should_succeed,
        )

    def remove_filesystem_from_project(
        self,
        request: RemoveFileSystemFromProjectRequest,
        should_succeed: bool = True,
    ) -> RemoveFileSystemFromProjectResult:
        logger.info(
            f"removing filesystem {request.filesystem_name} "
            f"from project {request.project_name}..."
        )

        return self._invoke(
            "FileSystem.RemoveFileSystemFromProject",
            "cluster-manager",
            request,
            RemoveFileSystemFromProjectResult,
            should_succeed,
        )

    def list_onboarded_file_systems(
        self,
        request: ListOnboardedFileSystemsRequest,
        should_succeed: bool = True,
    ) -> ListOnboardedFileSystemsResult:
        logger.info("listing onboarded file systems...")

        return self._invoke(
            "FileSystem.ListOnboardedFileSystems",
            "cluster-manager",
            request,
            ListOnboardedFileSystemsResult,
            should_succeed,
        )

    def _invoke(
        self,
        namespace: str,
        component: str,
        request: SocaPayload,
        response_type: Type[SocaPayloadType],
        should_succeed: bool = True,
        expected_error_code: Optional[str] = None,
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
            and should_succeed
            or not context.response_is_success()
            and not should_succeed
        ), f'error code: {context.response.get("error_code")} message: {context.response.get("message")}'

        if expected_error_code:
            actual_error_code = context.response.get("error_code")
            assert (
                actual_error_code == expected_error_code
            ), f"Expected error code '{expected_error_code}' but got '{actual_error_code}'"

        return context.get_response_payload_as(response_type)

    @staticmethod
    def _get_api_invoker(api_invoker_type: str) -> ResApiInvokerBase:
        if api_invoker_type == "http":
            return HttpApiInvoker()
        else:
            raise Exception(f"Invalid API invoker type {api_invoker_type}")
