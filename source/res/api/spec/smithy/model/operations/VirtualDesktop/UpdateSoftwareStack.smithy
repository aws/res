//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "PUT", uri: "/res/virtual-desktop/software-stack/{stackId}")
@tags(["virtual-desktop"])
@documentation("Update Software Stack")
operation UpdateSoftwareStack {
    input: UpdateSoftwareStackRequest
    output: UpdateSoftwareStackResponse
    errors: [
        BadRequestException
        InternalServiceException
        NotFoundException
    ]
}

@input
structure UpdateSoftwareStackRequest {
    @required
    @httpLabel
    @jsonName("stack_id")
    @length(min: 1)
    stackId: String

    @required
    @documentation("Update virtual desktop session request")
    @jsonName("software_stack")
    softwareStack: res.virtualdesktop#VirtualDesktopSoftwareStack
}

@output
structure UpdateSoftwareStackResponse {
    @required
    @documentation("Update virtual desktop session response")
    @jsonName("software_stack")
    softwareStack: res.virtualdesktop#VirtualDesktopSoftwareStack
}
