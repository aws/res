//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.dcvsessionmanagement

use res#BadRequestException
use res#ForbiddenException
use res#InternalServiceException

@http(method: "POST", uri: "/sessionConnectionData/{sessionId}/{username}")
@tags(["sessions"])
@documentation("Gets the information to connect to a session")
operation GetSessionConnectionData {
    input: GetSessionConnectionDataRequest
    output: GetSessionConnectionDataResponse
    errors: [
        BadRequestException
        ForbiddenException
        InternalServiceException
    ]
}

@input
structure GetSessionConnectionDataRequest {
    @documentation("Session id to get connection details for")
    @httpLabel
    @required
    @length(min: 1)
    sessionId: String

    @documentation("User to get the connection token for")
    @httpLabel
    @length(min: 1)
    @required
    username: String
}

@sensitive
string ConnectionToken

@output
structure GetSessionConnectionDataResponse {
    @required
    @documentation("Session to connect to")
    session: Session

    @required
    @documentation("The token used to connect to the session")
    connectionToken: ConnectionToken
}

@documentation("The entity that represents a session in DCV session manager")
structure Session {
    @documentation("The id of the session")
    @length(min: 1)
    @required
    id: String

    @documentation("The owner of the session")
    @length(min: 1)
    @required
    owner: String

    @required
    @documentation("The server in which the session is in")
    server: Server
}

@documentation("The entity representing a server in DCV Session Manager")
structure Server {
    @documentation("The server web url path")
    @length(min: 1)
    @required
    webUrlPath: String
}
