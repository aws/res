//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.dcvsessionmanagement

use res#BadRequestException
use res#InternalServiceException
use res#UnauthorizedClientError

@http(method: "POST", uri: "/externalAuth/{resSessionId}")
@tags(["sessions"])
@auth([])
@documentation("Validate user credentials and session permissions on DCV session streaming")
operation ExternalAuth {
    input: ExternalAuthRequest
    output: ExternalAuthResponse
    errors: [
        BadRequestException
        UnauthorizedClientError
        InternalServiceException
    ]
}

@input
structure ExternalAuthRequest {
    @required
    @httpLabel
    @length(min: 1, max: 64)
    @documentation("RES session ID embedded in the auth-token-verifier URL configured on the DCV host")
    resSessionId: String

    @required
    @length(min: 1, max: 64)
    @documentation("DCV session ID (always 'console' for auto-created sessions)")
    @jsonName("session_id")
    sessionId: String

    @required
    @length(min: 1, max: 2048)
    @documentation("Authentication token")
    @jsonName("authentication_token")
    authenticationToken: AuthenticationToken

    @required
    @length(min: 1, max: 45)
    @documentation("Client IP address")
    @jsonName("client_address")
    clientAddress: String
}

@sensitive
string AuthenticationToken

enum AuthResult {
    @enumValue("yes")
    YES

    @enumValue("no")
    NO
}

@output
structure ExternalAuthResponse {
    @required
    @documentation("Authentication result: 'yes' or 'no'")
    result: AuthResult

    @documentation("Authenticated username, present when result is 'yes'")
    username: String

    @documentation("Failure message, present when result is 'no'")
    message: String
}
