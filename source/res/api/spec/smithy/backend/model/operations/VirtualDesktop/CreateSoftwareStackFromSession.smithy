//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "POST", uri: "/res/virtual-desktop/software-stack/create-from-session")
@tags(["virtual-desktop"])
@documentation("Create a software stack from an existing session")
operation CreateSoftwareStackFromSession {
    input: CreateSoftwareStackFromSessionRequest
    output: CreateSoftwareStackFromSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure CreateSoftwareStackFromSessionRequest {
    @required
    @documentation("Session to create the software stack from")
    session: res.virtualdesktop#VirtualDesktopSession

    @required
    @documentation("New software stack configuration")
    @jsonName("software_stack")
    softwareStack: res.virtualdesktop#VirtualDesktopSoftwareStack
}

@output
structure CreateSoftwareStackFromSessionResponse {
    @required
    @documentation("The created software stack")
    @jsonName("software_stack")
    softwareStack: res.virtualdesktop#VirtualDesktopSoftwareStack
}
