#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from datamodel.models.health_check_response_content import HealthCheckResponseContent


def health_check():
    """Health check endpoint."""
    return HealthCheckResponseContent(status="OK")
