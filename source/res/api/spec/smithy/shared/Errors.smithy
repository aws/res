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

@documentation("The client does not have access to the requested resource.")
@error("client")
@httpError(403)
structure ForbiddenException {
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

@documentation("Error codes for individual item failures in batch operations")
enum BatchOperationErrorCode {
    @documentation("The caller does not have permission to perform this operation")
    FORBIDDEN = "ForbiddenException"

    @documentation("An internal service error occurred")
    INTERNAL_SERVICE = "InternalServiceException"

    @documentation("The request contains invalid or missing parameters.")
    BAD_REQUEST = "BadRequestException"

    @documentation("The requested resource was not found")
    NOT_FOUND = "NotFoundException"

    @documentation("The request conflicts with the current state of the resource")
    CONFLICT = "ConflictException"
}
