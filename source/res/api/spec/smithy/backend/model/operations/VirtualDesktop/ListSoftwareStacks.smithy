//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop/software-stack")
@paginated
@readonly
@tags(["virtual-desktop"])
@documentation("Get a list of software stacks")
operation ListSoftwareStacks {
    input: ListSoftwareStacksRequest
    output: ListSoftwareStacksResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListSoftwareStacksRequest {
    @httpQuery("projectId")
    @documentation("Filter by projectId")
    projectId: String

    @httpQuery("baseOs")
    @documentation("Filter by baseOs")
    baseOs: String

    @httpQuery("softwareStackName")
    @documentation("Filter by softwareStackName")
    softwareStackName: String

    @httpQuery("nextToken")
    @documentation("Pagination token for next page")
    nextToken: String
}

@output
structure ListSoftwareStacksResponse with [res.common#ResListingPayload] {
    @documentation("List of software stacks")
    listing: VirtualDesktopSoftwareStacksList

    @documentation("Pagination token for next page")
    nextToken: String
}

@documentation("List of software stacks")
list VirtualDesktopSoftwareStacksList {
    member: res.virtualdesktop#VirtualDesktopSoftwareStack
}
