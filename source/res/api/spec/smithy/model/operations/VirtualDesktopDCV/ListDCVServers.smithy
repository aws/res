//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop-dcv/server")
@paginated
@readonly
@tags(["virtual-desktop-dcv"])
@documentation("List DCV Servers")
operation ListDCVServers {
    input: ListDCVServersRequest
    output: ListDCVServersResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListDCVServersRequest {
    @httpQuery("nextToken")
    @documentation("Pagination token for next page")
    nextToken: String
}

@output
structure ListDCVServersResponse {
    @documentation("DCV servers response data")
    response: Document

    @documentation("Pagination token for next page")
    nextToken: String
}
