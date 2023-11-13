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

__all__ = ('SocaException')  # noqa

from ideadatamodel import errorcodes


class SocaException(Exception):
    def __init__(self, error_code: str, message: str = None,
                 exc: BaseException = None,
                 file: str = None, ref: object = None):
        self._error_code = error_code
        self._message = message
        self._exc = exc
        self._file = file
        self._ref = ref

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f'[{self.error_code}] {self.message}'

    @property
    def error_code(self):
        if self._error_code:
            return self._error_code
        return errorcodes.GENERAL_ERROR

    @property
    def message(self):
        message = []
        if self._message:
            message.append(self._message)
        if self._exc:
            message.append(f'Err: {self._exc}')
        return ", ".join(message)

    @property
    def exception(self):
        return self._exc

    @property
    def file(self):
        return self._file

    @property
    def ref(self):
        return self._ref
