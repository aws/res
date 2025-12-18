//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop-dcv/session")
@paginated
@readonly
@tags(["virtual-desktop-dcv"])
@documentation("Retrieve details of DCV sessions")
operation BatchGetDCVSessions {
    input: BatchGetDCVSessionsRequest
    output: BatchGetDCVSessionsResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure BatchGetDCVSessionsRequest {
    @documentation("List of sessions to retrieve DCV sessions of")
    sessions: res.virtualdesktop#VirtualDesktopSessionList

    @documentation("Pagination token for next page")
    nextToken: String
}

@output
structure BatchGetDCVSessionsResponse {
    @documentation("DCV sessions response data")
    response: Document

    @documentation("Pagination token for next page")
    nextToken: String
}
