//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop/shared-permissions")
@paginated
@readonly
@tags(["virtual-desktop"])
@documentation("Get a list of shared permissions")
operation ListSharedPermissions {
    input: ListSharedPermissionsRequest
    output: ListSharedPermissionsResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListSharedPermissionsRequest {
    @httpQuery("nextToken")
    @documentation("Pagination token for next page")
    nextToken: String

    @httpQuery("username")
    @documentation("Username of the shared permissions")
    username: String

    @httpQuery("state")
    @documentation("Filter by state")
    state: String

    @httpQuery("baseOs")
    @documentation("Filter by baseOs")
    baseOs: String

    @httpQuery("sessionName")
    @documentation("Filter by sessionName")
    sessionName: String

    @httpQuery("dateRangeKey")
    @documentation("The attribute name to filter on for date range")
    @suppress(["ShouldHaveUsedTimestamp"])
    dateRangeKey: String

    @httpQuery("after")
    @documentation("Start of the date range")
    after: String

    @httpQuery("before")
    @documentation("End of the date range")
    before: String
}

@output
structure ListSharedPermissionsResponse with [res.common#ResListingPayload] {
    @documentation("List of shared permissions")
    listing: SharedPermissionsList

    @documentation("Pagination token for next page")
    nextToken: String
}

@documentation("List of session permissions")
list SharedPermissionsList {
    member: res.virtualdesktop#VirtualDesktopSessionPermission
}
