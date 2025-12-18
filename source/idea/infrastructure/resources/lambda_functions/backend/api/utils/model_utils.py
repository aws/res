#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.utils import time_utils  # type: ignore


def convert_timestamps_to_iso(data, *timestamp_fields):
    """
    Convert timestamp fields from milliseconds to ISO format strings.
    
    :param data: Dictionary containing timestamp fields
    :param timestamp_fields: Field names to convert (defaults to 'created_on' and 'updated_on')
    :return: Data with converted timestamps
    """
    # Default fields if none specified
    if not timestamp_fields:
        timestamp_fields = ('created_on', 'updated_on')
    
    for field in timestamp_fields:
        if data.get(field):
            data[field] = time_utils.ms_to_iso(int(data[field]))
    
    return data
