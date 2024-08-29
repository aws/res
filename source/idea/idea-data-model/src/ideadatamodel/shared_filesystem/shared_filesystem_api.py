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
    "UpdateFileSystemRequest",
    "UpdateFileSystemResult",
    "ListFileSystemInVPCRequest",
    "ListFileSystemInVPCResult",
    'CommonOnboardFileSystemRequest',
    'OnboardEFSFileSystemRequest',
    'OnboardONTAPFileSystemRequest',
    'OnboardLUSTREFileSystemRequest',
    'OnboardFileSystemResult',
    'RemoveFileSystemRequest',
    'RemoveFileSystemResult',
    "OnboardS3BucketRequest",
    "OnboardS3BucketResult",
    "ListOnboardedFileSystemsRequest",
    "ListOnboardedFileSystemsResult",
    "OPEN_API_SPEC_ENTRIES_FILESYSTEM",
)

from enum import Enum

from ideadatamodel import constants
from ideadatamodel.api import SocaPayload, SocaListingPayload, IdeaOpenAPISpecEntry
from ideadatamodel.shared_filesystem import FileSystem, EFSFileSystem, FSxONTAPFileSystem, FSxLUSTREFileSystem
from typing import Optional, List


class FSxONTAPDeploymentType(str, Enum):
    MULTI_AZ = 'MULTI_AZ_1'
    SINGLE_AZ = 'SINGLE_AZ_1'


class FSxVolumeONTAPSecurityStyle(str, Enum):
    UNIX = 'UNIX'
    NTFS = 'NTFS'
    MIXED = 'MIXED'


class CustomBucketPrefixTypes(str, Enum):
    ProjectNamePrefix = constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX
    ProjectNameUsernamePrefix = constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX
    NoCustomPrefix = constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX

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


# UpdateFileSystemRequest


class UpdateFileSystemRequest(SocaPayload):
    filesystem_name: str
    filesystem_title: Optional[str]
    projects: Optional[List[str]]


class UpdateFileSystemResult(SocaPayload):
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


# ListFileSystems


class ListFileSystemInVPCRequest(SocaPayload):
    pass


class ListFileSystemInVPCResult(SocaPayload):
    efs: Optional[List[EFSFileSystem]]
    fsx_ontap: Optional[List[FSxONTAPFileSystem]]
    fsx_lustre: Optional[List[FSxLUSTREFileSystem]]


class ListOnboardedFileSystemsRequest(SocaListingPayload):
    pass


class ListOnboardedFileSystemsResult(SocaListingPayload):
    listing: Optional[List[FileSystem]]


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


class RemoveFileSystemRequest(SocaPayload):
    filesystem_name: str


class RemoveFileSystemResult(SocaPayload):
    pass


class OnboardS3BucketRequest(SocaPayload):
    object_storage_title: str
    bucket_arn: str
    read_only: bool
    custom_bucket_prefix: Optional[CustomBucketPrefixTypes]
    mount_directory: str
    iam_role_arn: Optional[str]
    projects: Optional[List[str]]


class OnboardS3BucketResult(SocaPayload):
    pass


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
        namespace="FileSystem.UpdateFileSystem",
        request=UpdateFileSystemRequest,
        result=UpdateFileSystemResult,
        is_listing=False,
        is_public=False,
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.RemoveFileSystem",
        request=RemoveFileSystemRequest,
        result=RemoveFileSystemResult,
        is_listing=False,
        is_public=False,
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.ListFSinVPC",
        request=ListFileSystemInVPCRequest,
        result=ListFileSystemInVPCResult,
        is_listing=True,
        is_public=False,
    ),
        IdeaOpenAPISpecEntry(
        namespace="FileSystem.ListOnboardedFileSystems",
        request=ListOnboardedFileSystemsRequest,
        result=ListOnboardedFileSystemsResult,
        is_listing=True,
        is_public=False
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
    ),
    IdeaOpenAPISpecEntry(
        namespace="FileSystem.OnboardS3Bucket",
        request=OnboardS3BucketRequest,
        result=OnboardS3BucketResult,
        is_listing=False,
        is_public=False
    ),
]
