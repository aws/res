//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop/session-permission")
@paginated
@readonly
@tags(["virtual-desktop"])
@documentation("Get a list of session permissions")
operation ListSessionPermissions {
    input: ListSessionPermissionsRequest
    output: ListSessionPermissionsResponse
    errors: [
        BadRequestException
        InternalServiceException
        NotFoundException
    ]
}

@input
structure ListSessionPermissionsRequest {
    @required
    @length(min: 1)
    @httpQuery("resSessionId")
    @documentation("Filter by resSessionId")
    resSessionId: String

    @httpQuery("nextToken")
    @documentation("Pagination token for next page")
    nextToken: String
}

@output
structure ListSessionPermissionsResponse with [res.common#ResListingPayload] {
    @documentation("List of session permissions")
    listing: SessionPermissionsList

    @documentation("Pagination token for next page")
    nextToken: String
}

@documentation("List of session permissions")
list SessionPermissionsList {
    member: res.virtualdesktop#VirtualDesktopSessionPermission
}
