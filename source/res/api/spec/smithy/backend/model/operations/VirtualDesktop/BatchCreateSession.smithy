//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/sessions")
@tags(["virtual-desktop"])
@documentation("Batch Create Sessions")
operation BatchCreateSession {
    input: BatchCreateSessionRequest
    output: BatchCreateSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
        ForbiddenException
        LimitExceededException
    ]
}

@input
structure BatchCreateSessionRequest {
    @required
    @documentation("List of sessions to create")
    // Setting maximum due to EC2 request throttling
    @length(min: 1, max: 1000)
    sessions: res.virtualdesktop#VirtualDesktopSessionList
}

@output
structure BatchCreateSessionResponse {
    @required
    @documentation("List of sessions that were successfully created")
    @jsonName("successful_list")
    successfulList: res.virtualdesktop#VirtualDesktopSessionList

    @required
    @documentation("List of sessions that failed to create")
    @jsonName("unsuccessful_list")
    unsuccessfulList: BatchCreateSessionFailureList
}

structure BatchCreateSessionFailure {
    @required
    @documentation("Session that failed to create")
    session: res.virtualdesktop#VirtualDesktopSession

    @required
    @documentation("Error code for the failure")
    @jsonName("error_code")
    errorCode: BatchOperationErrorCode

    @required
    @documentation("Error message describing why the session failed to create")
    message: String
}

list BatchCreateSessionFailureList {
    member: BatchCreateSessionFailure
}
