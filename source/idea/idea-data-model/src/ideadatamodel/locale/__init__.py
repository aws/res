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

from ideadatamodel import exceptions, errorcodes
from ideadatamodel.model_utils import ModelUtils

import locale
from typing import Any, Optional
import os

_LOCALE_INFO = None
_CURRENCY_CODE = None


def init(locale_: str):
    """
    must be called once! during app initialization, ideally from SocaContext

    for information on configuring additional locale on linux, see:
    https://stackoverflow.com/questions/14547631/python-locale-error-unsupported-locale-setting/36257050

    :param locale_:
    """
    try:
        locale.setlocale(locale.LC_ALL, locale=locale_)
        global _LOCALE_INFO
        _LOCALE_INFO = locale.localeconv()

        # pre-load
        get_currency_code()

    except locale.Error as e:
        raise exceptions.soca_exception(
            error_code=errorcodes.LOCALE_NOT_FOUND_OR_INVALID,
            message=f'locale: {locale_} is invalid or not configured in OS. Error: {e} {os.linesep}'
                    f'To configure locale on Linux, run below commands: {os.linesep}'
                    f'> export LC_ALL="{locale_}.UTF-8" {os.linesep}'
                    f'> export LC_CTYPE="{locale_}.UTF-8" {os.linesep}'
                    f'> sudo dpkg-reconfigure locales'
        )


def _get_locale_info(key: str) -> Optional[Any]:
    if _LOCALE_INFO is None:
        raise exceptions.soca_exception(
            error_code=errorcodes.GENERAL_ERROR,
            message='Locale not yet initialized'
        )
    return ModelUtils.get_any_value(key, _LOCALE_INFO)


def get_currency_code() -> str:
    """
    get the 3-letter ISO currency code. eg. USD, EUR, GBP, CNY etc.
    :return: ISO 3-letter currency code
    """
    global _CURRENCY_CODE
    if _CURRENCY_CODE is None:
        _CURRENCY_CODE = str(_get_locale_info('int_curr_symbol')).strip()
    return _CURRENCY_CODE


def get_currency_symbol() -> str:
    """
    get local currency symbol. eg. $, €, £ etc.
    :return: currency symbol based on locale
    """
    return _get_locale_info('currency_symbol')


def currency(amount: float, symbol=True, grouping=False, international=False) -> str:
    """
    Formats a number val according to the current LC_MONETARY settings.
    see: https://docs.python.org/3/library/locale.html#locale.currency for more details
    :param amount:
    :param symbol:
    :param grouping:
    :param international:
    :return: formatted currency value based on locale
    """
    return locale.currency(amount,
                           symbol=symbol,
                           grouping=grouping,
                           international=international)
