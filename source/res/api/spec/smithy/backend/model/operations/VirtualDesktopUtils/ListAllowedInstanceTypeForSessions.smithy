//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@suppress(["MissingPaginatedTrait"])
@http(method: "POST", uri: "/res/virtual-desktop-utils/allowed-instance-type-for-session")
@tags(["virtual-desktop-utils"])
@documentation("List allowed instance types for a virtual desktop session")
operation ListAllowedInstanceTypesForSession {
    input: ListAllowedInstanceTypesForSessionRequest
    output: ListAllowedInstanceTypesForSessionResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListAllowedInstanceTypesForSessionRequest {
    @documentation("Virtual desktop session which defines the requirements of the allowed instance types")
    @required
    session: res.virtualdesktop#VirtualDesktopSession
}

@output
structure ListAllowedInstanceTypesForSessionResponse with [res.common#ResListingPayload] {
    @documentation("List of allowed instance types")
    listing: AllowedInstanceTypeList
}

@documentation("List of allowed instance types for virtual desktops")
list AllowedInstanceTypeList {
    member: Document
}
