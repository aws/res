/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 * with the License. A copy of the License is located at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 * OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

import {
    CreateUserRequest,
    CreateUserResult,
    GetUserRequest,
    GetUserResult,
    ModifyUserRequest,
    ModifyUserResult,
    DeleteUserRequest,
    DeleteUserResult,
    EnableUserRequest,
    EnableUserResult,
    DisableUserRequest,
    DisableUserResult,
    ListUsersRequest,
    ListUsersResult,
    GlobalSignOutRequest,
    GlobalSignOutResult,
    CreateGroupRequest,
    CreateGroupResult,
    ModifyGroupRequest,
    ModifyGroupResult,
    DeleteGroupRequest,
    DeleteGroupResult,
    EnableGroupRequest,
    EnableGroupResult,
    DisableGroupRequest,
    DisableGroupResult,
    GetGroupRequest,
    GetGroupResult,
    ListGroupsRequest,
    ListGroupsResult,
    AddUserToGroupRequest,
    AddUserToGroupResult,
    RemoveUserFromGroupRequest,
    RemoveUserFromGroupResult,
    ListUsersInGroupRequest,
    ListUsersInGroupResult,
    AddAdminUserRequest,
    AddAdminUserResult,
    RemoveAdminUserRequest,
    RemoveAdminUserResult,
    ResetPasswordRequest,
    ResetPasswordResult,
    GetModuleInfoRequest,
    GetModuleInfoResult,
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface AuthAdminClientProps extends IdeaBaseClientProps {}

class AccountsClient extends IdeaBaseClient<AuthAdminClientProps> {
    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {});
    }

    createUser(req: CreateUserRequest): Promise<CreateUserResult> {
        return this.apiInvoker.invoke_alt<CreateUserRequest, CreateUserResult>("Accounts.CreateUser", req);
    }

    getUser(req: GetUserRequest): Promise<GetUserResult> {
        return this.apiInvoker.invoke_alt<GetUserRequest, GetUserResult>("Accounts.GetUser", req);
    }

    modifyUser(req: ModifyUserRequest): Promise<ModifyUserResult> {
        return this.apiInvoker.invoke_alt<ModifyUserRequest, ModifyUserResult>("Accounts.ModifyUser", req);
    }

    enableUser(req: EnableUserRequest): Promise<EnableUserResult> {
        return this.apiInvoker.invoke_alt<EnableUserRequest, EnableUserResult>("Accounts.EnableUser", req);
    }

    disableUser(req: DisableUserRequest): Promise<DisableUserResult> {
        return this.apiInvoker.invoke_alt<DisableUserRequest, DisableUserResult>("Accounts.DisableUser", req);
    }

    deleteUser(req: DeleteUserRequest): Promise<DeleteUserResult> {
        return this.apiInvoker.invoke_alt<DeleteUserRequest, DeleteUserResult>("Accounts.DeleteUser", req);
    }

    listUsers(req?: ListUsersRequest): Promise<ListUsersResult> {
        return this.apiInvoker.invoke_alt<ListUsersRequest, ListUsersResult>("Accounts.ListUsers", req);
    }

    createGroup(req: CreateGroupRequest): Promise<CreateGroupResult> {
        return this.apiInvoker.invoke_alt<CreateGroupRequest, CreateGroupResult>("Accounts.CreateGroup", req);
    }

    getGroup(req: GetGroupRequest): Promise<GetGroupResult> {
        return this.apiInvoker.invoke_alt<GetGroupRequest, GetGroupResult>("Accounts.GetGroup", req);
    }

    modifyGroup(req: ModifyGroupRequest): Promise<ModifyGroupResult> {
        return this.apiInvoker.invoke_alt<ModifyGroupRequest, ModifyGroupResult>("Accounts.ModifyGroup", req);
    }

    enableGroup(req: EnableGroupRequest): Promise<EnableGroupResult> {
        return this.apiInvoker.invoke_alt<EnableGroupRequest, EnableGroupResult>("Accounts.EnableGroup", req);
    }

    disableGroup(req: DisableGroupRequest): Promise<DisableGroupResult> {
        return this.apiInvoker.invoke_alt<DisableGroupRequest, DisableGroupResult>("Accounts.DisableGroup", req);
    }

    deleteGroup(req: DeleteGroupRequest): Promise<DeleteGroupResult> {
        return this.apiInvoker.invoke_alt<DeleteGroupRequest, DeleteGroupResult>("Accounts.DeleteGroup", req);
    }

    listGroups(req?: ListGroupsRequest): Promise<ListGroupsResult> {
        return this.apiInvoker.invoke_alt<ListGroupsRequest, ListGroupsResult>("Accounts.ListGroups", req);
    }

    listUsersInGroup(req?: ListUsersInGroupRequest): Promise<ListUsersInGroupResult> {
        return this.apiInvoker.invoke_alt<ListUsersInGroupRequest, ListUsersInGroupResult>("Accounts.ListUsersInGroup", req);
    }

    addUserToGroup(req: AddUserToGroupRequest): Promise<AddUserToGroupResult> {
        return this.apiInvoker.invoke_alt<AddUserToGroupRequest, AddUserToGroupResult>("Accounts.AddUserToGroup", req);
    }

    removeUserFromGroup(req: RemoveUserFromGroupRequest): Promise<RemoveUserFromGroupResult> {
        return this.apiInvoker.invoke_alt<RemoveUserFromGroupRequest, RemoveUserFromGroupResult>("Accounts.RemoveUserFromGroup", req);
    }

    addAdminUser(req: AddAdminUserRequest): Promise<AddAdminUserResult> {
        return this.apiInvoker.invoke_alt<AddAdminUserRequest, AddAdminUserResult>("Accounts.AddAdminUser", req);
    }

    removeAdminUser(req: RemoveAdminUserRequest): Promise<RemoveAdminUserResult> {
        return this.apiInvoker.invoke_alt<RemoveAdminUserRequest, RemoveAdminUserResult>("Accounts.RemoveAdminUser", req);
    }

    globalSignOut(req: GlobalSignOutRequest): Promise<GlobalSignOutResult> {
        return this.apiInvoker.invoke_alt<GlobalSignOutRequest, GlobalSignOutResult>("Accounts.GlobalSignOut", req);
    }

    resetPassword(req: ResetPasswordRequest): Promise<ResetPasswordResult> {
        return this.apiInvoker.invoke_alt<ResetPasswordRequest, ResetPasswordResult>("Accounts.ResetPassword", req);
    }
}

export default AccountsClient;
