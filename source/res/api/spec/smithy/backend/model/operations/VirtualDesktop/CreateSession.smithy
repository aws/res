//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/session")
@tags(["virtual-desktop"])
@documentation("Create Virtual Desktop Session ")
operation CreateSession {
    input: CreateSessionRequest
    output: CreateSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure CreateSessionRequest {
    @required
    @documentation("Create session request")
    @jsonName("session")
    session: res.virtualdesktop#VirtualDesktopSession
}

@output
structure CreateSessionResponse {
    @required
    @documentation("Created session response")
    @jsonName("session")
    profile: res.virtualdesktop#VirtualDesktopSession
}
