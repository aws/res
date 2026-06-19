//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.dcvsessionmanagement

use res#BadRequestException
use res#InternalServiceException
use res#NotFoundException

@http(method: "POST", uri: "/resolveSession")
@tags(["sessionResolver"])
@auth([])
@documentation("Maps RES Session ID to a destination host running the Amazon DCV server")
operation ResolveSession {
    input: ResolveSessionRequest
    output: ResolveSessionResponse
    errors: [
        BadRequestException
        NotFoundException
        InternalServiceException
    ]
}

@input
structure ResolveSessionRequest {
    @documentation("RES Session ID to resolve")
    @httpQuery("sessionId")
    @required
    @length(min: 1)
    sessionId: String

    @documentation("Transport protocol")
    @httpQuery("transport")
    @required
    @length(min: 1)
    transport: String

    @documentation("Client IP address")
    @httpQuery("clientIpAddress")
    @required
    @length(min: 1)
    clientIpAddress: String
}

@output
structure ResolveSessionResponse {
    @required
    @documentation("Resolved session ID")
    @jsonName("SessionId")
    sessionId: String

    @required
    @documentation("Transport protocol for connection")
    @jsonName("TransportProtocol")
    transportProtocol: String

    @required
    @documentation("DCV server DNS name")
    @jsonName("DcvServerEndpoint")
    dcvServerEndpoint: String

    @required
    @documentation("Port number for connection")
    @jsonName("Port")
    port: Integer

    @required
    @documentation("Web URL path for the session")
    @jsonName("WebUrlPath")
    webUrlPath: String
}
