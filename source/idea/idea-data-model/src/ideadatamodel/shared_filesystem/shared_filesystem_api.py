#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

__all__ = (
    "AddFileSystemToProjectRequest",
    "AddFileSystemToProjectResult",
    "RemoveFileSystemFromProjectRequest",
    "RemoveFileSystemFromProjectResult",
    "CommonCreateFileSystemRequest",
    "CreateEFSFileSystemRequest",
    "CreateONTAPFileSystemRequest",
    "CreateFileSystemResult",
    "ListFileSystemInVPCRequest",
    "ListFileSystemInVPCResult",
    'CommonOnboardFileSystemRequest',
    'OnboardEFSFileSystemRequest',
    'OnboardONTAPFileSystemRequest',
    'OnboardLUSTREFileSystemRequest',
    'OnboardFileSystemResult',
    'OffboardFileSystemRequest',
    "OPEN_API_SPEC_ENTRIES_FILESYSTEM",
)

from enum import Enum

from ideadatamodel.api import SocaPayload, IdeaOpenAPISpecEntry
from ideadatamodel.shared_filesystem import EFSFileSystem, FSxONTAPFileSystem, FSxLUSTREFileSystem
from typing import Optional, List


class FSxONTAPDeploymentType(str, Enum):
    MULTI_AZ = 'MULTI_AZ_1'
    SINGLE_AZ = 'SINGLE_AZ_1'


class FSxVolumeONTAPSecurityStyle(str, Enum):
    UNIX = 'UNIX'
    NTFS = 'NTFS'
    MIXED = 'MIXED'

# CreateFileSystemRequest


class CommonCreateFileSystemRequest(SocaPayload):
    filesystem_name: Optional[str]
    filesystem_title: Optional[str]
    projects: Optional[List[str]]


class CreateEFSFileSystemRequest(CommonCreateFileSystemRequest):
    mount_directory: str
    subnet_id_1: str
    subnet_id_2: str


class CreateONTAPFileSystemRequest(CommonCreateFileSystemRequest):
    mount_directory: Optional[str]
    mount_drive: Optional[str]
    primary_subnet: str
    standby_subnet: Optional[str]
    deployment_type: FSxONTAPDeploymentType
    volume_security_style: FSxVolumeONTAPSecurityStyle
    storage_capacity: int
    file_share_name:  Optional[str]


class CreateFileSystemResult(SocaPayload):
    pass


# AddFileSystemToProject


class AddFileSystemToProjectRequest(SocaPayload):
    filesystem_id: Optional[str]
    filesystem_name: Optional[str]
    project_id: Optional[str]
    project_name: Optional[str]


class AddFileSystemToProjectResult(SocaPayload):
    pass


# RemoveFileSystemFromProject


class RemoveFileSystemFromProjectRequest(SocaPayload):
    filesystem_id: Optional[str]
    filesystem_name: Optional[str]
    project_id: Optional[str]
    project_name: Optional[str]


class RemoveFileSystemFromProjectResult(SocaPayload):
    pass


# ListFileSystemInVPC
class ListFileSystemInVPCRequest(SocaPayload):
    pass


class ListFileSystemInVPCResult(SocaPayload):
    efs: Optional[List[EFSFileSystem]]
    fsx_ontap: Optional[List[FSxONTAPFileSystem]]
    fsx_lustre: Optional[List[FSxLUSTREFileSystem]]


# OnboardFileSystems
class CommonOnboardFileSystemRequest(SocaPayload):
    filesystem_name: str
    filesystem_title: str
    filesystem_id: str


class OnboardEFSFileSystemRequest(CommonOnboardFileSystemRequest):
    mount_directory: str


class OnboardONTAPFileSystemRequest(CommonOnboardFileSystemRequest):
    mount_directory: Optional[str]
    mount_drive: Optional[str]
    svm_id: str
    volume_id: str
    file_share_name: Optional[str]


class OnboardLUSTREFileSystemRequest(CommonOnboardFileSystemRequest):
    mount_directory: str


class OnboardFileSystemResult(SocaPayload):
    pass


class OffboardFileSystemRequest(SocaPayload):
    filesystem_name: str


OPEN_API_SPEC_ENTRIES_FILESYSTEM = [
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.AddFileSystemToProject",
        request=AddFileSystemToProjectRequest,
        result=AddFileSystemToProjectResult,
        is_listing=False,
        is_public=False,
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.RemoveFileSystemFromProject",
        request=RemoveFileSystemFromProjectRequest,
        result=RemoveFileSystemFromProjectResult,
        is_listing=False,
        is_public=False,
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.CreateEFS",
        request=CreateEFSFileSystemRequest,
        result=CreateFileSystemResult,
        is_listing=False,
        is_public=False,
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.CreateONTAP",
        request=CreateONTAPFileSystemRequest,
        result=CreateFileSystemResult,
        is_listing=False,
        is_public=False,
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.ListFSinVPC",
        request=ListFileSystemInVPCRequest,
        result=ListFileSystemInVPCResult,
        is_listing=False,
        is_public=False,
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.OnboardEFSFileSystem",
        request=OnboardEFSFileSystemRequest,
        result=OnboardFileSystemResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.OnboardONTAPFileSystem",
        request=OnboardONTAPFileSystemRequest,
        result=OnboardFileSystemResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.OnboardLUSTREFileSystem",
        request=OnboardLUSTREFileSystemRequest,
        result=OnboardFileSystemResult,
        is_listing=False,
        is_public=False
    )
]
