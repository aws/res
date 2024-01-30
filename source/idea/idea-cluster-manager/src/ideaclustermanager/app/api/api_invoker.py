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

import ideaclustermanager
from ideasdk.api import ApiInvocationContext
from ideasdk.protocols import ApiInvokerProtocol
from ideasdk.auth import TokenService, ApiAuthorizationServiceBase
from ideasdk.utils import Utils
from ideadatamodel.auth import (
    CreateUserRequest,
    InitiateAuthRequest,
    InitiateAuthResult,
    ListUsersResult,
    ListGroupsResult,
    RespondToAuthChallengeRequest,
    RespondToAuthChallengeResult,
    ChangePasswordRequest,
    ConfirmForgotPasswordRequest,
    GetUserPrivateKeyResult,
    SignOutRequest
)
from ideadatamodel.filesystem import (
    ReadFileResult,
    TailFileResult
)
from ideadatamodel.snapshots import (
    ListSnapshotsResult
)

from ideasdk.app import SocaAppAPI
from ideasdk.filesystem.filebrowser_api import FileBrowserAPI
from ideaclustermanager.app.api.cluster_settings_api import ClusterSettingsAPI
from ideaclustermanager.app.api.filesystem_api import FileSystemAPI
from ideaclustermanager.app.api.projects_api import ProjectsAPI
from ideaclustermanager.app.api.accounts_api import AccountsAPI
from ideaclustermanager.app.api.auth_api import AuthAPI
from ideaclustermanager.app.api.email_templates_api import EmailTemplatesAPI
from ideaclustermanager.app.api.snapshots_api import SnapshotsAPI
from typing import Optional, Dict


class ClusterManagerApiInvoker(ApiInvokerProtocol):

    def __init__(self, context: ideaclustermanager.AppContext):
        self._context = context
        self.app_api = SocaAppAPI(context)
        self.file_browser_api = FileBrowserAPI(context)
        self.cluster_settings_api = ClusterSettingsAPI(context)
        self.projects_api = ProjectsAPI(context)
        self.filesystem_api = FileSystemAPI(context)
        self.auth_api = AuthAPI(context)
        self.accounts_api = AccountsAPI(context)
        self.snapshots_api = SnapshotsAPI(context)
        self.email_templates_api = EmailTemplatesAPI(context)
        self.max_listings_for_logging = 10
        self.auto_truncate_responses = {
            "Accounts.ListUsers": ListUsersResult,
            "Accounts.ListGroups": ListGroupsResult,
            "Snapshots.ListSnapshots": ListSnapshotsResult
        }

    def get_token_service(self) -> Optional[TokenService]:
        return self._context.token_service

    def get_api_authorization_service(self) -> Optional[ApiAuthorizationServiceBase]:
        return self._context.api_authorization_service

    def get_request_logging_payload(self, context: ApiInvocationContext) -> Optional[Dict]:
        namespace = context.namespace

        if namespace == 'Auth.InitiateAuth':
            request = context.get_request(deep_copy=True)
            payload = context.get_request_payload_as(InitiateAuthRequest)
            if payload.password is not None:
                payload.password = '*****'
            if payload.authorization_code is not None:
                payload.authorization_code = '*****'
            request['payload'] = Utils.to_dict(payload)
            return request
        elif namespace == 'Auth.SignOut':
            request = context.get_request(deep_copy=True)
            payload = context.get_request_payload_as(SignOutRequest)
            payload.refresh_token = '*****'
            request['payload'] = Utils.to_dict(payload)
            return request
        elif namespace == 'Auth.RespondToAuthChallenge':
            request = context.get_request(deep_copy=True)
            payload = context.get_request_payload_as(RespondToAuthChallengeRequest)
            payload.new_password = '*****'
            request['payload'] = Utils.to_dict(payload)
            return request
        elif namespace == 'Auth.ConfirmForgotPassword':
            request = context.get_request(deep_copy=True)
            payload = context.get_request_payload_as(ConfirmForgotPasswordRequest)
            payload.password = '*****'
            request['payload'] = Utils.to_dict(payload)
            return request
        elif namespace == 'Auth.ChangePassword':
            request = context.get_request(deep_copy=True)
            payload = context.get_request_payload_as(ChangePasswordRequest)
            payload.old_password = '*****'
            payload.new_password = '*****'
            request['payload'] = Utils.to_dict(payload)
            return request
        elif namespace == 'Accounts.CreateUser':
            request = context.get_request(deep_copy=True)
            payload = context.get_request_payload_as(CreateUserRequest)
            if payload.user is not None and Utils.is_not_empty(payload.user.password):
                payload.user.password = '*****'
            request['payload'] = Utils.to_dict(payload)
            return request

    def get_response_logging_payload(self, context: ApiInvocationContext) -> Optional[Dict]:
        if not context.is_success():
            return None

        namespace = context.namespace

        # Namespaces that are subject to listing truncating
        # to keep the logs usable in larger environments.


        if namespace == 'Auth.InitiateAuth':
            response = context.get_response(deep_copy=True)
            payload = context.get_response_payload_as(InitiateAuthResult)
            if payload.auth is not None:
                payload.auth.access_token = '*****'
                if payload.auth.id_token is not None:
                    payload.auth.id_token = '*****'
                if payload.auth.refresh_token is not None:
                    payload.auth.refresh_token = '*****'
            response['payload'] = Utils.to_dict(payload)
            return response
        elif namespace == 'Auth.RespondToAuthChallenge':
            response = context.get_response(deep_copy=True)
            payload = context.get_response_payload_as(RespondToAuthChallengeResult)
            if payload.auth is not None:
                payload.auth.access_token = '*****'
                if payload.auth.refresh_token is not None:
                    payload.auth.refresh_token = '*****'
            response['payload'] = Utils.to_dict(payload)
            return response
        elif namespace == 'Auth.GetUserPrivateKey':
            response = context.get_response(deep_copy=True)
            payload = context.get_response_payload_as(GetUserPrivateKeyResult)
            key_size = Utils.get_as_int(payload.key_material, default=0)
            payload.key_material = f'**key_material_length=={key_size}**'
            response['payload'] = Utils.to_dict(payload)
            return response
        elif namespace == 'FileBrowser.ReadFile':
            response = context.get_response(deep_copy=True)
            payload = context.get_response_payload_as(ReadFileResult)
            payload.content = '****'
            response['payload'] = Utils.to_dict(payload)
            return response
        elif namespace == 'FileBrowser.TailFile':
            response = context.get_response(deep_copy=True)
            payload = context.get_response_payload_as(TailFileResult)
            payload.lines = ['****']
            response['payload'] = Utils.to_dict(payload)
            return response
        elif namespace in self.auto_truncate_responses:
            request = context.get_response(deep_copy=True)
            payload = context.get_response_payload_as(self.auto_truncate_responses.get(namespace))
            payload_listing_count = Utils.get_as_int(len(Utils.get_as_list(payload.listing, default=[])), default=0)

            if payload_listing_count > self.max_listings_for_logging:
                # This would normally be a log_debug() but the API response log line comes out as INFO
                # We want to make sure we do not confuse the admin log-user by showing a truncated list
                context.log_info(f"Truncated {payload_listing_count - self.max_listings_for_logging} entries from payload logging for {namespace} ({payload_listing_count} non-truncated listings)")
                payload.listing = payload.listing[0:self.max_listings_for_logging]
            request['payload'] = Utils.to_dict(payload)
            return request

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace
        if namespace.startswith('Auth.'):
            self.auth_api.invoke(context)
        elif namespace.startswith('App.'):
            return self.app_api.invoke(context)
        elif namespace.startswith('FileBrowser.'):
            self.file_browser_api.invoke(context)
        elif namespace.startswith('ClusterSettings.'):
            self.cluster_settings_api.invoke(context)
        elif namespace.startswith('Projects.'):
            self.projects_api.invoke(context)
        elif namespace.startswith('FileSystem.'):
            self.filesystem_api.invoke(context)
        elif namespace.startswith('Accounts.'):
            self.accounts_api.invoke(context)
        elif namespace.startswith('EmailTemplates.'):
            self.email_templates_api.invoke(context)
        elif namespace.startswith('Snapshots.'):
            self.snapshots_api.invoke(context)
