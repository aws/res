#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone

from res.utils import time_utils


def test_to_utc_datetime_from_iso_format_handles_trailing_z():
    result = time_utils.to_utc_datetime_from_iso_format("2026-06-22T09:15:00Z")
    assert result == datetime(2026, 6, 22, 9, 15, tzinfo=timezone.utc)


def test_to_utc_datetime_from_iso_format_handles_lowercase_z():
    result = time_utils.to_utc_datetime_from_iso_format("2026-06-22T09:15:00z")
    assert result == datetime(2026, 6, 22, 9, 15, tzinfo=timezone.utc)


def test_to_utc_datetime_from_iso_format_handles_offset():
    result = time_utils.to_utc_datetime_from_iso_format("2026-06-22T09:15:00+00:00")
    assert result == datetime(2026, 6, 22, 9, 15, tzinfo=timezone.utc)


def test_to_datetime_in_timezone_converts_utc_to_local():
    """09:15 UTC is 02:15 in America/Los_Angeles (PDT, UTC-7)."""
    result = time_utils.to_datetime_in_timezone(
        "2026-06-22T09:15:00Z", "America/Los_Angeles"
    )
    assert result.hour == 2
    assert result.minute == 15
    assert result.utcoffset().total_seconds() == -7 * 3600


def test_to_datetime_in_timezone_utc_to_utc_is_identity():
    result = time_utils.to_datetime_in_timezone("2026-06-22T09:15:00Z", "UTC")
    assert result.hour == 9
    assert result.minute == 15
