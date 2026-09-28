#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from zoneinfo import ZoneInfo

import arrow


def to_utc_datetime_from_iso_format(time_str: str) -> datetime:
    """
    Convert ISO-8601 formatted string to a UTC-aware datetime.
    :return: UTC-aware datetime.
    """
    if time_str[-1] == "Z" or time_str[-1] == "z":
        time_str = time_str[:-1]
        if not time_str.endswith("+00:00"):
            time_str += "+00:00"
    return datetime.fromisoformat(time_str)


def to_datetime_in_timezone(time_str: str, time_zone_str: str) -> datetime:
    """
    Convert ISO-8601 formatted string in UTC to a datetime in the given time zone.
    :return: datetime in the given time zone.
    """
    return to_utc_datetime_from_iso_format(time_str).astimezone(ZoneInfo(time_zone_str))


def current_time_ms() -> int:
    """
    Returns the current time in milliseconds.
    :return: Current time in milliseconds.
    """
    return int(arrow.utcnow().timestamp() * 1000)


def current_time_iso() -> str:
    """
    Returns the current time in ISO-8601 formatted string in UTC.
    :return: Current time in ISO-8601 format.
    """
    return arrow.utcnow().isoformat()


def iso_to_ms(iso_time: str) -> int:
    """
    Convert ISO-8601 formatted string in UTC to time in milliseconds.
    :return: Time in milliseconds.
    """
    return int(arrow.get(iso_time).timestamp() * 1000)


def ms_to_iso(time_ms: int) -> str:
    """
    Convert time in milliseconds to ISO-8601 formatted string in UTC.
    :param time_ms: Time in milliseconds.
    :return: ISO-8601 formatted string.
    """
    return arrow.get(time_ms / 1000).format("YYYY-MM-DD HH:mm:ssZZ")
