//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.dcvsessionmanagement

use res#BadRequestException
use res#InternalServiceException

@sensitive
string SensitiveString

@http(method: "POST", uri: "/sessionScreenshots")
@tags(["sessions"])
@documentation("Gets DCV session screenshots")
operation GetSessionScreenshots {
    input: GetSessionScreenshotsRequest
    output: GetSessionScreenshotsResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure GetSessionScreenshotsRequest {
    @required
    @documentation("The username of the screenshots requester.")
    @length(min: 1)
    requester: String

    @required
    @documentation("Sessions to get screenshots for")
    sessions: GetSessionScreenshotRequestDataList
}

list GetSessionScreenshotRequestDataList {
    member: GetSessionScreenshotRequestData
}

structure GetSessionScreenshotRequestData {
    @required
    @documentation("The RES session id")
    @jsonName("session_id")
    @length(min: 1)
    sessionId: String
}

@output
structure GetSessionScreenshotsResponse {
    @required
    @documentation("The array of session screenshots successfully retrieved")
    @jsonName("successful_list")
    successfulList: GetSessionScreenshotSuccessfulResponseList

    @required
    @documentation("The array of session screenshots that cannot be retrieved")
    @jsonName("unsuccessful_list")
    unsuccessfulList: GetSessionScreenshotUnsuccessfulResponseList
}

list GetSessionScreenshotSuccessfulResponseList {
    member: GetSessionScreenshotSuccessfulResponse
}

list GetSessionScreenshotUnsuccessfulResponseList {
    member: GetSessionScreenshotUnsuccessfulResponse
}

structure GetSessionScreenshotSuccessfulResponse {
    @required
    @documentation("The DCV session screenshot")
    @jsonName("session_screenshot")
    sessionScreenshot: SessionScreenshot
}

structure GetSessionScreenshotUnsuccessfulResponse {
    @required
    @documentation("The data related to the failure request")
    @jsonName("get_session_screenshot_request_data")
    getSessionScreenshotRequestData: GetSessionScreenshotRequestData

    @required
    @documentation("The failure reason")
    @jsonName("failure_reason")
    failureReason: String
}

structure SessionScreenshot {
    @required
    @documentation("The id of the session")
    @jsonName("session_id")
    @length(min: 1)
    sessionId: String

    @required
    @documentation("The array of session screenshots")
    images: SessionScreenshotImageList
}

list SessionScreenshotImageList {
    member: SessionScreenshotImage
}

structure SessionScreenshotImage {
    @required
    @documentation("The image format. Supported formats: jpeg, png")
    @length(min: 1)
    format: String

    @required
    @documentation("The base64 image data")
    @length(min: 1)
    data: SensitiveString

    @required
    @documentation("Timestamp when the screenshot was created")
    @jsonName("created_on")
    @length(min: 1)
    createdOnStr: String

    @required
    @documentation("Tells if the image belongs to the primary screen")
    primary: Boolean
}
