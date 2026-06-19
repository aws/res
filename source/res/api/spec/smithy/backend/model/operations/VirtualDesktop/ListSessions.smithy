//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop/session")
@paginated
@readonly
@tags(["virtual-desktop"])
@documentation("Get a list of sessions")
operation ListSessions {
    input: ListSessionsRequest
    output: ListSessionsResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListSessionsRequest {
    @httpQuery("state")
    @documentation("Filter by state")
    state: String

    @httpQuery("baseOs")
    @documentation("Filter by baseOs")
    baseOs: String

    @httpQuery("sessionName")
    @documentation("Filter by sessionName")
    sessionName: String

    @httpQuery("stackId")
    @documentation("Filter by stackId")
    stackId: String

    @httpQuery("dateRangeKey")
    @documentation("The attribute name to filter on for date range")
    @suppress(["ShouldHaveUsedTimestamp"])
    dateRangeKey: String

    @httpQuery("after")
    @documentation("Start of the date range")
    after: String

    @httpQuery("before")
    @documentation("End of the date range ")
    before: String

    @httpQuery("nextToken")
    @documentation("Pagination token for next page")
    nextToken: String

    @httpQuery("owner")
    @documentation("Filter by owner")
    owner: String
}

@output
structure ListSessionsResponse with [res.common#ResListingPayload] {
    @documentation("List of sessions")
    listing: res.virtualdesktop#VirtualDesktopSessionList

    @documentation("Pagination token for next page")
    nextToken: String
}
