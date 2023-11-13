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

from ideasdk.api import BaseAPI
from ideasdk.protocols import SocaContextProtocol
from ideasdk.api import ApiInvocationContext
from ideadatamodel import exceptions
from ideadatamodel.filesystem import (
    ListFilesRequest,
    ReadFileRequest,
    SaveFileRequest,
    DownloadFilesRequest,
    DownloadFilesResult,
    CreateFileRequest,
    DeleteFilesRequest,
    TailFileRequest
)
from ideasdk.filesystem.filesystem_helper import FileSystemHelper


class FileBrowserAPI(BaseAPI):

    def __init__(self, context: SocaContextProtocol):
        self.context = context

    def list_files(self, context: ApiInvocationContext):
        helper = FileSystemHelper(self.context, context.get_username())
        request = context.get_request_payload_as(ListFilesRequest)
        response = helper.list_files(request)
        context.success(response)

    def read_file(self, context: ApiInvocationContext):
        helper = FileSystemHelper(self.context, context.get_username())
        request = context.get_request_payload_as(ReadFileRequest)
        response = helper.read_file(request)
        context.success(response)

    def tail_file(self, context: ApiInvocationContext):
        helper = FileSystemHelper(self.context, context.get_username())
        request = context.get_request_payload_as(TailFileRequest)
        response = helper.tail_file(request)
        context.success(response)

    def save_file(self, context: ApiInvocationContext):
        helper = FileSystemHelper(self.context, context.get_username())
        request = context.get_request_payload_as(SaveFileRequest)
        response = helper.save_file(request)
        context.success(response)

    def download_files(self, context: ApiInvocationContext):
        helper = FileSystemHelper(self.context, context.get_username())
        request = context.get_request_payload_as(DownloadFilesRequest)
        download_file = helper.download_files(request)
        context.success(DownloadFilesResult(
            download_url=download_file
        ))

    def create_file(self, context: ApiInvocationContext):
        helper = FileSystemHelper(self.context, context.get_username())
        request = context.get_request_payload_as(CreateFileRequest)
        response = helper.create_file(request)
        context.success(response)

    def delete_files(self, context: ApiInvocationContext):
        helper = FileSystemHelper(self.context, context.get_username())
        request = context.get_request_payload_as(DeleteFilesRequest)
        response = helper.delete_files(request)
        context.success(response)

    def invoke(self, context: ApiInvocationContext):

        # authorized user access - do not allow app based authorizations to read user files
        if not context.is_authorized_user():
            raise exceptions.unauthorized_access()

        namespace = context.namespace

        if namespace == 'FileBrowser.ListFiles':
            self.list_files(context)
        elif namespace == 'FileBrowser.ReadFile':
            self.read_file(context)
        elif namespace == 'FileBrowser.TailFile':
            self.tail_file(context)
        elif namespace == 'FileBrowser.SaveFile':
            self.save_file(context)
        elif namespace == 'FileBrowser.DownloadFiles':
            self.download_files(context)
        elif namespace == 'FileBrowser.CreateFile':
            self.create_file(context)
        elif namespace == 'FileBrowser.DeleteFiles':
            self.delete_files(context)
