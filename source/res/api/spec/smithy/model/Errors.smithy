//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@documentation("This exception is thrown on an unhandled service error.")
@error("server")
@httpError(500)
structure InternalServiceException {
    message: String
}

@documentation("This exception is thrown when a client calls an API with wrong parameters.")
@error("client")
@httpError(400)
structure BadRequestException {
    message: String
}

@documentation("The client is not authorized to perform an action.")
@error("client")
@httpError(401)
structure UnauthorizedClientError {
    message: String
}

@documentation("The requested entity is not found.")
@error("client")
@httpError(404)
structure NotFoundException {
    message: String
}

@documentation("The client is sending more than the allowed number of requests per unit of time.")
@error("client")
@httpError(429)
structure LimitExceededException {
    message: String
}
