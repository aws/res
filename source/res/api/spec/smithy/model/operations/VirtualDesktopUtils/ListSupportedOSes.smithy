//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@suppress(["MissingPaginatedTrait"])
@http(method: "GET", uri: "/res/virtual-desktop-utils/supported-os")
@readonly
@tags(["virtual-desktop-utils"])
@documentation("List supported operating systems for virtual desktops")
operation ListSupportedOses {
    input: ListSupportedOsesRequest
    output: ListSupportedOsesResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListSupportedOsesRequest {}

@output
structure ListSupportedOsesResponse with [res.common#ResListingPayload] {
    @documentation("List of available base operating systems for virtual desktops")
    listing: VirtualDesktopBaseOsList
}

@documentation("List of supported base operating systems for virtual desktops")
list VirtualDesktopBaseOsList {
    member: res.virtualdesktop#VirtualDesktopBaseOs
}
