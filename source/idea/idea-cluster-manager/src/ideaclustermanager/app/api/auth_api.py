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

from ideasdk.api import BaseAPI, ApiInvocationContext
from ideadatamodel.auth import (
    GetUserResult,
    InitiateAuthRequest,
    RespondToAuthChallengeRequest,
    ForgotPasswordRequest,
    ForgotPasswordResult,
    ChangePasswordRequest,
    ChangePasswordResult,
    ConfirmForgotPasswordRequest,
    ConfirmForgotPasswordResult,
    GetGroupResult,
    ListUsersInGroupRequest,
    GetUserPrivateKeyRequest,
    GetUserPrivateKeyResult,
    SignOutRequest,
    SignOutResult,
    GlobalSignOutRequest,
    GlobalSignOutResult,
    ConfigureSSORequest
)
from ideadatamodel import exceptions
from ideasdk.utils import Utils

import ideaclustermanager
from ideaclustermanager.app.accounts.user_home_directory import UserHomeDirectory


class AuthAPI(BaseAPI):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context

    def initiate_auth(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(InitiateAuthRequest)
        result = self.context.accounts.initiate_auth(request)
        context.success(result)

    def respond_to_auth_challenge(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(RespondToAuthChallengeRequest)
        result = self.context.accounts.respond_to_auth_challenge(request)
        context.success(result)

    def forgot_password(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ForgotPasswordRequest)
        self.context.accounts.forgot_password(request.username)
        context.success(ForgotPasswordResult())

    def confirm_forgot_password(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ConfirmForgotPasswordRequest)
        self.context.accounts.confirm_forgot_password(
            request.username,
            request.password,
            request.confirmation_code
        )
        context.success(ConfirmForgotPasswordResult())

    def change_password(self, context: ApiInvocationContext):
        username = context.get_username()
        if Utils.is_empty(username):
            raise exceptions.unauthorized_access()

        request = context.get_request_payload_as(ChangePasswordRequest)
        self.context.accounts.change_password(context.access_token, username, request.old_password, request.new_password)

        context.success(ChangePasswordResult())

    def get_user(self, context: ApiInvocationContext):
        username = context.get_username()
        if Utils.is_empty(username):
            raise exceptions.unauthorized_access()

        user = self.context.accounts.get_user(username)
        context.success(GetUserResult(
            user=user
        ))

    def get_user_group(self, context: ApiInvocationContext):
        username = context.get_username()
        if Utils.is_empty(username):
            raise exceptions.unauthorized_access()

        group_name = self.context.accounts.group_name_helper.get_user_group(username)
        group = self.context.accounts.get_group(group_name)
        context.success(GetGroupResult(
            group=group
        ))

    def sign_out(self, context: ApiInvocationContext):
        if not context.is_authenticated():
            raise exceptions.unauthorized_access()

        request = context.get_request_payload_as(SignOutRequest)
        self.context.accounts.sign_out(
            refresh_token=request.refresh_token,
            sso_auth=Utils.get_as_bool(request.sso_auth, False)
        )

        context.success(SignOutResult())

    def global_sign_out(self, context: ApiInvocationContext):
        if not context.is_authenticated_user():
            raise exceptions.unauthorized_access()

        request = context.get_request_payload_as(GlobalSignOutRequest)
        if Utils.is_not_empty(request.username) and request.username != context.get_username():
            raise exceptions.unauthorized_access()

        self.context.accounts.global_sign_out(username=context.get_username())

        context.success(GlobalSignOutResult())

    def get_user_private_key(self, context: ApiInvocationContext):
        if not context.is_authorized_user():
            raise exceptions.unauthorized_access()

        request = context.get_request_payload_as(GetUserPrivateKeyRequest)
        key_format = request.key_format
        platform = request.platform

        user = self.context.accounts.get_user(context.get_username())
        home_dir = UserHomeDirectory(self.context, user)

        key_name = home_dir.get_key_name(key_format)
        key_material = home_dir.get_key_material(key_format, platform)

        context.success(GetUserPrivateKeyResult(
            name=key_name,
            key_material=key_material
        ))

    def list_users_in_group(self, context: ApiInvocationContext):
        if not context.is_authenticated():
            raise exceptions.unauthorized_access()
        request = context.get_request_payload_as(ListUsersInGroupRequest)
        result = self.context.accounts.list_users_in_group(request)
        context.success(result)

    def configure_sso(self, context: ApiInvocationContext):
        if not context.is_administrator():
            raise exceptions.unauthorized_access()

        request = context.get_request_payload_as(ConfigureSSORequest)
        result = self.context.accounts.configure_sso(request)
        context.success(result)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace
        if namespace == 'Auth.GlobalSignOut':
            self.global_sign_out(context)
        elif namespace == 'Auth.SignOut':
            self.sign_out(context)
        elif namespace == 'Auth.InitiateAuth':
            self.initiate_auth(context)
        elif namespace == 'Auth.RespondToAuthChallenge':
            self.respond_to_auth_challenge(context)
        elif namespace == 'Auth.ForgotPassword':
            self.forgot_password(context)
        elif namespace == 'Auth.ConfirmForgotPassword':
            self.confirm_forgot_password(context)
        elif namespace == 'Auth.ChangePassword':
            self.change_password(context)
        elif namespace == 'Auth.GetUser':
            self.get_user(context)
        elif namespace == 'Auth.GetGroup':
            self.get_user_group(context)
        elif namespace == 'Auth.GetUserPrivateKey':
            self.get_user_private_key(context)
        elif namespace == 'Auth.ListUsersInGroup':
            self.list_users_in_group(context)
        elif namespace == 'Auth.ConfigureSSO':
            self.configure_sso(context)
