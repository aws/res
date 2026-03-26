//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/permission-profile")
@tags(["virtual-desktop"])
@documentation("Create Permission Profile")
operation CreatePermissionProfile {
    input: CreatePermissionProfileRequest
    output: CreatePermissionProfileResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure CreatePermissionProfileRequest {
    @required
    @documentation("Create permission profile request")
    @jsonName("profile")
    profile: res.virtualdesktop#VirtualDesktopPermissionProfile
}

@output
structure CreatePermissionProfileResponse {
    @required
    @documentation("Create permission profile response")
    @jsonName("profile")
    profile: res.virtualdesktop#VirtualDesktopPermissionProfile
}
