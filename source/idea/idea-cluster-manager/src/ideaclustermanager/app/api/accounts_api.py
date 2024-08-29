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
    GetUserRequest,
    GetUserResult,
    GetUserByEmailRequest,
    GetUserByEmailResult,
    ModifyUserRequest,
    ModifyUserResult,
    EnableUserRequest,
    EnableUserResult,
    DisableUserRequest,
    DisableUserResult,
    ListUsersRequest,
    ResetPasswordRequest,
    ResetPasswordResult,
    ModifyGroupRequest,
    ModifyGroupResult,
    EnableGroupRequest,
    EnableGroupResult,
    DisableGroupRequest,
    DisableGroupResult,
    GetGroupRequest,
    GetGroupResult,
    ListGroupsRequest,
    ListUsersInGroupRequest,
    AddAdminUserRequest,
    AddAdminUserResult,
    RemoveAdminUserRequest,
    RemoveAdminUserResult,
    GlobalSignOutRequest,
    GlobalSignOutResult,
)
from ideadatamodel import exceptions
from ideasdk.utils import Utils

import ideaclustermanager


class AccountsAPI(BaseAPI):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context

        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
            'Accounts.GetUser': {
                'scope': self.SCOPE_READ,
                'method': self.get_user
            },
            'Accounts.GetUserByEmail': {
                'scope': self.SCOPE_READ,
                'method': self.get_user_by_email
            },
            'Accounts.ModifyUser': {
                'scope': self.SCOPE_WRITE,
                'method': self.modify_user
            },
            'Accounts.ListUsers': {
                'scope': self.SCOPE_READ,
                'method': self.list_users
            },
            'Accounts.EnableUser': {
                'scope': self.SCOPE_WRITE,
                'method': self.enable_user
            },
            'Accounts.DisableUser': {
                'scope': self.SCOPE_WRITE,
                'method': self.disable_user
            },
            'Accounts.GetGroup': {
                'scope': self.SCOPE_READ,
                'method': self.get_group
            },
            'Accounts.ModifyGroup': {
                'scope': self.SCOPE_WRITE,
                'method': self.modify_group
            },
            'Accounts.EnableGroup': {
                'scope': self.SCOPE_WRITE,
                'method': self.enable_group
            },
            'Accounts.DisableGroup': {
                'scope': self.SCOPE_WRITE,
                'method': self.disable_group
            },
            'Accounts.ListGroups': {
                'scope': self.SCOPE_READ,
                'method': self.list_groups
            },
            'Accounts.ListUsersInGroup': {
                'scope': self.SCOPE_READ,
                'method': self.list_users_in_group
            },
            'Accounts.AddAdminUser': {
                'scope': self.SCOPE_WRITE,
                'method': self.add_admin_user
            },
            'Accounts.RemoveAdminUser': {
                'scope': self.SCOPE_WRITE,
                'method': self.remove_admin_user
            },
            'Accounts.GlobalSignOut': {
                'scope': self.SCOPE_WRITE,
                'method': self.global_sign_out
            },
            'Accounts.ResetPassword': {
                'scope': self.SCOPE_WRITE,
                'method': self.reset_password
            }
        }

    @property
    def token_service(self):
        return self.context.token_service

    def is_applicable(self, context: ApiInvocationContext, scope: str) -> bool:
        access_token = context.access_token
        decoded_token = self.token_service.decode_token(access_token)

        groups = Utils.get_value_as_list('cognito:groups', decoded_token)
        if Utils.is_not_empty(groups) and self.context.user_pool.admin_group_name in groups:
            return True

        token_scope = Utils.get_value_as_string('scope', decoded_token)
        if Utils.is_empty(token_scope):
            return False
        return scope in token_scope.split(' ')

    def get_user(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetUserRequest)
        user = self.context.accounts.get_user(request.username)
        context.success(GetUserResult(user=user))

    def get_user_by_email(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetUserByEmailRequest)
        user = self.context.accounts.get_user_by_email(request.email)
        context.success(GetUserByEmailResult(user=user))

    def modify_user(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ModifyUserRequest)
        email_verified = Utils.get_as_bool(request.email_verified, False)
        user = self.context.accounts.modify_user(request.user, email_verified)
        context.success(ModifyUserResult(
            user=user
        ))

    def enable_user(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(EnableUserRequest)
        self.context.accounts.enable_user(request.username)
        context.success(EnableUserResult())

    def disable_user(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(DisableUserRequest)
        self.context.accounts.disable_user(request.username)
        context.success(DisableUserResult())

    def list_users(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListUsersRequest)
        result = self.context.accounts.list_users(request)
        context.success(result)

    def global_sign_out(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GlobalSignOutRequest)

        self.context.accounts.global_sign_out(username=request.username)

        context.success(GlobalSignOutResult())

    def reset_password(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ResetPasswordRequest)
        self.context.accounts.reset_password(request.username)
        context.success(ResetPasswordResult())

    def modify_group(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ModifyGroupRequest)
        modified_group = self.context.accounts.modify_group(request.group)
        context.success(ModifyGroupResult(
            group=modified_group
        ))

    def enable_group(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(EnableGroupRequest)
        self.context.accounts.enable_group(request.group_name)
        context.success(EnableGroupResult())

    def disable_group(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(DisableGroupRequest)
        self.context.accounts.disable_group(request.group_name)
        context.success(DisableGroupResult())

    def get_group(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetGroupRequest)
        group = self.context.accounts.get_group(request.group_name)
        context.success(GetGroupResult(
            group=group
        ))

    def list_groups(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListGroupsRequest)
        result = self.context.accounts.list_groups(request)
        context.success(result)

    def list_users_in_group(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListUsersInGroupRequest)
        result = self.context.accounts.list_users_in_group(request)
        context.success(result)

    def add_admin_user(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(AddAdminUserRequest)
        self.context.accounts.add_admin_user(request.username)
        user = self.context.accounts.get_user(request.username)
        context.success(AddAdminUserResult(
            user=user
        ))

    def remove_admin_user(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(RemoveAdminUserRequest)
        self.context.accounts.remove_admin_user(request.username)
        user = self.context.accounts.get_user(request.username)
        context.success(RemoveAdminUserResult(
            user=user
        ))

    @staticmethod
    def check_admin_authorization_services(context: ApiInvocationContext):
        """
        only an admin user should be able to create additional admin users or perform
        admin user related operations
        a "manager" user should be able to add new users, but without admin access
        an admin user cannot be created using client credentials grant scope. needs an admin "user" to create a admin user.
        """

        namespace = context.namespace
        is_admin_authorization_required = namespace in (
            'Accounts.AddAdminUser',
            'Accounts.RemoveAdminUser',
            'Accounts.ModifyUser'
        )

        if not is_admin_authorization_required:
            return

        if context.is_administrator():
            return

        raise exceptions.unauthorized_access()

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        # special check only applicable for admin users related functionality
        self.check_admin_authorization_services(context)

        acl_entry_scope = Utils.get_value_as_string('scope', acl_entry)
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])

        # Allow if admin
        if is_authorized:
            acl_entry['method'](context)
            return

        if namespace == 'Accounts.ListUsers':
            username = context.get_username()
            user = self.context.accounts.get_user(username)
            if self.context.role_assignments.check_permissions_in_any_role(user=user, permissions=["projects.update_personnel","vdis.create_terminate_others_sessions"]):
                acl_entry['method'](context)
                return
        elif namespace == 'Accounts.ListGroups':
            username = context.get_username()
            user = self.context.accounts.get_user(username)
            if self.context.role_assignments.check_permissions_in_any_role(user=user, permissions=["projects.update_personnel"]):
                acl_entry['method'](context)
                return
        
        raise exceptions.unauthorized_access()
