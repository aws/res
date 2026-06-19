//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.dcvsessionmanagement

use res#InternalServiceException

@http(method: "GET", uri: "/health")
@readonly
@tags(["health"])
@documentation("Health check endpoint")
operation HealthCheck {
    input: HealthCheckRequest
    output: HealthCheckResponse
    errors: [
        InternalServiceException
    ]
}

@input
structure HealthCheckRequest {}

@output
structure HealthCheckResponse {
    @documentation("Health status")
    status: String
}
