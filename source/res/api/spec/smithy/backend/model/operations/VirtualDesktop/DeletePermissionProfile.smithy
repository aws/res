//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "DELETE", uri: "/res/virtual-desktop/permission-profile/{profileId}")
@suppress(["HttpMethodSemantics.UnexpectedPayload"])
@idempotent
@tags(["virtual-desktop"])
@documentation("Delete Permission Profile")
operation DeletePermissionProfile {
    input: DeletePermissionProfileRequest
    output: DeletePermissionProfileResponse
    errors: [
        BadRequestException
        InternalServiceException
        NotFoundException
    ]
}

@input
structure DeletePermissionProfileRequest {
    @required
    @httpLabel
    @jsonName("profile_id")
    profileId: String
}

@output
structure DeletePermissionProfileResponse {
    @required
    success: Boolean
}
