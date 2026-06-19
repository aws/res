//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/session-connections")
@tags(["virtual-desktop"])
@documentation("Get connection information for a virtual desktop session")
operation GetSessionConnection {
    input: GetSessionConnectionRequest
    output: GetSessionConnectionResponse
    errors: [
        BadRequestException
        InternalServiceException
        ForbiddenException
    ]
}

@input
structure GetSessionConnectionRequest {
    @required
    @documentation("Session connection information")
    connection: res.virtualdesktop#VirtualDesktopSessionConnection
}

@output
structure GetSessionConnectionResponse {
    @required
    @documentation("Session connection information with endpoint and access token")
    connection: res.virtualdesktop#VirtualDesktopSessionConnection
}
