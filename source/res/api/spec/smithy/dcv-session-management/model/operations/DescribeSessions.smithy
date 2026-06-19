//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.dcvsessionmanagement

use res#BadRequestException
use res#InternalServiceException

@http(method: "POST", uri: "/describeSessions")
@tags(["sessions"])
@documentation("Describes DCV sessions")
operation DescribeSessions {
    input: DescribeSessionsRequest
    output: DescribeSessionsResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure DescribeSessionsRequest {
    @required
    @length(min: 1)
    @documentation("Sessions to describe")
    sessions: DescribeSessionsRequestDataList
}

list DescribeSessionsRequestDataList {
    member: DescribeSessionsRequestData
}

structure DescribeSessionsRequestData {
    @required
    @length(min: 1)
    @documentation("The RES session id")
    @jsonName("session_id")
    sessionId: String

    @required
    @length(min: 1)
    @documentation("The session owner")
    @jsonName("owner")
    owner: String
}

@output
structure DescribeSessionsResponse {
    @required
    @documentation("The array of sessions successfully described")
    @jsonName("successful_list")
    successfulList: DescribeSessionsSuccessfulResponseList

    @required
    @documentation("The array of sessions that failed to describe")
    @jsonName("unsuccessful_list")
    unsuccessfulList: DescribeSessionsUnsuccessfulResponseList
}

list DescribeSessionsSuccessfulResponseList {
    member: DescribeSessionsSuccessfulResponse
}

list DescribeSessionsUnsuccessfulResponseList {
    member: DescribeSessionsUnsuccessfulResponse
}

structure DescribeSessionsSuccessfulResponse {
    @required
    @documentation("The session id")
    @jsonName("session_id")
    sessionId: String

    @required
    @documentation("The number of active connections to the session")
    @jsonName("num_of_connections")
    numOfConnections: Integer
}

structure DescribeSessionsUnsuccessfulResponse {
    @required
    @documentation("The session id")
    @jsonName("session_id")
    sessionId: String

    @required
    @documentation("The failure reason")
    @jsonName("failure_reason")
    failureReason: String
}
