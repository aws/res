//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop-utils/permission-profile")
@paginated
@readonly
@tags(["virtual-desktop-utils"])
@documentation("Get a list of permission profiles")
operation ListPermissionProfiles {
    input: ListPermissionProfilesRequest
    output: ListPermissionProfilesResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListPermissionProfilesRequest {
    @httpQuery("profileId")
    @documentation("Filter by profileId")
    profileId: res.virtualdesktop#VirtualDesktopPermissionProfileId

    @httpQuery("nextToken")
    @documentation("Pagination token for next page")
    nextToken: String
}

@output
structure ListPermissionProfilesResponse with [res.common#ResListingPayload] {
    @documentation("List of permission profiles")
    listing: VirtualDesktopPermissionProfilesList

    @documentation("Pagination token for next page")
    nextToken: String
}

@documentation("List of permission profiles")
list VirtualDesktopPermissionProfilesList {
    member: res.virtualdesktop#VirtualDesktopPermissionProfile
}
