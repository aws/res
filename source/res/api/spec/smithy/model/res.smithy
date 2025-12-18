//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res

use aws.api#service
use aws.protocols#restJson1
use smithy.api#httpBearerAuth

@paginated(inputToken: "nextToken", outputToken: "nextToken")
@restJson1
@service(sdkId: "RES")
@httpBearerAuth
@documentation("RES API")
service RES {
    version: "1.0.0"
    operations: [
        ListSupportedOses
        ListSupportedGpus
        ListScheduleTypes
        ListAllowedInstanceTypes
        ListAllowedInstanceTypesForSession
        ListPermissionProfiles
        GetPermissionProfile
        ListDCVServers
        BatchGetDCVSessions
    ]
}
