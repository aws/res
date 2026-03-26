//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "GET", uri: "/res/virtual-desktop/software-stack/{stackId}")
@readonly
@tags(["virtual-desktop"])
@documentation("Get details of a software stack")
operation GetSoftwareStack {
    input: GetSoftwareStackRequest
    output: GetSoftwareStackResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure GetSoftwareStackRequest {
    @documentation("Software stack identifier")
    @httpLabel
    @required
    @length(min: 1)
    stackId: String

    @documentation("Base operating system for the software stack")
    @length(min: 1)
    @httpQuery("baseOs")
    @required
    baseOs: res.virtualdesktop#VirtualDesktopBaseOs
}

@output
structure GetSoftwareStackResponse {
    softwareStack: res.virtualdesktop#VirtualDesktopSoftwareStack
}
