#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from datetime import datetime, timedelta, time as dt_time
import pytz
from pytz import utc
import time


class DateTimeUtils:
    def __init__(self):
        pass

    @staticmethod
    def to_time_object(hours: int = 0, minutes: int = 0, seconds: int = 0) -> dt_time:
        return dt_time(hours, minutes, seconds)

    @staticmethod
    def to_datetime_in_timezone(time_str: str, time_zone_str: str):
        utc_time = DateTimeUtils.to_utc_datetime_from_iso_format(time_str)
        return utc_time.astimezone(pytz.timezone(time_zone_str))

    @staticmethod
    def to_utc_datetime_from_iso_format(time_str: str) -> datetime:
        if time_str[-1] == 'Z' or time_str[-1] == 'z':
            time_str = time_str[:-1]
            if not time_str.endswith('+00:00'):
                time_str += '+00:00'
        return datetime.fromisoformat(time_str)

    @staticmethod
    def to_datetime(current_time_in_ms: int):
        return DateTimeUtils.localize(datetime.fromtimestamp(current_time_in_ms))

    @staticmethod
    def to_minutes(hours: int = None, seconds: int = None, millis: int = None):
        if hours is not None:
            return int(hours / (60 * 60 * 1000))
        if seconds is not None:
            return int(seconds / 60)
        if millis is not None:
            return int(millis / (60 * 1000))
        return None

    @staticmethod
    def diff(d1: datetime, d2: datetime, to_minutes: bool = False):
        """
        returns difference between to datetime objects in seconds
        :param d1:
        :param d2:
        :param to_minutes:
        :return:
        """
        delta = d1 - d2
        if to_minutes:
            return DateTimeUtils.to_minutes(seconds=delta.seconds)
        return delta.seconds

    @staticmethod
    def current_datetime():
        return DateTimeUtils.localize(datetime.now())

    @staticmethod
    def current_datetime_iso():
        return datetime.now().isoformat()

    @staticmethod
    def localize(value: datetime):
        return utc.localize(value)

    @staticmethod
    def compare(d1: datetime, d2: datetime, offset_secs: int = None):
        """
        compares date with datetime compare_with
        if date is None, current datetime is used.
        if offset (-ve or +ve) is provided, offset is added to d2 and then compared
        :param d1:
        :param d2:
        :param offset_secs:
        :return:
            -1 - if d1 < d2
            0 - if d1 == d2
            1 - if d1 > d2

        """
        if offset_secs is not None:
            d2 = d2 + timedelta(seconds=offset_secs)

        if d1 < d2:
            return -1
        elif d1 > d2:
            return 1
        else:
            return 0

    @staticmethod
    def compare_to_now(date: datetime, offset_secs: int = None):
        return DateTimeUtils.compare(
            d1=DateTimeUtils.current_datetime(),
            d2=date,
            offset_secs=offset_secs
        )

    @staticmethod
    def current_time_millis():
        return round(time.time() * 1000)
