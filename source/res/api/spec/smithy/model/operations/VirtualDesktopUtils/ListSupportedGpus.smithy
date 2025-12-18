//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@suppress(["MissingPaginatedTrait"])
@http(method: "GET", uri: "/res/virtual-desktop-utils/supported-gpu")
@readonly
@tags(["virtual-desktop-utils"])
@documentation("List supported GPUs for virtual desktops")
operation ListSupportedGpus {
    input: ListSupportedGpusRequest
    output: ListSupportedGpusResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListSupportedGpusRequest {}

@output
structure ListSupportedGpusResponse with [res.common#ResListingPayload] {
    @documentation("List of available GPUs for virtual desktops")
    listing: VirtualDesktopGpuList
}

@documentation("List of supported GPUs for virtual desktops")
list VirtualDesktopGpuList {
    member: res.virtualdesktop#VirtualDesktopGpu
}
