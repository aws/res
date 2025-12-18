//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop-utils/permission-profile/{profileId}")
@readonly
@tags(["virtual-desktop-utils"])
@documentation("Get details of a permission profile")
operation GetPermissionProfile {
    input: GetPermissionProfileRequest
    output: GetPermissionProfileResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure GetPermissionProfileRequest {
    @httpLabel
    @required
    profileId: res.virtualdesktop#VirtualDesktopPermissionProfileId
}

@output
structure GetPermissionProfileResponse with [res.common#ResListingPayload] {
    @documentation("Permission profile")
    profile: res.virtualdesktop#VirtualDesktopPermissionProfile
}
