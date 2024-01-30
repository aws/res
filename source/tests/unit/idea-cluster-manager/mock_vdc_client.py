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

from typing import Optional

from ideasdk.client.vdc_client import AbstractVirtualDesktopControllerClient

from ideadatamodel import (
    VirtualDesktopPermission,
    VirtualDesktopPermissionProfile,
    VirtualDesktopSession,
    VirtualDesktopSoftwareStack,
)


class MockVirtualDesktopControllerClient(AbstractVirtualDesktopControllerClient):
    sessions: list[VirtualDesktopSession] = []
    software_stacks: list[VirtualDesktopSoftwareStack] = []
    base_permissions: list[VirtualDesktopPermission] = []

    def list_sessions_by_project_id(
        self, project_id: str
    ) -> list[VirtualDesktopSession]:
        return self.sessions

    def list_software_stacks_by_project_id(
        self, project_id: str
    ) -> list[VirtualDesktopSoftwareStack]:
        return self.software_stacks

    def get_base_permissions(self) -> list[VirtualDesktopPermission]:
        return self.base_permissions

    def create_permission_profile(
        self,
        profile: VirtualDesktopPermissionProfile,
    ) -> VirtualDesktopPermissionProfile:
        pass

    def delete_permission_profile(self, profile_id: str) -> None:
        pass

    def get_permission_profile(
        self, profile_id: str
    ) -> VirtualDesktopPermissionProfile:
        pass

    def get_software_stacks_by_name(
        self, stack_name: str
    ) -> list[VirtualDesktopSoftwareStack]:
        return self.software_stacks

    def create_software_stack(
        self, software_stack: VirtualDesktopSoftwareStack
    ) -> VirtualDesktopSoftwareStack:
        pass

    def delete_software_stack(
        self, software_stack: VirtualDesktopSoftwareStack
    ) -> None:
        pass
