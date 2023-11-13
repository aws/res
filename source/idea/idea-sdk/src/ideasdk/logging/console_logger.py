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

import sys
import datetime
import traceback


class ConsoleLogger:
    """
    This class should be used when application loggers are not yet initialized.
    key candidates to use this class are during app initialization where logger is not available main methods

    Log levels for ConsoleLogger are informational, and are not configurable. i.e. You cannot disable console logging
    logging.

    ConsoleLogger should be used in special cases and sparingly and times when SocaLogger is not available or
    SocaConfig is not yet initialized.
    """

    def __init__(self, tag: str):
        self._tag = tag

    def _log(self, level, message):
        try:
            print(f'[{datetime.datetime.now()}] [{level}] [{self._tag}] {message}', flush=True)
        except:  # noqa
            traceback.print_stack()

    def info(self, message):
        self._log(
            level='INFO',
            message=message
        )

    def warning(self, message):
        self._log(
            level='WARNING',
            message=message
        )

    def error(self, message, print_exc_stack=True):
        level = 'ERROR'
        self._log(
            level=level,
            message=message
        )
        if print_exc_stack:
            etype, exc, tb = sys.exc_info()
            if etype is not None:
                traceback.print_exception(
                    etype=etype,
                    value=exc,
                    tb=tb
                )
