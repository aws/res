//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/sessions/reboot")
@tags(["virtual-desktop"])
@documentation("Batch Reboot Sessions")
operation BatchRebootSession {
    input: BatchRebootSessionRequest
    output: BatchRebootSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
        ForbiddenException
        LimitExceededException
    ]
}

@input
structure BatchRebootSessionRequest {
    @required
    @documentation("List of sessions to reboot")
    // Setting maximum due to EC2 request throttling
    @length(min: 1, max: 1000)
    sessions: res.virtualdesktop#VirtualDesktopSessionList
}

@output
structure BatchRebootSessionResponse {
    @required
    @documentation("List of sessions that were successfully rebooted")
    @jsonName("successful-list")
    successfulList: res.virtualdesktop#VirtualDesktopSessionList

    @required
    @documentation("List of sessions that failed to reboot")
    @jsonName("unsuccessful-list")
    unsuccessfulList: BatchRebootSessionFailureList
}

structure BatchRebootSessionFailure {
    @required
    @documentation("Session that failed to reboot")
    session: res.virtualdesktop#VirtualDesktopSession

    @required
    @documentation("Error code for the failure")
    @jsonName("error-code")
    errorCode: BatchOperationErrorCode

    @required
    @documentation("Error message describing why the session failed to reboot")
    message: String
}

list BatchRebootSessionFailureList {
    member: BatchRebootSessionFailure
}
