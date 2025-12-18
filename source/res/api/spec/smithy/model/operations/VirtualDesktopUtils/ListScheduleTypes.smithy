//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@suppress(["MissingPaginatedTrait"])
@http(method: "GET", uri: "/res/virtual-desktop-utils/schedule-type")
@readonly
@tags(["virtual-desktop-utils"])
@documentation("List available schedule types for virtual desktops")
operation ListScheduleTypes {
    input: ListScheduleTypesRequest
    output: ListScheduleTypesResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure ListScheduleTypesRequest {}

@output
structure ListScheduleTypesResponse with [res.common#ResListingPayload] {
    @documentation("List of available schedule types for virtual desktops")
    listing: VirtualDesktopScheduleTypeList
}

@documentation("List of schedule types for virtual desktops")
list VirtualDesktopScheduleTypeList {
    member: res.virtualdesktop#VirtualDesktopScheduleType
}
