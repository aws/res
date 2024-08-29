#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from pydantic import ValidationError

import ideaclustermanager

from ideasdk.api import ApiInvocationContext, BaseAPI
from ideadatamodel.shared_filesystem import (
    AddFileSystemToProjectRequest,
    RemoveFileSystemFromProjectRequest,
    AddFileSystemToProjectResult,
    RemoveFileSystemFromProjectResult,
    CreateFileSystemResult,
    OnboardEFSFileSystemRequest,
    OnboardONTAPFileSystemRequest,
    OnboardLUSTREFileSystemRequest,
    OnboardFileSystemResult,
    CreateEFSFileSystemRequest,
    CreateONTAPFileSystemRequest,
    OnboardS3BucketRequest,
    ListOnboardedFileSystemsRequest,
    UpdateFileSystemRequest,
    RemoveFileSystemRequest,
)
from ideadatamodel import (
    exceptions
)
from ideasdk.utils import Utils

class FileSystemAPI(BaseAPI):
    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.config = self.context.config()
        self.logger = self.context.logger("shared-filesystem")

        self.SCOPE_WRITE = f"{self.context.module_id()}/write"
        self.SCOPE_READ = f"{self.context.module_id()}/read"

        self.acl = {
            "FileSystem.AddFileSystemToProject": {
                "scope": self.SCOPE_WRITE,
                "method": self.add_filesystem_to_project,
            },
            "FileSystem.RemoveFileSystemFromProject": {
                "scope": self.SCOPE_WRITE,
                "method": self.remove_filesystem_from_project,
            },
            "FileSystem.CreateEFS": {
                "scope": self.SCOPE_WRITE,
                "method": self.create_filesystem,
            },
            "FileSystem.CreateONTAP": {
                "scope": self.SCOPE_WRITE,
                "method": self.create_filesystem,
            },
            "FileSystem.UpdateFileSystem": {
                "scope": self.SCOPE_WRITE,
                "method": self.update_filesystem
            },
            "FileSystem.RemoveFileSystem": {
                "scope": self.SCOPE_WRITE,
                "method": self.remove_filesystem,
            },
            "FileSystem.ListOnboardedFileSystems": {
                "scope": self.SCOPE_READ,
                "method": self.list_onboarded_file_systems,
            },
            "FileSystem.ListFSinVPC": {
                "scope": self.SCOPE_READ,
                "method": self.list_file_systems_in_vpc,
            },
            "FileSystem.OnboardEFSFileSystem": {
                "scope": self.SCOPE_WRITE,
                "method": self.onboard_filesystem,
            },
            "FileSystem.OnboardONTAPFileSystem": {
                "scope": self.SCOPE_WRITE,
                "method": self.onboard_filesystem,
            },
            "FileSystem.OnboardLUSTREFileSystem": {
                "scope": self.SCOPE_WRITE,
                "method": self.onboard_filesystem,
            },
            "FileSystem.OnboardS3Bucket": {
                "scope": self.SCOPE_WRITE,
                "method": self.onboard_filesystem
            },
        }

    def create_filesystem(self, context: ApiInvocationContext):
        try:
            if context.namespace == "FileSystem.CreateEFS":
                self.context.shared_filesystem.create_efs(
                    context.get_request_payload_as(CreateEFSFileSystemRequest)
                )
            elif context.namespace == "FileSystem.CreateONTAP":
                self.context.shared_filesystem.create_fsx_ontap(
                    context.get_request_payload_as(CreateONTAPFileSystemRequest)
                )
        except ValidationError as e:
            self.logger.error(e.json())
            raise exceptions.general_exception(str(e.errors()))

        context.success(CreateFileSystemResult())
    
    def update_filesystem(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(UpdateFileSystemRequest)
        result = self.context.shared_filesystem.update_filesystem(request)
        context.success(result)
    
    def remove_filesystem(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(RemoveFileSystemRequest)
        result = self.context.shared_filesystem.remove_filesystem(request)
        context.success(result)

    def add_filesystem_to_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(AddFileSystemToProjectRequest)
        self.context.shared_filesystem.add_filesystem_to_project(request)
        context.success(AddFileSystemToProjectResult())

    def remove_filesystem_from_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(RemoveFileSystemFromProjectRequest)
        self.context.shared_filesystem.remove_filesystem_from_project(request)
        context.success(RemoveFileSystemFromProjectResult())

    def list_onboarded_file_systems(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListOnboardedFileSystemsRequest)
        result = self.context.shared_filesystem.list_onboarded_file_systems(request)
        context.success(result)

    def list_file_systems_in_vpc(self, context: ApiInvocationContext):
        result = self.context.shared_filesystem.list_file_systems_in_vpc()
        context.success(result)

    def onboard_filesystem(self, context: ApiInvocationContext):
        if context.namespace == 'FileSystem.OnboardEFSFileSystem':
            self.context.shared_filesystem.onboard_efs_filesystem(context.get_request_payload_as(OnboardEFSFileSystemRequest))

        elif context.namespace == 'FileSystem.OnboardONTAPFileSystem':
            self.context.shared_filesystem.onboard_ontap_filesystem(context.get_request_payload_as(OnboardONTAPFileSystemRequest))

        elif context.namespace == 'FileSystem.OnboardLUSTREFileSystem':
            self.context.shared_filesystem.onboard_lustre_filesystem(context.get_request_payload_as(OnboardLUSTREFileSystemRequest))

        elif context.namespace == 'FileSystem.OnboardS3Bucket':
            self.context.shared_filesystem.onboard_s3_bucket(context.get_request_payload_as(OnboardS3BucketRequest))

        context.success(OnboardFileSystemResult())

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = Utils.get_value_as_string("scope", acl_entry)
        is_authorized = context.is_authorized(
            elevated_access=True, scopes=[acl_entry_scope]
        )

        if is_authorized:
            acl_entry["method"](context)
        else:
            raise exceptions.unauthorized_access()
