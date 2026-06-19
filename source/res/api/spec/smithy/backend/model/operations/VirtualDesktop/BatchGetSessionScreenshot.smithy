//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/session-screenshots")
@tags(["virtual-desktop"])
@documentation("Batch Get Session Screenshots")
operation BatchGetSessionScreenshot {
    input: BatchGetSessionScreenshotRequest
    output: BatchGetSessionScreenshotResponse
    errors: [
        BadRequestException
        InternalServiceException
        ForbiddenException
        LimitExceededException
    ]
}

@input
structure BatchGetSessionScreenshotRequest {
    @required
    @documentation("List of sessions to get screenshots for")
    @length(min: 1, max: 1000)
    screenshots: res.virtualdesktop#VirtualDesktopSessionScreenshotList
}

@output
structure BatchGetSessionScreenshotResponse {
    @required
    @documentation("List of screenshots that were successfully retrieved")
    @jsonName("successful_list")
    successfulList: res.virtualdesktop#VirtualDesktopSessionScreenshotList

    @required
    @documentation("List of screenshots that failed to be retrieved")
    @jsonName("unsuccessful_list")
    unsuccessfulList: BatchGetSessionScreenshotFailureList
}

structure BatchGetSessionScreenshotFailure {
    @required
    @documentation("Screenshot request that failed")
    screenshot: res.virtualdesktop#VirtualDesktopSessionScreenshot

    @required
    @documentation("Error code for the failure")
    @jsonName("error_code")
    errorCode: BatchOperationErrorCode

    @required
    @documentation("Error message describing why the screenshot could not be retrieved")
    message: String
}

list BatchGetSessionScreenshotFailureList {
    member: BatchGetSessionScreenshotFailure
}
