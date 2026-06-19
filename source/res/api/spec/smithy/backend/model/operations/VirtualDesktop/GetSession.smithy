//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop/session/{resSessionId}")
@readonly
@tags(["virtual-desktop"])
@documentation("Get details of a session")
operation GetSession {
    input: GetSessionRequest
    output: GetSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure GetSessionRequest {
    @documentation("Session identifier")
    @httpLabel
    @required
    @length(min: 1)
    resSessionId: String

    @documentation("Owner of the session")
    @httpQuery("owner")
    @required
    @length(min: 1)
    owner: String
}

@output
structure GetSessionResponse {
    session: res.virtualdesktop#VirtualDesktopSession
}
