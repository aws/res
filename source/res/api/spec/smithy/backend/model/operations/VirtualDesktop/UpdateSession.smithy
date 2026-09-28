//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "PUT", uri: "/res/virtual-desktop/sessions/{res_session_id}")
@tags(["virtual-desktop"])
@documentation("Update Session")
operation UpdateSession {
    input: UpdateSessionRequest
    output: UpdateSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
        NotFoundException
    ]
}

@input
structure UpdateSessionRequest {
    @documentation("Session identifier")
    @httpLabel
    @required
    @length(min: 1)
    @suppress(["CamelCase"])
    res_session_id: String

    @documentation("Update virtual desktop session request")
    @required
    session: res.virtualdesktop#VirtualDesktopSession
}

@output
structure UpdateSessionResponse {
    @required
    @documentation("Update virtual desktop session response")
    session: res.virtualdesktop#VirtualDesktopSession
}
