//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/sessions/delete")
@tags(["virtual-desktop"])
@documentation("Batch Delete Sessions")
operation BatchDeleteSession {
    input: BatchDeleteSessionRequest
    output: BatchDeleteSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
        ForbiddenException
        LimitExceededException
    ]
}

@input
structure BatchDeleteSessionRequest {
    @required
    @documentation("List of sessions to delete")
    // Setting maximum due to EC2 request throttling
    @length(min: 1, max: 1000)
    sessions: res.virtualdesktop#VirtualDesktopSessionList
}

@output
structure BatchDeleteSessionResponse {
    @required
    @documentation("List of sessions that were successfully deleted")
    @jsonName("successful-list")
    successfulList: res.virtualdesktop#VirtualDesktopSessionList

    @required
    @documentation("List of sessions that failed to delete")
    @jsonName("unsuccessful-list")
    unsuccessfulList: BatchDeleteSessionFailureList
}

structure BatchDeleteSessionFailure {
    @required
    @documentation("Session that failed to delete")
    session: res.virtualdesktop#VirtualDesktopSession

    @required
    @documentation("Error code for the failure")
    @jsonName("error-code")
    errorCode: BatchOperationErrorCode

    @required
    @documentation("Error message describing why the session failed to delete")
    message: String
}

list BatchDeleteSessionFailureList {
    member: BatchDeleteSessionFailure
}
