//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/sessions/start")
@tags(["virtual-desktop"])
@documentation("Batch Start Sessions")
operation BatchStartSession {
    input: BatchStartSessionRequest
    output: BatchStartSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
        ForbiddenException
        LimitExceededException
    ]
}

@input
structure BatchStartSessionRequest {
    @required
    @documentation("List of sessions to start")
    // Setting maximum due to EC2 request throttling
    @length(min: 1, max: 1000)
    sessions: res.virtualdesktop#VirtualDesktopSessionList
}

@output
structure BatchStartSessionResponse {
    @required
    @documentation("List of sessions that were successfully started")
    @jsonName("successful-list")
    successfulList: res.virtualdesktop#VirtualDesktopSessionList

    @required
    @documentation("List of sessions that failed to start")
    @jsonName("unsuccessful-list")
    unsuccessfulList: BatchStartSessionFailureList
}

structure BatchStartSessionFailure {
    @required
    @documentation("Session that failed to start")
    session: res.virtualdesktop#VirtualDesktopSession

    @required
    @documentation("Error code for the failure")
    @jsonName("error-code")
    errorCode: BatchOperationErrorCode

    @required
    @documentation("Error message describing why the session failed to start")
    message: String
}

list BatchStartSessionFailureList {
    member: BatchStartSessionFailure
}
