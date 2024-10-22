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

    SHARED_STORAGE_FILE_BROWSER_FEATURE_TITLE: "File browser",
    SHARED_STORAGE_FILE_BROWSER_KEY: "enable_file_browser",

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
    SHARED_STORAGE_HOME_MOUNT_DIRECTORY: "/home",
    SHARED_STORAGE_EBS_VOLUME: "ebs_volume",

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
    DCV_SETTINGS_DEFAULT_OWNER_PROFILE_ID: "admin_profile",
    DCV_SETTINGS_DESKTOP_SETTINGS: {
        column_one: ["display", "pointer", "mouse", "audio_out", "unsupervised_access"],
        column_two: ["keyboard", "keyboard_sas", "screenshot"],
        column_three: ["clipboard_paste", "clipboard_copy", "file_upload", "file_download"],
        getAllColumns: function () {
            return [...this.column_one, ...this.column_two, ...this.column_three]
        }
    },
    DCV_SETTINGS_DESKTOP_ADVANCED_SETTINGS: {
        column_one: ["audio_in", "printer"],
        column_two: ["usb", "smartcard", "stylus"],
        column_three: ["webcam", "touch", "gamepad"],
        getAllColumns: function () {
            return [...this.column_one, ...this.column_two, ...this.column_three]
        }
    },
    BUDGET_NOT_FOUND: "BUDGET_NOT_FOUND",
    DIVIDER_COLOR: "#d1d5db",
  };

export const ErrorCodes = {
    MODULE_NOT_FOUND: "MODULE_NOT_FOUND",
    UNAUTHORIZED_ACCESS: "UNAUTHORIZED_ACCESS",
    DISABLED_FEATURE: "DISABLED_FEATURE",
    NOT_A_TEXT_FILE: "NOT_A_TEXT_FILE",
};

export const ErrorMessages = {
    PERMISSION_DENIED: "Permission Denied",
    DISABLED_FILE_BROWSER_BY_ADMIN: "The File browser has been disabled. Contact your administrator to request data access via the web portal.",
    DISABLED_FILE_BROWSER_NEW_USER: "Your personal home directory has not yet been created. File browsing is limited to the global home file system. Launch at least one Linux virtual desktop session with a project using the global home file system to have a personal home directory created for you.",
};
