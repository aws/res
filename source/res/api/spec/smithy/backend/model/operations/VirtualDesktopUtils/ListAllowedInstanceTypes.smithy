//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@suppress(["MissingPaginatedTrait"])
@http(method: "POST", uri: "/res/virtual-desktop-utils/allowed-instance-type")
@tags(["virtual-desktop-utils"])
@documentation("List allowed instance types for virtual desktops")
operation ListAllowedInstanceTypes {
    input: ListAllowedInstanceTypesRequest
    output: ListAllowedInstanceTypesResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListAllowedInstanceTypesRequest {
    @documentation("Whether the instance types need to support hibernation")
    @jsonName("hibernation_support")
    hibernationSupport: Boolean = false

    @documentation("Virtual desktop software stack which defines the requirements of the allowed instance types")
    @jsonName("software_stack")
    softwareStack: res.virtualdesktop#VirtualDesktopSoftwareStack
}

@output
structure ListAllowedInstanceTypesResponse with [res.common#ResListingPayload] {
    @documentation("List of allowed instance types")
    listing: AllowedInstanceTypeList
}

@documentation("List of allowed instance types for virtual desktops")
list AllowedInstanceTypeList {
    member: Document
}
