#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from api.exceptions import BadRequestException
from res.utils import logging_utils


logger = logging_utils.get_logger(__name__)


def validate_date_range_filter(
    date_range_key: str = None, after: str = None, before: str = None
) -> None:
    """
    Validate date range filter parameters
    :param date_range_key: The attribute name to filter on
    :param after: Start of the date range as string timestamp
    :param before: End of the date range as string timestamp
    :raises BadRequestException: If validation fails
    """
    if not date_range_key:
        if after or before:
            raise BadRequestException(
                "date_range_key is required when specifying after or before"
            )
    else:
        if not after and not before:
            raise BadRequestException(
                "after and/or before is required when specifying date_range_key"
            )

        # Validate that after and before can be converted to int
        try:
            after_int = int(after) if after else None
            before_int = int(before) if before else None
        except ValueError:
            raise BadRequestException(
                "after and before must be valid integer timestamps"
            )

        if after_int and before_int and after_int > before_int:
            raise BadRequestException("after must be less than or equal to before")
        