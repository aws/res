//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.dcvsessionmanagement

use res#BadRequestException
use res#InternalServiceException

@http(method: "PUT", uri: "/sessionPermissions")
@tags(["sessions"])
@documentation("Updates DCV session permissions")
operation UpdateSessionPermissions {
    input: UpdateSessionPermissionsRequest
    output: UpdateSessionPermissionsResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure UpdateSessionPermissionsRequest {
    @required
    @length(min: 1)
    @documentation("DCV Sessions to update permissions for")
    sessions: UpdateSessionPermissionsRequestDataList
}

list UpdateSessionPermissionsRequestDataList {
    member: UpdateSessionPermissionsRequestData
}

structure UpdateSessionPermissionsRequestData {
    @required
    @length(min: 1)
    @documentation("The session id")
    @jsonName("session_id")
    sessionId: String

    @required
    @length(min: 1)
    @documentation("The session owner")
    @jsonName("owner")
    owner: String

    @required
    @length(min: 1)
    @documentation("The permissions file base64 encoded")
    @jsonName("permissions_file")
    permissionsFile: String
}

@output
structure UpdateSessionPermissionsResponse {
    @required
    @documentation("The array of sessions with permissions successfully updated")
    @jsonName("successful_list")
    successfulList: UpdateSessionPermissionsSuccessfulResponseList

    @required
    @documentation("The array of sessions with permissions that failed to update")
    @jsonName("unsuccessful_list")
    unsuccessfulList: UpdateSessionPermissionsUnsuccessfulResponseList
}

list UpdateSessionPermissionsSuccessfulResponseList {
    member: UpdateSessionPermissionsSuccessfulResponse
}

list UpdateSessionPermissionsUnsuccessfulResponseList {
    member: UpdateSessionPermissionsUnsuccessfulResponse
}

structure UpdateSessionPermissionsSuccessfulResponse {
    @required
    @documentation("The session id")
    @jsonName("session_id")
    sessionId: String
}

structure UpdateSessionPermissionsUnsuccessfulResponse {
    @required
    @documentation("The session id")
    @jsonName("session_id")
    sessionId: String

    @required
    @documentation("The failure reason")
    @jsonName("failure_reason")
    failureReason: String
}
