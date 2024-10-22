#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import arrow


def current_time_ms() -> int:
    """
    Returns the current time in milliseconds.
    :return: Current time in milliseconds.
    """
    return int(arrow.utcnow().timestamp() * 1000)
