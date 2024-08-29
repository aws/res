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

export const Constants = {
    ADMIN_ROLE: 'admin',
    USER_ROLE: 'user',
    MODULE_VIRTUAL_DESKTOP_CONTROLLER: "virtual-desktop-controller",
    MODULE_SCHEDULER: "scheduler",
    MODULE_DIRECTORY_SERVICE: "directoryservice",
    MODULE_IDENTITY_PROVIDER: "identity-provider",
    MODULE_SHARED_STORAGE: "shared-storage",
    MODULE_BASTION_HOST: "bastion-host",
    MODULE_CLUSTER: "cluster",
    MODULE_CLUSTER_MANAGER: "cluster-manager",
    MODULE_GLOBAL_SETTINGS: "global-settings",

    NODE_TYPE_APP: "app",
    NODE_TYPE_INFRA: "infra",

    MODULE_TYPE_APP: "app",
    MODULE_TYPE_STACK: "stack",
    MODULE_TYPE_CONFIG: "config",

    ADMIN_ZONE_LINK_TEXT: "ADMIN ZONE",

    SHARED_STORAGE_PROVIDER_EFS: "efs",
    SHARED_STORAGE_PROVIDER_FSX_CACHE: "fsx_cache",
    SHARED_STORAGE_PROVIDER_FSX_LUSTRE: "fsx_lustre",
    SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP: "fsx_netapp_ontap",
    SHARED_STORAGE_PROVIDER_FSX_OPENZFS: "fsx_openzfs",
    SHARED_STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER: "fsx_windows_file_server",
    SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP_SECURITY_TYPE_UNIX: "UNIX",
    SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP_SECURITY_TYPE_MIXED: "MIXED",
    SHARED_STORAGE_PROVIDER_FSX_NETAPP_ONTAP_SECURITY_TYPE_NTFS: "NTFS",
    SHARED_STORAGE_PROVIDER_S3_BUCKET: "s3_bucket",

    SHARED_STORAGE_MODE_READ_ONLY: "R",
    SHARED_STORAGE_MODE_READ_WRITE: "R/W",

    SHARED_STORAGE_NO_CUSTOM_PREFIX: "NO_CUSTOM_PREFIX",
    SHARED_STORAGE_CUSTOM_PROJECT_NAME_PREFIX: "PROJECT_NAME_PREFIX",
    SHARED_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX: "PROJECT_NAME_AND_USERNAME_PREFIX",

    FSX_NETAPP_ONTAP_DEPLOYMENT_TYPE_MULTI_AZ: "MULTI_AZ_1",
    FSX_NETAPP_ONTAP_DEPLOYMENT_TYPE_SINGLE_AZ: "SINGLE_AZ_1",

    FSX_VOLUME_ONTAP_SECURITY_STYLE_UNIX: "UNIX",
    FSX_VOLUME_ONTAP_SECURITY_STYLE_NTFS: "NTFS",
    FSX_VOLUME_ONTAP_SECURITY_STYLE_MIXED: "MIXED",

    SPLIT_PANEL_I18N_STRINGS: {
        preferencesTitle: "Split panel preferences",
        preferencesPositionLabel: "Split panel position",
        preferencesPositionDescription: "Choose the default split panel position for the service.",
        preferencesPositionSide: "Side",
        preferencesPositionBottom: "Bottom",
        preferencesConfirm: "Confirm",
        preferencesCancel: "Cancel",
        closeButtonAriaLabel: "Close panel",
        openButtonAriaLabel: "Open panel",
        resizeHandleAriaLabel: "Resize split panel",
    },

    ServiceWorker: {
        SKIP_WAITING: "SKIP_WAITING",
        IDEA_AUTH_INIT: "IDEA.Auth.InitializeAuth",
        IDEA_AUTH_TOKEN_CLAIMS: "IDEA.Auth.GetTokenClaims",
        IDEA_AUTH_IS_LOGGED_IN: "IDEA.Auth.IsLoggedIn",
        IDEA_AUTH_LOGOUT: "IDEA.Auth.Logout",
        IDEA_AUTH_DEBUG: "IDEA.Auth.Debug",
        IDEA_AUTH_ACCESS_TOKEN: "IDEA.Auth.GetAccessToken",
        IDEA_API_INVOCATION: "IDEA.InvokeApi",
        IDEA_HTTP_FETCH: "IDEA.HttpFetch",
        IDEA_CLIENT_ID: "IDEA.ClientId",
        IDEA_SW_INIT: "IDEA.InitializeServiceWorker",
        IDEA_GET_SW_INIT: "IDEA.GetServiceWorkerInitialized",
    },

    ROLE_NAME_REGEX: "^[a-zA-Z0-9-_ ]{3,36}$",
    ROLE_NAME_ERROR_MESSAGE: "Only use alphabets, numbers, spaces, dashes (-), or underscores (_) for role name. Must be between 3 and 36 characters long.",
    ROLE_DESC_REGEX: "^[a-zA-Z0-9-_ ]{0,50}$",
    ROLE_DESC_ERROR_MESSAGE: "Only use alphabets, numbers, spaces, dashes (-), or underscores (_) for role description. Can be up to 50 characters long.",
};

export const ErrorCodes = {
    MODULE_NOT_FOUND: "MODULE_NOT_FOUND",
};
