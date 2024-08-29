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

__all__ = (
    'SocaMemoryUnit',
    'SocaMemory',
    'SocaAmount',
    'SocaSortOrder',
    'SocaDateRange',
    'SocaSortBy',
    'SocaPaginator',
    'SocaFilter',
    'SocaLogEntry',
    'SocaKeyValue',
    'CustomFileLoggerParams',
    'BaseOS'
)

from ideadatamodel import (exceptions, errorcodes, SocaBaseModel)
from ideadatamodel.model_utils import ModelUtils
import ideadatamodel.locale as locale

from pydantic import Field
from enum import Enum
from typing import Optional, Union, Dict, Any, List
from functools import total_ordering
from datetime import datetime


class BaseOS(str, Enum):
    WINDOWS = 'windows'
    AMAZON_LINUX_2 = 'amazonlinux2'
    RHEL_8 = 'rhel8'
    RHEL_9 = 'rhel9'

    def __str__(self):
        return self.value

    def __repr__(self):
        return str(self)


@total_ordering
class SocaMemoryUnit(str, Enum):
    BYTES = 'bytes'
    # refer to https://searchstorage.techtarget.com/definition/mebibyte-MiB
    #   for difference between MiB vs MB
    KiB = 'kib'
    MiB = 'mib'
    GiB = 'gib'
    TiB = 'tib'
    KB = 'kb'
    MB = 'mb'
    GB = 'gb'
    TB = 'tb'

    def __str__(self):
        return self.value

    def __repr__(self):
        return str(self)

    def __eq__(self, other: Optional[Union['SocaMemoryUnit', str]]):
        if other is None:
            return False
        if isinstance(other, str):
            other = SocaMemoryUnit(other)

        if not isinstance(other, SocaMemoryUnit):
            return False

        return self.value == other.value

    def __ne__(self, other: Optional[Union['SocaMemoryUnit', str]]):
        if other is None:
            return True

        if isinstance(other, str):
            other = SocaMemoryUnit(other)

        if not isinstance(other, SocaMemoryUnit):
            return True

        return self.value != other.value

    def __le__(self, other: Optional[Union['SocaMemoryUnit', str]]):
        if other is None:
            return False

        if isinstance(other, str):
            other = SocaMemoryUnit(other)

        if not isinstance(other, SocaMemoryUnit):
            return False

        if self.value == other.value:
            return True

        return self < other

    def __lt__(self, other: Optional[Union['SocaMemoryUnit', str]]):
        if other is None:
            return False

        if isinstance(other, str):
            other = SocaMemoryUnit(other)

        if not isinstance(other, SocaMemoryUnit):
            return False

        return not (self > other)

    def __ge__(self, other: Optional[Union['SocaMemoryUnit', str]]):
        if other is None:
            return True

        if isinstance(other, str):
            other = SocaMemoryUnit(other)

        if not isinstance(other, SocaMemoryUnit):
            return True

        if self.value == other.value:
            return True

        return self > other

    def __gt__(self, other: Optional[Union['SocaMemoryUnit', str]]):
        if other is None:
            return True

        if isinstance(other, str):
            other = SocaMemoryUnit(other)

        if not isinstance(other, SocaMemoryUnit):
            return True

        # if any one of them is TiB, it is definitely greater
        if self.value == SocaMemoryUnit.TiB and other.value != SocaMemoryUnit.TiB:
            return True
        elif other.value == SocaMemoryUnit.TiB:
            return False
        # neither of them is TiB

        # if any one of them is TB, it is definitely greater
        if self.value == SocaMemoryUnit.TB and other.value != SocaMemoryUnit.TB:
            return True
        elif other.value == SocaMemoryUnit.TB:
            return False
        # neither of them is TB

        # if any one of them is GiB, it is definitely greater
        if self.value == SocaMemoryUnit.GiB and other.value != SocaMemoryUnit.GiB:
            return True
        elif other.value == SocaMemoryUnit.GiB:
            return False
        # neither of them is GiB

        # if any one of them is GB, it is definitely greater
        if self.value == SocaMemoryUnit.GB and other.value != SocaMemoryUnit.GB:
            return True
        elif other.value == SocaMemoryUnit.GB:
            return False
        # neither of them is GB

        # if any one of them is MiB, it is definitely greater
        if self.value == SocaMemoryUnit.MiB and other.value != SocaMemoryUnit.MiB:
            return True
        elif other.value == SocaMemoryUnit.MiB:
            return False
        # neither of them is MiB

        # if any one of them is MB, it is definitely greater
        if self.value == SocaMemoryUnit.MB and other.value != SocaMemoryUnit.MB:
            return True
        elif other.value == SocaMemoryUnit.MB:
            return False
        # neither of them is MB

        # if any one of them is KiB, it is definitely greater
        if self.value == SocaMemoryUnit.KiB and other.value != SocaMemoryUnit.KiB:
            return True
        elif other.value == SocaMemoryUnit.KiB:
            return False
        # neither of them is KiB

        # if any one of them is KB, it is definitely greater
        if self.value == SocaMemoryUnit.KB and other.value != SocaMemoryUnit.KB:
            return True
        elif other.value == SocaMemoryUnit.KB:
            return False
        # neither of them is KiB

        # they're both bytes
        return False


@total_ordering
class SocaMemory(SocaBaseModel):
    value: float
    unit: SocaMemoryUnit

    def as_unit(self, desired_unit: SocaMemoryUnit) -> 'SocaMemory':
        if desired_unit == SocaMemoryUnit.TiB:
            value = self.tib()
        elif desired_unit == SocaMemoryUnit.TB:
            value = self.tb()
        elif desired_unit == SocaMemoryUnit.GiB:
            value = self.gib()
        elif desired_unit == SocaMemoryUnit.GB:
            value = self.gb()
        elif desired_unit == SocaMemoryUnit.MiB:
            value = self.mib()
        elif desired_unit == SocaMemoryUnit.MB:
            value = self.mb()
        elif desired_unit == SocaMemoryUnit.KiB:
            value = self.kib()
        elif desired_unit == SocaMemoryUnit.KB:
            value = self.kb()
        else:
            value = self.bytes()
            desired_unit = SocaMemoryUnit.BYTES

        return SocaMemory(
            value=value,
            unit=desired_unit
        )

    def bytes(self) -> int:
        if self.unit == SocaMemoryUnit.BYTES:
            return int(self.value)
        elif self.unit == SocaMemoryUnit.KiB:
            return int(self.value * 1024)
        elif self.unit == SocaMemoryUnit.MiB:
            return int(self.value * (1024 ** 2))
        elif self.unit == SocaMemoryUnit.GiB:
            return int(self.value * (1024 ** 3))
        elif self.unit == SocaMemoryUnit.TiB:
            return int(self.value * (1024 ** 4))
        elif self.unit == SocaMemoryUnit.KB:
            return int(self.value * 1000)
        elif self.unit == SocaMemoryUnit.MB:
            return int(self.value * (1000 ** 2))
        elif self.unit == SocaMemoryUnit.GB:
            return int(self.value * (1000 ** 3))
        elif self.unit == SocaMemoryUnit.TB:
            return int(self.value * (1000 ** 4))

    @staticmethod
    def _value(value: float) -> Union[float, int]:
        if value.is_integer():
            return int(value)
        else:
            return round(value, 1)

    def int_val(self) -> int:
        return int(self.value)

    def float_val(self) -> float:
        return self.value

    def kib(self) -> Union[float, int]:
        if self.unit == SocaMemoryUnit.KiB:
            return self._value(self.value)
        return self._value(self.bytes() / 1024)

    def mib(self) -> Union[float, int]:
        if self.unit == SocaMemoryUnit.MiB:
            return self._value(self.value)
        return self._value(self.bytes() / (1024 ** 2))

    def gib(self) -> Union[float, int]:
        if self.unit == SocaMemoryUnit.GiB:
            return self._value(self.value)
        return self._value(self.bytes() / (1024 ** 3))

    def tib(self) -> Union[float, int]:
        if self.unit == SocaMemoryUnit.TiB:
            return self._value(self.value)
        return self._value(self.bytes() / (1024 ** 4))

    def kb(self) -> Union[float, int]:
        if self.unit == SocaMemoryUnit.KB:
            return self._value(self.value)
        return self._value(self.bytes() / 1000)

    def mb(self) -> Union[float, int]:
        if self.unit == SocaMemoryUnit.MB:
            return self._value(self.value)
        return self._value(self.bytes() / (1000 ** 2))

    def gb(self) -> Union[float, int]:
        if self.unit == SocaMemoryUnit.GB:
            return self._value(self.value)
        return self._value(self.bytes() / (1000 ** 3))

    def tb(self) -> Union[float, int]:
        if self.unit == SocaMemoryUnit.TB:
            return self._value(self.value)
        return self._value(self.bytes() / (1000 ** 4))

    def __repr__(self):
        return str(self)

    def __str__(self):
        s = f'{self._value(self.value)}'
        if self.unit == SocaMemoryUnit.BYTES:
            s += 'b'
        elif self.unit == SocaMemoryUnit.KiB:
            s += 'kib'
        elif self.unit == SocaMemoryUnit.MiB:
            s += 'mib'
        elif self.unit == SocaMemoryUnit.GiB:
            s += 'gib'
        elif self.unit == SocaMemoryUnit.TiB:
            s += 'tib'
        elif self.unit == SocaMemoryUnit.KB:
            s += 'kb'
        elif self.unit == SocaMemoryUnit.MB:
            s += 'mb'
        elif self.unit == SocaMemoryUnit.GB:
            s += 'gb'
        elif self.unit == SocaMemoryUnit.TB:
            s += 'tb'

        return s

    def __sub__(self, other: Optional[Union['SocaMemory', str]]):
        if other is None:
            return False

        if isinstance(other, str):
            other = self.resolve(other)

        larger_unit = self.unit
        if self.unit < other.unit:
            larger_unit = other.unit

        return SocaMemory(
            value=self.bytes() - other.bytes(),
            unit=SocaMemoryUnit.BYTES
        ).as_unit(larger_unit)

    def __add__(self, other: Optional[Union['SocaMemory', str]]):
        if other is None:
            return False

        if isinstance(other, str):
            other = self.resolve(other)

        larger_unit = self.unit
        if self.unit < other.unit:
            larger_unit = other.unit

        return SocaMemory(
            value=self.bytes() + other.bytes(),
            unit=SocaMemoryUnit.BYTES
        ).as_unit(larger_unit)

    # see Rich Comparisons: https://portingguide.readthedocs.io/en/latest/comparisons.html#rich-comparisons

    def __eq__(self, other: Optional[Union['SocaMemory', int, float, str]]):
        if other is None:
            return False
        if isinstance(other, SocaMemory):
            return self.bytes() == other.bytes()
        elif isinstance(other, str):
            memory = self.resolve(other)
            return self.bytes() == memory.bytes()
        elif isinstance(other, int) or isinstance(other, float):
            return self.value == other

    def __ne__(self, other: Optional[Union['SocaMemory', int, float, str]]):
        if other is None:
            # since the other is None. NE should turn out to be True
            return True
        if isinstance(other, SocaMemory):
            return self.bytes() != other.bytes()
        elif isinstance(other, str):
            memory = self.resolve(other)
            return self.bytes() != memory.bytes()
        elif isinstance(other, int) or isinstance(other, float):
            return self.value != other

    def __lt__(self, other: Optional[Union['SocaMemory', int, float, str]]):
        if other is None:
            return False
        if isinstance(other, SocaMemory):
            return self.bytes() < other.bytes()
        elif isinstance(other, str):
            memory = self.resolve(other)
            return self.bytes() < memory.bytes()
        elif isinstance(other, int) or isinstance(other, float):
            return self.value < other

    def __le__(self, other: Optional[Union['SocaMemory', int, float, str]]):
        if other is None:
            return False
        if isinstance(other, SocaMemory):
            return self.bytes() <= other.bytes()
        elif isinstance(other, str):
            memory = self.resolve(other)
            return self.bytes() <= memory.bytes()
        elif isinstance(other, int) or isinstance(other, float):
            return self.value <= other

    def __gt__(self, other: Optional[Union['SocaMemory', int, float, str]]):
        if other is None:
            # since the other is None. The current value is definitely greater. Hence True
            return True
        if isinstance(other, SocaMemory):
            return self.bytes() > other.bytes()
        elif isinstance(other, str):
            memory = self.resolve(other)
            return self.bytes() > memory.bytes()
        elif isinstance(other, int) or isinstance(other, float):
            return self.value > other

    def __ge__(self, other: Optional[Union['SocaMemory', int, float, str]]):
        if other is None:
            # since the other is None. The current value is definitely greater. Hence True
            return True
        if isinstance(other, SocaMemory):
            return self.bytes() >= other.bytes()
        elif isinstance(other, str):
            memory = self.resolve(other)
            return self.bytes() >= memory.bytes()
        elif isinstance(other, int) or isinstance(other, float):
            return self.value >= other

    @staticmethod
    def zero(unit: SocaMemoryUnit = SocaMemoryUnit.BYTES):
        return SocaMemory(value=0, unit=unit)

    @staticmethod
    def resolve(value: Optional[str], unit: SocaMemoryUnit = None, default: 'SocaMemory' = None) -> Optional['SocaMemory']:
        if ModelUtils.is_empty(value):
            return default

        value = value.lower().strip()

        if value.endswith('tib'):
            unit = SocaMemoryUnit.TiB
            memory = value.strip('tib')
        elif value.endswith('gib'):
            unit = SocaMemoryUnit.GiB
            memory = value.strip('gib')
        elif value.endswith('mib'):
            unit = SocaMemoryUnit.MiB
            memory = value.strip('mib')
        elif value.endswith('kib'):
            unit = SocaMemoryUnit.KiB
            memory = value.strip('kib')
        elif value.endswith('tb'):
            unit = SocaMemoryUnit.TB
            memory = value.strip('tb')
        elif value.endswith('gb'):
            unit = SocaMemoryUnit.GB
            memory = value.strip('gb')
        elif value.endswith('mb'):
            unit = SocaMemoryUnit.MB
            memory = value.strip('mb')
        elif value.endswith('kb'):
            unit = SocaMemoryUnit.KB
            memory = value.strip('kb')
        elif value.endswith('b'):
            unit = SocaMemoryUnit.BYTES
            memory = value.strip('b')
        else:
            if unit is None:
                raise exceptions.SocaException(
                    error_code=errorcodes.MEMORY_FORMAT_PARSING_FAILED,
                    message=f'memory string format not supported for value: {value}'
                )
            memory = value

        memory = memory.strip()
        if not ModelUtils.is_int(memory) and not ModelUtils.is_float(memory):
            raise exceptions.SocaException(
                error_code=errorcodes.MEMORY_FORMAT_PARSING_FAILED,
                message=f'invalid memory value: {memory}. memory must be an integer or float value.'
            )

        return SocaMemory(value=float(memory), unit=unit)


@total_ordering
class SocaAmount(SocaBaseModel):
    amount: float
    unit: Optional[str]

    def __init__(self, amount: float = 0.0, unit: str = None):
        super().__init__(amount=amount, unit=unit)

        currency_code = locale.get_currency_code()
        if self.unit is None:
            self.unit = currency_code

        if self.unit != currency_code:
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_LOCALE_CONFIGURATION,
                message=f'Given currency code: {self.unit} does not match the configured '
                        f'currency code: {locale.get_currency_code()}. Please ensure locale is '
                        f'configured as per the expected local currency.'
            )

    @property
    def symbol(self) -> Optional[str]:
        return locale.get_currency_symbol()

    def formatted(self) -> str:
        return locale.currency(amount=self.amount)

    def __str__(self):
        return self.formatted()

    def __repr__(self):
        return str(self)

    def __eq__(self, other: 'SocaAmount'):
        return self.amount == other.amount

    def __ne__(self, other: 'SocaAmount'):
        return self.amount != other.amount

    def __lt__(self, other: 'SocaAmount'):
        return self.amount < other.amount

    def __le__(self, other: 'SocaAmount'):
        return self.amount <= other.amount

    def __gt__(self, other: 'SocaAmount'):
        return self.amount > other.amount

    def __ge__(self, other: 'SocaAmount'):
        return self.amount >= other.amount

    def int_val(self) -> int:
        return int(self.amount)

    def float_val(self) -> float:
        return self.amount


class SocaDateRange(SocaBaseModel):
    key: Optional[str]
    start: Optional[datetime]
    end: Optional[datetime]


class SocaSortOrder(str, Enum):
    ASC = 'asc'
    DESC = 'desc'


class SocaSortBy(SocaBaseModel):
    key: Optional[str]
    order: Optional[SocaSortOrder]


class SocaPaginator(SocaBaseModel):
    total: Optional[int]
    page_size: Optional[int]
    start: Optional[int]
    cursor: Optional[str]


class SocaFilter(SocaBaseModel):
    key: Optional[str]
    value: Optional[Any]
    eq: Optional[Any]
    in_: Optional[Union[str, List[Any]]] = Field(alias='in')
    like: Optional[str]
    starts_with: Optional[str]
    ends_with: Optional[str]
    and_: Optional[List['SocaFilter']] = Field(alias='and')
    or_: Optional[List['SocaFilter']] = Field(alias='or')


class SocaLogEntry(SocaBaseModel):
    tag: Optional[str]
    message: Optional[Union[str, Dict, SocaBaseModel]]
    file_handle: Optional[str]

    def __str__(self):
        s = ''
        if self.tag:
            s = f'({self.tag}) '
        if self.message:
            if isinstance(self.message, str):
                s += self.message.rstrip()
            else:
                s += ModelUtils.to_json(self.message)
        return s


class SocaKeyValue(SocaBaseModel):
    key: Optional[str]
    value: Optional[str]


class CustomFileLoggerParams(SocaBaseModel):
    logger_name: str
    log_dir_name: Optional[str]
    log_file_name: str
    when: str
    interval: int
    backupCount: int
