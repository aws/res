//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

@http(method: "PUT", uri: "/res/virtual-desktop/session-permission")
@readonly
@tags(["virtual-desktop"])
@documentation("Get a list of session permissions")
operation UpdateSessionPermissions {
    input: UpdatePermissionsRequest
    output: UpdatePermissionsResponse
    errors: [
        BadRequestException
        InternalServiceException
    ]
}

@input
structure UpdatePermissionsRequest {
    @documentation("List of session permissions to create")
    create: SessionPermissionsList

    @documentation("List of session permissions to update")
    update: SessionPermissionsList

    @documentation("List of session permissions to delete")
    delete: SessionPermissionsList
}

@output
structure UpdatePermissionsResponse {
    @documentation("List of session permissions that where create/updated")
    permissions: SessionPermissionsList
}
