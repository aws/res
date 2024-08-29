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

from ideadatamodel import constants, exceptions, errorcodes
from typing import Optional, Union, Any, List, Tuple, Set, Dict, TypeVar, Mapping
import json
import hashlib
from decimal import Decimal
from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar('T')
TRUE_VALUES = ('true', 'yes', 'y', '1')
FALSE_VALUES = ('false', 'no', 'n', '0')


def json_serializer(obj):
    if isinstance(obj, Decimal):
        s = str(obj)
        if '.' in s:
            return float(s)
        else:
            return int(s)
    else:
        return str(obj)


class ModelUtils:

    @staticmethod
    def is_empty(value: Optional[Any]) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return len(value.strip()) == 0
        if isinstance(value, List):
            return len(value) == 0
        if isinstance(value, Tuple):
            return len(value) == 0
        if isinstance(value, Set):
            return len(value) == 0
        if isinstance(value, Dict):
            return len(value) == 0
        if isinstance(value, dict):
            return len(value) == 0
        if isinstance(value, bytearray):
            return len(value) == 0
        if isinstance(value, bytes):
            return len(value) == 0
        return False

    @staticmethod
    def is_not_empty(value: Optional[Any]) -> bool:
        return not ModelUtils.is_empty(value)

    @staticmethod
    def is_true(value: Optional[Union[str, bool, int]], default=False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value is True
        if isinstance(value, int):
            return bool(value) is True
        if ModelUtils.is_empty(value):
            return default
        return value.strip().lower() in TRUE_VALUES

    @staticmethod
    def is_false(value: Optional[Union[str, bool, int]], default=False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value is False
        if isinstance(value, int):
            return bool(value) is False
        if ModelUtils.is_empty(value):
            return default
        return value.strip().lower() in FALSE_VALUES

    @staticmethod
    def is_int(value: Union[str, int]):
        if isinstance(value, int):
            return True
        if isinstance(value, Decimal):
            return True
        if isinstance(value, str) or isinstance(value, float):
            try:
                int(value)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def is_float(value: Optional[Union[str, float]]):
        if value is None:
            return False
        if isinstance(value, float):
            return True
        if isinstance(value, Decimal):
            return True
        if isinstance(value, str) or isinstance(value, int):
            try:
                float(value)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def get_as_string(value: Optional[Any], default: str = None) -> Optional[str]:
        if value is None:
            return default
        if isinstance(value, str):
            stripped = value.strip()
            if len(stripped) == 0:
                return default
            else:
                return stripped
        if isinstance(value, bytes) or isinstance(value, bytearray):
            return ModelUtils.from_bytes(value)

        return str(value)

    @staticmethod
    def get_as_int(value: Optional[Union[float, int, str]], default: int = None) -> Optional[int]:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, Decimal):
            return int(value)
        if isinstance(value, str):
            if ModelUtils.is_int(value):
                return int(value)
            if ModelUtils.is_float(value):
                return int(float(value))
        return default

    @staticmethod
    def get_as_float(value: Optional[Union[float, str]], default: float = None) -> Optional[float]:
        if value is None:
            return None if default is None else float(default)
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            if ModelUtils.is_float(value):
                return float(value)
            if ModelUtils.is_int(value):
                return float(value)
        return None if default is None else float(default)

    @staticmethod
    def get_as_decimal(value: Optional[Union[float, str]], default: Decimal = None) -> Optional[Decimal]:
        if value is None:
            return None if default is None else float(default)
        if isinstance(value, float):
            return Decimal(value)
        if isinstance(value, int):
            return Decimal(float(value))
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str):
            if ModelUtils.is_float(value):
                return Decimal(float(value))
            if ModelUtils.is_int(value):
                return Decimal(float(value))
        return None if default is None else default

    @staticmethod
    def get_as_bool(value: Optional[Union[bool, str, int]], default=None) -> Optional[bool]:
        if ModelUtils.is_empty(value) is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            if ModelUtils.is_true(value):
                return True
            elif ModelUtils.is_false(value):
                return False
        return default

    @staticmethod
    def get_as_dict(value, default: dict = None) -> Optional[dict]:
        if value is None:
            return default
        if isinstance(value, dict):
            if len(value.keys()) == 0:
                return default
            else:
                return value
        else:
            return default

    @staticmethod
    def get_first(value: Optional[List], default: Any = None) -> Optional[Any]:
        if value is None:
            return default
        if isinstance(value, List):
            if len(value) == 0:
                return default
            return value[0]
        return default

    @staticmethod
    def get_as_list(value, default: list = None) -> Optional[list]:
        if value is None:
            return default
        if isinstance(value, list):
            if len(value) == 0:
                return default
            else:
                return value
        else:
            return default

    @staticmethod
    def get_as_bool_list(value, default: List[bool] = None) -> Optional[List[bool]]:
        entries = ModelUtils.get_as_list(value, default)
        if entries is None:
            return default
        result = []
        for entry in entries:
            entry_ = ModelUtils.get_as_bool(entry)
            if entry_ is None:
                continue
            result.append(entry_)
        return result

    @staticmethod
    def get_as_string_list(value, default: List[str] = None) -> Optional[List[str]]:
        entries = ModelUtils.get_as_list(value, default)
        if entries is None:
            return default
        result = []
        for entry in entries:
            entry_ = ModelUtils.get_as_string(entry)
            if entry_ is None:
                continue
            result.append(entry_)
        return result

    @staticmethod
    def get_as_int_list(value, default: List[int] = None) -> Optional[List[int]]:
        entries = ModelUtils.get_as_list(value, default)
        if entries is None:
            return default
        result = []
        for entry in entries:
            entry_ = ModelUtils.get_as_int(entry)
            if entry_ is None:
                continue
            result.append(entry_)
        return result

    @staticmethod
    def get_as_float_list(value, default: List[float] = None) -> Optional[List[float]]:
        entries = ModelUtils.get_as_list(value, default)
        if entries is None:
            return default
        result = []
        for entry in entries:
            entry_ = ModelUtils.get_as_int(entry)
            if entry_ is None:
                continue
            result.append(entry_)
        return result

    @staticmethod
    def get_as_dict_list(value, default: List[Dict] = None) -> Optional[List[Dict]]:
        entries = ModelUtils.get_as_list(value, default)
        if entries is None:
            return default
        result = []
        for entry in entries:
            entry_ = ModelUtils.get_as_dict(entry)
            if entry_ is None:
                continue
            result.append(entry_)
        return result

    @staticmethod
    def get_as_one_of(value, one_of: Set[Any], default: Any):
        if value is None:
            return default
        if value in one_of:
            return value
        return default

    @staticmethod
    def value_exists(key: str, obj: dict = None) -> bool:
        if obj is None:
            return False
        if key not in obj:
            return False
        value = obj[key]
        if value is None:
            return False
        if isinstance(value, list) or isinstance(value, dict) or isinstance(value, str):
            return not ModelUtils.is_empty(value=value)
        return True

    @staticmethod
    def get_value_as_int(key: str, obj: Mapping = None, default: int = None) -> Optional[int]:
        if not ModelUtils.value_exists(key=key, obj=obj):
            return default
        return ModelUtils.get_as_int(value=obj[key], default=default)

    @staticmethod
    def get_value_as_float(key: str, obj: Mapping = None, default: float = None) -> Optional[float]:
        if not ModelUtils.value_exists(key=key, obj=obj):
            return default
        return ModelUtils.get_as_float(value=obj[key], default=default)

    @staticmethod
    def get_value_as_decimal(key: str, obj: Mapping = None, default: float = None) -> Optional[Decimal]:
        if not ModelUtils.value_exists(key=key, obj=obj):
            return default
        return ModelUtils.get_as_decimal(value=obj[key], default=default)

    @staticmethod
    def get_value_as_bool(key: str, obj: Mapping = None, default: bool = None) -> Optional[bool]:
        if not ModelUtils.value_exists(key=key, obj=obj):
            return default
        return ModelUtils.get_as_bool(value=obj[key], default=default)

    @staticmethod
    def get_value_as_string(key: str, obj: Mapping = None, default: str = None) -> Optional[str]:
        if not ModelUtils.value_exists(key=key, obj=obj):
            return default

        return ModelUtils.get_as_string(value=obj[key], default=default)

    @staticmethod
    def get_value_as_dict(key: str, obj: Mapping = None, default: dict = None) -> Optional[dict]:
        if not ModelUtils.value_exists(key=key, obj=obj):
            return default
        return ModelUtils.get_as_dict(value=obj[key], default=default)

    @staticmethod
    def get_value_as_list(key: str, obj: Mapping = None, default: list = None) -> Optional[list]:
        if not ModelUtils.value_exists(key=key, obj=obj):
            return default
        return ModelUtils.get_as_list(value=obj[key], default=default)

    @staticmethod
    def get_any_value(key: str, obj: Mapping = None, default: Any = None) -> Optional[Any]:
        if not ModelUtils.value_exists(key=key, obj=obj):
            return default
        return obj[key]

    @staticmethod
    def are_equal(str1: Optional[str], str2: Optional[str]) -> bool:
        if str1 is None and str2 is None:
            return True
        if str1 is None:
            return False
        if str2 is None:
            return False
        return str1 == str2

    @staticmethod
    def are_not_equal(str1: Optional[str], str2: Optional[str]) -> bool:
        return not ModelUtils.are_equal(str1, str2)

    @staticmethod
    def are_empty(*args) -> bool:
        if ModelUtils.is_empty(args):
            return True
        for arg in args:
            if not ModelUtils.is_empty(arg):
                return False
        return True

    @staticmethod
    def is_any_empty(*args) -> bool:
        if ModelUtils.is_empty(args):
            return True
        for arg in args:
            if ModelUtils.is_empty(arg):
                return True
        return False

    @staticmethod
    def check_required(label: str, value: Optional[Any]):
        """
        check if the value is empty or not.
        if value is empty, raise an exception for the label.
        :param label: label for the value
        :param value: the value to be checked
        :return: None
        """
        if ModelUtils.is_empty(value):
            raise exceptions.SocaException(
                error_code=errorcodes.INVALID_PARAMS,
                message=f'Invalid arguments. {label} is required.'
            )

    @staticmethod
    def from_bytes(value: Union[bytes, bytearray]) -> str:
        if isinstance(value, bytes):
            return str(value, constants.DEFAULT_ENCODING)
        else:
            return value.decode(constants.DEFAULT_ENCODING)

    @staticmethod
    def to_bytes(value: str) -> bytes:
        return value.encode(constants.DEFAULT_ENCODING)

    @staticmethod
    def to_json(payload: Union[BaseModel, Any], indent=False) -> str:
        if isinstance(payload, BaseModel) or isinstance(payload, GenericModel):
            if indent:
                return payload.json(exclude_none=True, by_alias=True, indent=2)
            else:
                return payload.json(exclude_none=True, by_alias=True)
        else:
            if indent:
                return json.dumps(payload, default=str, indent=2, separators=(',', ':'))
            else:
                return json.dumps(payload, default=str, separators=(',', ':'))

    @staticmethod
    def from_json(data: str) -> Union[Dict, List]:
        return json.loads(data)

    @staticmethod
    def shake_256(data: str, num_bytes: int = 5) -> str:
        return hashlib.shake_256(data.encode('utf-8')).hexdigest(num_bytes)

    @staticmethod
    def walltime_to_seconds(walltime: str) -> int:
        """
        converts wall time to seconds
        walltime format: 00:23:30
        :param walltime:
        :return: seconds as int
        """
        hour, minute, seconds = walltime.split(':')
        return int(hour) * 3600 + int(minute) * 60 + int(seconds)
