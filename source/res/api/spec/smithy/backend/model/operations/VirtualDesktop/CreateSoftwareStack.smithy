//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/software-stack")
@tags(["virtual-desktop"])
@documentation("Create Software Stack")
operation CreateSoftwareStack {
    input: CreateSoftwareStackRequest
    output: CreateSoftwareStackResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure CreateSoftwareStackRequest {
    @required
    @documentation("Create virtual desktop session request")
    @jsonName("software_stack")
    softwareStack: res.virtualdesktop#VirtualDesktopSoftwareStack
}

@output
structure CreateSoftwareStackResponse {
    @required
    @documentation("Create virtual desktop session response")
    @jsonName("software_stack")
    softwareStack: res.virtualdesktop#VirtualDesktopSoftwareStack
}
