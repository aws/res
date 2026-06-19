//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.dcvsessionmanagement

use aws.api#service
use aws.protocols#restJson1
use smithy.api#httpBearerAuth

@restJson1
@httpBearerAuth
@service(sdkId: "DCVSessionManagement")
@documentation("DCV Session Management API")
service DCVSessionManagement {
    version: "1.0.0"
    operations: [
        HealthCheck
        GetSessionScreenshots
        GetSessionConnectionData
        UpdateSessionPermissions
        ExternalAuth
        ResolveSession
        DescribeSessions
    ]
}
