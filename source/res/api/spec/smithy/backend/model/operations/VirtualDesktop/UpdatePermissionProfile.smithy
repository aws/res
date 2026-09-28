//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "PUT", uri: "/res/virtual-desktop/permission-profiles/{profile_id}")
@tags(["virtual-desktop"])
@documentation("Update Permission Profile")
operation UpdatePermissionProfile {
    input: UpdatePermissionProfileRequest
    output: UpdatePermissionProfileResponse
    errors: [
        BadRequestException
        InternalServiceException
        NotFoundException
    ]
}

@input
structure UpdatePermissionProfileRequest {
    @required
    @httpLabel
    @suppress(["CamelCase"])
    profile_id: res.virtualdesktop#VirtualDesktopPermissionProfileId

    @required
    @documentation("Update virtual desktop permission profile request")
    @jsonName("profile")
    profile: res.virtualdesktop#VirtualDesktopPermissionProfile
}

@output
structure UpdatePermissionProfileResponse {
    @required
    @documentation("Update virtual desktop permission profile response")
    @jsonName("profile")
    profile: res.virtualdesktop#VirtualDesktopPermissionProfile
}
