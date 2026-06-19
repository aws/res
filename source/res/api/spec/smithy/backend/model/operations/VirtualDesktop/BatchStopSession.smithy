//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/sessions/stop")
@tags(["virtual-desktop"])
@documentation("Batch Stop Sessions")
operation BatchStopSession {
    input: BatchStopSessionRequest
    output: BatchStopSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
        ForbiddenException
        LimitExceededException
    ]
}

@input
structure BatchStopSessionRequest {
    @required
    @documentation("List of sessions to stop")
    // Setting maximum due to EC2 request throttling
    @length(min: 1, max: 1000)
    sessions: res.virtualdesktop#VirtualDesktopSessionList
}

@output
structure BatchStopSessionResponse {
    @required
    @documentation("List of sessions that were successfully stopped")
    successfulList: res.virtualdesktop#VirtualDesktopSessionList

    @required
    @documentation("List of sessions that failed to stop")
    unsuccessfulList: BatchStopSessionFailureList
}

structure BatchStopSessionFailure {
    @required
    @documentation("Session that failed to stop")
    session: res.virtualdesktop#VirtualDesktopSession

    @required
    @documentation("Error code for the failure")
    errorCode: BatchOperationErrorCode

    @required
    @documentation("Error message describing why the session failed to stop")
    message: String
}

list BatchStopSessionFailureList {
    member: BatchStopSessionFailure
}
