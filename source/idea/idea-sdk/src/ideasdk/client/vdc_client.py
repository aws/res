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

from ideasdk.protocols import SocaContextProtocol
from ideasdk.client.soca_client import SocaClient, SocaClientOptions
from ideasdk.auth import TokenService
from ideasdk.utils import Utils
from ideadatamodel import exceptions
from ideadatamodel import (
    ListSessionsRequest,
    ListSessionsResponse,
    ListSoftwareStackRequest,
    ListSoftwareStackResponse,
    GetBasePermissionsRequest,
    GetBasePermissionsResponse,
    CreatePermissionProfileRequest,
    CreatePermissionProfileResponse,
    DeletePermissionProfileRequest,
    DeletePermissionProfileResponse,
    GetPermissionProfileRequest,
    GetPermissionProfileResponse,
    CreateSoftwareStackRequest,
    CreateSoftwareStackResponse,
    DeleteSoftwareStackRequest,
    DeleteSoftwareStackResponse,
    GetSoftwareStackInfoResponse,
    VirtualDesktopSoftwareStack,
    VirtualDesktopSession,
    VirtualDesktopPermission,
    VirtualDesktopPermissionProfile,
    SocaFilter,
)

from abc import abstractmethod
from typing import Optional


class AbstractVirtualDesktopControllerClient:
    @abstractmethod
    def list_sessions_by_project_id(self, project_id: str) -> list[VirtualDesktopSession]:
        ...

    @abstractmethod
    def list_software_stacks_by_project_id(self, project_id: str) -> list[VirtualDesktopSoftwareStack]:
        ...

    @abstractmethod
    def get_base_permissions(self) -> list[VirtualDesktopPermission]:
        ...

    @abstractmethod
    def create_permission_profile(self, profile: VirtualDesktopPermissionProfile) -> VirtualDesktopPermissionProfile:
        ...

    @abstractmethod
    def delete_permission_profile(self, profile_id: str) -> None:
        ...

    @abstractmethod
    def get_permission_profile(self, profile_id: str) -> VirtualDesktopPermissionProfile:
        ...

    @abstractmethod
    def get_software_stacks_by_name(self, stack_name: str) -> list[VirtualDesktopSoftwareStack]:
        ...

    @abstractmethod
    def create_software_stack(self, software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        ...

    @abstractmethod
    def delete_software_stack(self, software_stack: VirtualDesktopSoftwareStack) -> None:
        ...


class VirtualDesktopControllerClient(AbstractVirtualDesktopControllerClient):

    def __init__(self, context: SocaContextProtocol,
                 options: SocaClientOptions, token_service: Optional[TokenService]):
        """
        :param context: Application Context
        :param options: Client Options
        """
        self.context = context
        self.logger = context.logger('vdc-client')
        self.client = SocaClient(context=context, options=options)

        if Utils.is_empty(options.unix_socket) and token_service is None:
            raise exceptions.invalid_params('token_service is required for http client')
        self.token_service = token_service

    def get_access_token(self) -> Optional[str]:
        if self.token_service is None:
            return None
        return self.token_service.get_access_token()

    def list_sessions_by_project_id(self, project_id: str) -> list[VirtualDesktopSession]:
        result = self.client.invoke_alt(
            namespace='VirtualDesktopAdmin.ListSessions',
            payload=ListSessionsRequest(),
            result_as=ListSessionsResponse,
            access_token=self.get_access_token(),
        )

        return [session for session in result.listing if session.project.project_id == project_id] if result.listing else []

    def list_software_stacks_by_project_id(self, project_id: str) -> list[VirtualDesktopSoftwareStack]:
        result = self.client.invoke_alt(
            namespace='VirtualDesktop.ListSoftwareStacks',
            payload=ListSoftwareStackRequest(project_id=project_id),
            result_as=ListSoftwareStackResponse,
            access_token=self.get_access_token(),
        )

        return result.listing if result.listing else []

    def get_base_permissions(self) -> list[VirtualDesktopPermission]:
        result = self.client.invoke_alt(
            namespace='VirtualDesktopUtils.GetBasePermissions',
            payload=GetBasePermissionsRequest(),
            result_as=GetBasePermissionsResponse,
            access_token=self.get_access_token(),
        )

        return result.permissions if result.permissions else []

    def create_permission_profile(self, profile: VirtualDesktopPermissionProfile) -> VirtualDesktopPermissionProfile:
        result = self.client.invoke_alt(
            namespace='VirtualDesktopAdmin.CreatePermissionProfile',
            payload=CreatePermissionProfileRequest(profile=profile),
            result_as=CreatePermissionProfileResponse,
            access_token=self.get_access_token(),
        )

        return result.profile

    def delete_permission_profile(self, profile_id: str) -> None:
        self.client.invoke_alt(
            namespace='VirtualDesktopAdmin.DeletePermissionProfile',
            payload=DeletePermissionProfileRequest(profile_id=profile_id),
            result_as=DeletePermissionProfileResponse,
            access_token=self.get_access_token(),
        )

    def get_permission_profile(self, profile_id: str) -> VirtualDesktopPermissionProfile:
        result = self.client.invoke_alt(
            namespace='VirtualDesktopUtils.GetPermissionProfile',
            payload=GetPermissionProfileRequest(profile_id=profile_id),
            result_as=GetPermissionProfileResponse,
            access_token=self.get_access_token(),
        )

        return result.profile

    def get_software_stacks_by_name(self, stack_name: str) -> list[VirtualDesktopSoftwareStack]:
        result = self.client.invoke_alt(
            namespace='VirtualDesktopAdmin.ListSoftwareStacks',
            payload=ListSoftwareStackRequest(
                filters=[
                    SocaFilter(
                        key="name",
                        value=stack_name,
                    )
                ]
            ),
            result_as=ListSoftwareStackResponse,
            access_token=self.get_access_token(),
        )

        return result.listing if result.listing else []

    def create_software_stack(self, software_stack: VirtualDesktopSoftwareStack) -> VirtualDesktopSoftwareStack:
        result = self.client.invoke_alt(
            namespace='VirtualDesktopAdmin.CreateSoftwareStack',
            payload=CreateSoftwareStackRequest(software_stack=software_stack),
            result_as=CreateSoftwareStackResponse,
            access_token=self.get_access_token(),
        )

        return result.software_stack

    def delete_software_stack(self, software_stack: VirtualDesktopSoftwareStack) -> None:
        self.client.invoke_alt(
            namespace='VirtualDesktopAdmin.DeleteSoftwareStack',
            payload=DeleteSoftwareStackRequest(
                software_stack=software_stack
            ),
            result_as=DeleteSoftwareStackResponse,
            access_token=self.get_access_token(),
        )

    def destroy(self):
        self.client.close()
