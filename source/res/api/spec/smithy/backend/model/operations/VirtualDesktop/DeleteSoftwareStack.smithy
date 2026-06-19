//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "DELETE", uri: "/res/virtual-desktop/software-stack/{stackId}")
@suppress(["HttpMethodSemantics.UnexpectedPayload"])
@idempotent
@tags(["virtual-desktop"])
@documentation("Delete Software Stack")
operation DeleteSoftwareStack {
    input: DeleteSoftwareStackRequest
    output: DeleteSoftwareStackResponse
    errors: [
        BadRequestException
        InternalServiceException
        NotFoundException
    ]
}

@input
structure DeleteSoftwareStackRequest {
    @required
    @length(min: 1)
    @httpLabel
    @jsonName("stack_id")
    stackId: String

    @required
    @length(min: 1)
    @jsonName("base_os")
    baseOs: String
}

@output
structure DeleteSoftwareStackResponse {
    @required
    success: Boolean
}
