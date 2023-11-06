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
    InitiateAuthRequest,
    InitiateAuthResult,
    RespondToAuthChallengeRequest,
    RespondToAuthChallengeResult,
    ForgotPasswordRequest,
    ForgotPasswordResult,
    ChangePasswordRequest,
    ChangePasswordResult,
    ConfirmForgotPasswordRequest,
    ConfirmForgotPasswordResult,
    SignOutRequest,
    SignOutResult,
    GlobalSignOutRequest,
    GlobalSignOutResult,
    GetUserResult,
    GetUserRequest,
    GetUserPrivateKeyRequest,
    GetUserPrivateKeyResult,
    AddUserToGroupRequest,
    AddUserToGroupResult,
    RemoveUserFromGroupRequest,
    RemoveUserFromGroupResult,
    GetGroupRequest,
    GetGroupResult,
    GetModuleInfoRequest,
    GetModuleInfoResult,
    ListUsersInGroupRequest,
    ListUsersInGroupResult,
    ConfigureSSORequest,
    ConfigureSSOResponse
} from "./data-model";

import { JwtTokenClaims } from "../common/token-utils";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface AuthClientProps extends IdeaBaseClientProps {
    baseUrl: string;
    apiContextPath: string;
    serviceWorkerRegistration?: ServiceWorkerRegistration;
}

/**
 * Auth Client
 */
class AuthClient extends IdeaBaseClient<AuthClientProps> {
    getModuleInfo(): Promise<GetModuleInfoRequest> {
        return this.apiInvoker.invoke_alt<GetModuleInfoRequest, GetModuleInfoResult>("App.GetModuleInfo", {}, true);
    }

    initiateAuth(req: InitiateAuthRequest): Promise<InitiateAuthResult> {
        return this.apiInvoker.invoke_alt<InitiateAuthRequest, InitiateAuthResult>("Auth.InitiateAuth", req, true);
    }

    logout() {
        return this.apiInvoker.logout();
    }

    isLoggedIn(): Promise<boolean> {
        return this.apiInvoker.isLoggedIn();
    }

    getAccessToken(): Promise<string> {
        return this.apiInvoker.getAccessToken();
    }

    debug() {
        return this.apiInvoker.debug();
    }

    getSWInitialized(): Promise<boolean> {
        return this.apiInvoker.getSWInitialized();
    }

    getClientId(): Promise<string> {
        return this.apiInvoker.getClientId();
    }

    getClaims(): Promise<JwtTokenClaims> {
        return this.apiInvoker.getClaims();
    }

    respondToAuthChallenge(req: RespondToAuthChallengeRequest): Promise<RespondToAuthChallengeResult> {
        return this.apiInvoker.invoke_alt<RespondToAuthChallengeRequest, RespondToAuthChallengeResult>("Auth.RespondToAuthChallenge", req, true);
    }

    forgotPassword(req: ForgotPasswordRequest): Promise<ForgotPasswordResult> {
        return this.apiInvoker.invoke_alt<ForgotPasswordRequest, ForgotPasswordResult>("Auth.ForgotPassword", req, true);
    }

    confirmForgotPassword(req: ConfirmForgotPasswordRequest): Promise<ConfirmForgotPasswordResult> {
        return this.apiInvoker.invoke_alt<ConfirmForgotPasswordRequest, ConfirmForgotPasswordResult>("Auth.ConfirmForgotPassword", req, true);
    }

    signOut(req: SignOutRequest): Promise<SignOutResult> {
        return this.apiInvoker.invoke_alt<SignOutRequest, SignOutResult>("Auth.SignOut", req);
    }

    globalSignOut(req: GlobalSignOutRequest): Promise<GlobalSignOutResult> {
        return this.apiInvoker.invoke_alt<GlobalSignOutRequest, GlobalSignOutResult>("Auth.GlobalSignOut", req);
    }

    changePassword(req: ChangePasswordRequest): Promise<ChangePasswordResult> {
        return this.apiInvoker.invoke_alt<ChangePasswordRequest, ChangePasswordResult>("Auth.ChangePassword", req);
    }

    getUser(): Promise<GetUserResult> {
        return this.apiInvoker.invoke_alt<GetUserRequest, GetUserResult>("Auth.GetUser", {});
    }

    getUserPrivateKey(request: GetUserPrivateKeyRequest): Promise<GetUserPrivateKeyResult> {
        return this.apiInvoker.invoke_alt<GetUserPrivateKeyRequest, GetUserPrivateKeyResult>("Auth.GetUserPrivateKey", request);
    }

    getGroup(request: GetGroupRequest): Promise<GetGroupResult> {
        return this.apiInvoker.invoke_alt<GetGroupRequest, GetGroupResult>("Auth.GetGroup", request);
    }

    addUserToGroup(request: AddUserToGroupRequest): Promise<AddUserToGroupResult> {
        return this.apiInvoker.invoke_alt<AddUserToGroupRequest, AddUserToGroupResult>("Auth.AddUserToGroup", request);
    }

    removeUserFromGroup(request: RemoveUserFromGroupRequest): Promise<RemoveUserFromGroupResult> {
        return this.apiInvoker.invoke_alt<RemoveUserFromGroupRequest, RemoveUserFromGroupResult>("Auth.RemoveUserFromGroup", request);
    }

    listUsersInGroup(request: ListUsersInGroupRequest): Promise<ListUsersInGroupResult> {
        return this.apiInvoker.invoke_alt<ListUsersInGroupRequest, ListUsersInGroupResult>("Auth.ListUsersInGroup", request);
    }
    configureSSO(request: ConfigureSSORequest): Promise<ConfigureSSOResponse> {
        return this.apiInvoker.invoke_alt<ConfigureSSORequest, ConfigureSSOResponse>("Auth.ConfigureSSO", request);

    }
}

export default AuthClient;
