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

import { SocaUserInputParamMetadata } from "../../client/data-model";
import { IdeaAppNavigationProps } from "../../navigation/navigation-utils";

export interface IdeaAuthProps extends IdeaAppNavigationProps {}

export interface IdeaAuthState {
    loading: boolean;
    layoutLoading: boolean;
    canSubmit?: boolean;
}

export const AUTH_PARAM_USERNAME: SocaUserInputParamMetadata = {
    name: "username",
    title: "Username",
    description: "Enter your account's username",
    param_type: "text",
    data_type: "str",
    auto_focus: true,
    validate: {
        required: true,
    },
};

export const AUTH_PARAM_PASSWORD: SocaUserInputParamMetadata = {
    name: "password",
    title: "Password",
    description: "Enter your account's password",
    param_type: "password",
    data_type: "str",
    validate: {
        required: true,
    },
};

export const AUTH_PARAM_VERIFICATION_CODE: SocaUserInputParamMetadata = {
    name: "verificationCode",
    title: "Verification Code",
    description: "Enter the verification code",
    param_type: "text",
    data_type: "str",
    auto_focus: true,
    validate: {
        required: true,
    },
};

export const AUTH_PARAM_NEW_PASSWORD: SocaUserInputParamMetadata = {
    name: "password",
    title: "New Password",
    description: "Enter password",
    param_type: "new-password",
    data_type: "str",
    auto_focus: true,
    validate: {
        required: true,
    },
};
