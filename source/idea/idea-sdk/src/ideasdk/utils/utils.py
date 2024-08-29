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

import base64
import hashlib
import os
import pathlib
import platform
import random
import re
import stat
import time
import unicodedata
import urllib.parse
import uuid
from collections.abc import MutableMapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union, List, Set, Dict, Any, Mapping, Callable, TypeVar

import arrow
import semver
import shortuuid
import yaml
from password_generator import PasswordGenerator
from pydantic import BaseModel
from decimal import Decimal
import botocore.session
import boto3

import ideasdk
from ideadatamodel import exceptions, errorcodes, constants
from ideadatamodel.model_utils import ModelUtils
from ideasdk.utils import EnvironmentUtils

T = TypeVar('T')
TRUE_VALUES = ('true', 'yes', 'y', '1')
FALSE_VALUES = ('false', 'no', 'n', '0')

FILENAME_ASCII_STRIP_RE = re.compile(r"[^A-Za-z0-9_.-]")

# directory tree constants
DIRECTORY_TREE_SPACE = '    '
DIRECTORY_TREE_BRANCH = '│   '
DIRECTORY_TREE_TEE = '├── '
DIRECTORY_TREE_LAST = '└── '


class Utils:

    @staticmethod
    def is_empty(value: Optional[Union[Any]]) -> bool:
        return ModelUtils.is_empty(value)

    @staticmethod
    def is_not_empty(value: Optional[Union[Any]]) -> bool:
        return ModelUtils.is_not_empty(value)

    @staticmethod
    def is_true(value: Optional[Union[str, bool, int]], default=False) -> bool:
        return ModelUtils.is_true(value, default)

    @staticmethod
    def is_false(value: Optional[Union[str, bool, int]], default=False) -> bool:
        return ModelUtils.is_false(value, default)

    @staticmethod
    def is_int(value: Union[str, int]):
        return ModelUtils.is_int(value)

    @staticmethod
    def is_float(value: Optional[Union[str, float]]):
        return ModelUtils.is_float(value)

    @staticmethod
    def get_as_string(value: Optional[Any], default: str = None) -> Optional[str]:
        return ModelUtils.get_as_string(value, default)

    @staticmethod
    def get_as_int(value: Optional[Union[float, int, str]], default: int = None) -> Optional[int]:
        return ModelUtils.get_as_int(value, default)

    @staticmethod
    def get_as_float(value: Optional[Union[float, str]], default: float = None) -> Optional[float]:
        return ModelUtils.get_as_float(value, default)

    @staticmethod
    def get_as_decimal(value: Optional[Union[float, str]], default: float = None) -> Optional[Decimal]:
        return ModelUtils.get_as_decimal(value, default)

    @staticmethod
    def get_as_bool(value: Optional[Union[bool, str, int]], default=None) -> Optional[bool]:
        return ModelUtils.get_as_bool(value, default)

    @staticmethod
    def get_as_dict(value, default: dict = None) -> Optional[dict]:
        return ModelUtils.get_as_dict(value, default)

    @staticmethod
    def get_first(value: Optional[List], default: Any = None) -> Optional[Any]:
        return ModelUtils.get_first(value, default)

    @staticmethod
    def get_as_list(value, default: list = None) -> Optional[list]:
        return ModelUtils.get_as_list(value, default)

    @staticmethod
    def get_as_bool_list(value, default: List[bool] = None) -> Optional[List[bool]]:
        return ModelUtils.get_as_bool_list(value, default)

    @staticmethod
    def get_as_string_list(value, default: List[str] = None) -> Optional[List[str]]:
        return ModelUtils.get_as_string_list(value, default)

    @staticmethod
    def get_as_int_list(value, default: List[int] = None) -> Optional[List[int]]:
        return ModelUtils.get_as_int_list(value, default)

    @staticmethod
    def get_as_float_list(value, default: List[float] = None) -> Optional[List[float]]:
        return ModelUtils.get_as_float_list(value, default)

    @staticmethod
    def get_as_dict_list(value, default: List[Dict] = None) -> Optional[List[Dict]]:
        return ModelUtils.get_as_dict_list(value, default)

    @staticmethod
    def get_as_one_of(value, one_of: Set[Any], default: Any):
        return ModelUtils.get_as_one_of(value, one_of, default)

    @staticmethod
    def value_exists(key: str, obj: dict = None) -> bool:
        return ModelUtils.value_exists(key, obj)

    @staticmethod
    def get_value_as_int(key: str, obj: Mapping = None, default: int = None) -> Optional[int]:
        return ModelUtils.get_value_as_int(key, obj, default)

    @staticmethod
    def get_value_as_float(key: str, obj: Mapping = None, default: float = None) -> Optional[float]:
        return ModelUtils.get_value_as_float(key, obj, default)

    @staticmethod
    def get_value_as_decimal(key: str, obj: Mapping = None, default: float = None) -> Optional[Decimal]:
        return ModelUtils.get_value_as_decimal(key, obj, default)

    @staticmethod
    def get_value_as_bool(key: str, obj: Mapping = None, default: bool = None) -> Optional[bool]:
        return ModelUtils.get_value_as_bool(key, obj, default)

    @staticmethod
    def get_value_as_string(key: str, obj: Mapping = None, default: str = None) -> Optional[str]:
        return ModelUtils.get_value_as_string(key, obj, default)

    @staticmethod
    def get_value_as_dict(key: str, obj: Mapping = None, default: dict = None) -> Optional[dict]:
        return ModelUtils.get_value_as_dict(key, obj, default)

    @staticmethod
    def get_value_as_list(key: str, obj: Mapping = None, default: list = None) -> Optional[list]:
        return ModelUtils.get_value_as_list(key, obj, default)

    @staticmethod
    def get_any_value(key: str, obj: Mapping = None, default: Any = None) -> Optional[Any]:
        return ModelUtils.get_any_value(key, obj, default)

    @staticmethod
    def are_equal(str1: Optional[str], str2: Optional[str]) -> bool:
        return ModelUtils.are_equal(str1, str2)

    @staticmethod
    def are_not_equal(str1: Optional[str], str2: Optional[str]) -> bool:
        return ModelUtils.are_not_equal(str1, str2)

    @staticmethod
    def are_empty(*args) -> bool:
        return ModelUtils.are_empty(*args)

    @staticmethod
    def is_any_empty(*args) -> bool:
        return ModelUtils.is_any_empty(*args)

    @staticmethod
    def check_required(key: str, value: Optional[Any]):
        return ModelUtils.check_required(key, value)

    @staticmethod
    def to_json(payload: Union[BaseModel, Any], indent=False) -> str:
        return ModelUtils.to_json(payload, indent)

    @staticmethod
    def from_json(data: str) -> Union[Dict, List]:
        return ModelUtils.from_json(data)

    @staticmethod
    def deep_copy(payload: Union[BaseModel, Dict]) -> Dict:
        json_string = ModelUtils.to_json(payload)
        return Utils.from_json(json_string)

    @staticmethod
    def to_yaml(payload: Union[BaseModel, Any], sort_keys=False, width=140) -> str:
        json_string = Utils.to_json(payload)
        json_dict = Utils.from_json(json_string)
        return yaml.dump(json_dict, sort_keys=sort_keys, width=width)

    @staticmethod
    def from_yaml(data: str) -> Union[Dict, List]:
        return yaml.safe_load(data)

    @staticmethod
    def from_bytes(value: Union[bytes, bytearray]) -> str:
        return ModelUtils.from_bytes(value)

    @staticmethod
    def to_bytes(value: str) -> bytes:
        return ModelUtils.to_bytes(value)

    # end model util wrappers

    @staticmethod
    def is_interval_expired(last_run_ms: Optional[int], now_ms: int, interval_secs: int) -> bool:
        if last_run_ms is None:
            return True
        return (now_ms - last_run_ms) > (interval_secs * 1000)

    @staticmethod
    def to_datetime(time_in_ms: int) -> Union[datetime, None]:
        if Utils.is_empty(time_in_ms):
            return None
        return arrow.get(int(time_in_ms / 1000)).datetime

    @staticmethod
    def to_milliseconds(datetime_obj: datetime) -> int:
        if Utils.is_empty(datetime_obj):
            return 0

        return int(datetime_obj.timestamp() * 1000)

    @staticmethod
    def walltime_to_seconds(walltime: str) -> int:
        return ModelUtils.walltime_to_seconds(walltime)

    @staticmethod
    def format_currency(amount: float, currency='$'):
        return currency + '{:,.2f}'.format(amount)

    @staticmethod
    def get_retry_backoff_interval(current_retry=0,
                                   max_retries: Optional[int] = None,
                                   backoff_in_seconds=1) -> float:
        if max_retries is not None:
            current_retry = current_retry % max_retries
        return backoff_in_seconds * 2 ** current_retry + random.uniform(0, 1)

    @staticmethod
    def retry_with_backoff(fn: Callable[[], T], retries=5, backoff_in_seconds=1) -> T:
        """
        retry and exponential backoff
        To make a setup more resilient we should allow for certain actions to be retried before they fail.
        We should not "hammer" our underlying systems, so it is wise to wait a bit before a
        retry (exponential backoff).
        Note: this only works if actions are idempotent and you can afford to wait.

        credits: Kees C. Bakker
        sourced from https://keestalkstech.com/2021/03/python-utility-function-retry-with-exponential-backoff/

        modified as per SOCA requirements.

        :param fn:
        :param retries:
        :param backoff_in_seconds:
        :return:
        """
        x = 0
        while True:
            try:
                return fn()
            except:  # noqa
                if x == retries:
                    raise exceptions.exceeded_max_retries(f'retries: {retries}')
                else:
                    sleep = Utils.get_retry_backoff_interval(
                        current_retry=x,
                        max_retries=retries,
                        backoff_in_seconds=backoff_in_seconds
                    )
                    time.sleep(sleep)
                    x += 1

    @staticmethod
    def minutes(seconds=None, millis=None) -> int:
        seconds = Utils.get_as_int(seconds, 0)
        if seconds > 0:
            return int(seconds / 60)
        millis = Utils.get_as_int(millis, 0)
        if millis > 0:
            return int(millis / (60 * 1000))
        return 0

    @staticmethod
    def duration(seconds: int, absolute: bool = True, future: bool = False) -> str:
        if 0 <= seconds < 60:
            result = ''
            if seconds == 0:
                if absolute:
                    result += '0 seconds'
                else:
                    result += 'now'
            else:
                if seconds == 1:
                    result += '1 second'
                else:
                    result = f'{seconds} seconds'
                if not absolute:
                    if future:
                        result = f'in {result}'
                    else:
                        result = f'{result} ago'
            return result

        if absolute:
            return arrow.utcnow().shift(seconds=seconds).humanize(only_distance=True)
        else:
            if future:
                return arrow.utcnow().shift(seconds=seconds).humanize(only_distance=False)
            else:
                return arrow.utcnow().shift(seconds=-seconds).humanize(only_distance=False)

    @staticmethod
    def uuid() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def short_uuid() -> str:
        return shortuuid.uuid()

    @staticmethod
    def generate_password(length=8, min_uppercase_chars=1, min_lowercase_chars=1, min_numbers=1, min_special_chars=1) -> str:
        generator = PasswordGenerator()
        generator.maxlen = length
        generator.minlen = length
        generator.minuchars = min_uppercase_chars
        generator.minlchars = min_lowercase_chars
        generator.minnumbers = min_numbers
        generator.minschars = min_special_chars
        generator.excludeschars = "$"
        return generator.generate()

    @staticmethod
    def to_title_case(s: str) -> str:
        token = s.replace('-', ' ').replace('_', ' ')
        return ''.join(x for x in token.title() if not x.isspace())

    @staticmethod
    def shake_256(data: str, num_bytes: int = 5) -> str:
        return hashlib.shake_256(data.encode('utf-8')).hexdigest(num_bytes)

    @staticmethod
    def md5(data: str) -> str:
        return hashlib.md5(data.encode('utf-8'), usedforsecurity=False).hexdigest()

    @staticmethod
    def sha256(data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def sha384(data: str) -> str:
        return hashlib.sha384(data.encode('utf-8')).hexdigest()

    @staticmethod
    def compute_checksum_for_dir(dir_path: str) -> str:
        return Utils.compute_checksum_for_dirs([dir_path])

    @staticmethod
    def compute_checksum_for_dirs(dir_paths: List[str]) -> str:
        checksum = ''
        for dir_path in dir_paths:
            for file_path in pathlib.Path(dir_path).glob('**/*'):
                file_path = str(file_path.absolute())
                if Utils.is_file(file_path):
                    checksum = f'{checksum}{Utils.compute_checksum_for_file(file_path)}'

        return Utils.sha256(checksum)

    @staticmethod
    def compute_checksum_for_file(file_path: str) -> str:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    @staticmethod
    def is_file(file: str) -> bool:
        if Utils.is_empty(file):
            return False
        return os.path.isfile(file)

    @staticmethod
    def is_socket(path: str) -> bool:
        try:
            mode = os.stat(path).st_mode
            return stat.S_ISSOCK(mode)
        except FileNotFoundError:
            return False

    @staticmethod
    def is_dir(directory: str) -> bool:
        if Utils.is_empty(directory):
            return False
        return os.path.isdir(directory)

    @staticmethod
    def is_symlink(path: str) -> bool:
        if Utils.is_empty(path):
            return False
        return os.path.islink(path)

    @staticmethod
    def current_time_ms() -> int:
        return int(arrow.utcnow().timestamp() * 1000)

    @staticmethod
    def extract_semver(filename_or_uri) -> str:
        stem = Path(filename_or_uri).stem
        index = None
        for index, c in enumerate(stem):
            if not c.isnumeric():
                continue
            break
        version = stem[index:]
        try:
            semver.VersionInfo.parse(version)
            return version
        except ValueError:
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_SEMVER,
                message=f'Could not extract semantic version from: {filename_or_uri}. '
                        f'Please ensure you have included a semantic version in the package name.'
            )

    @staticmethod
    def base64_encode(data: Union[str, bytes]) -> str:
        if isinstance(data, str):
            return Utils.from_bytes(base64.b64encode(Utils.to_bytes(data)))
        else:
            return Utils.from_bytes(base64.b64encode(data))

    @staticmethod
    def base64_decode(data: Union[str, bytes]) -> str:
        if isinstance(data, str):
            return Utils.from_bytes(base64.b64decode(Utils.to_bytes(data)))
        else:
            return Utils.from_bytes(base64.b64decode(data))

    @staticmethod
    def url_encode(data: str, encoding: str = constants.DEFAULT_ENCODING) -> str:
        return urllib.parse.quote(data, encoding=encoding)

    @staticmethod
    def url_decode(data: str, encoding: str = constants.DEFAULT_ENCODING) -> str:
        return urllib.parse.unquote(data, encoding=encoding)

    @staticmethod
    def is_url(url: str, scheme: str) -> bool:
        return urllib.parse.urlparse(url).scheme == scheme

    @staticmethod
    def encode_basic_auth(username: str, password: str) -> str:
        return Utils.base64_encode(f'{username}:{password}')

    @staticmethod
    def file_system_friendly_timestamp() -> str:
        return arrow.now().format('YYYY-MM-DD-HHmmss.SSS')

    @staticmethod
    def from_win_timestamp(win_timestamp: int) -> float:
        unix_epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        windows_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        epoch_delta = unix_epoch - windows_epoch
        windows_timestamp_in_seconds = win_timestamp / 10_000_000
        unix_timestamp = windows_timestamp_in_seconds - epoch_delta.total_seconds()
        return unix_timestamp

    @staticmethod
    def is_linux() -> bool:
        return platform.system() == 'Linux'

    @staticmethod
    def is_windows() -> bool:
        return platform.system() == 'Windows'

    @staticmethod
    def app_deploy_dir() -> str:
        app_deploy_dir = EnvironmentUtils.idea_app_deploy_dir()
        if app_deploy_dir is None:
            user_home = os.path.expanduser('~')
            app_deploy_dir = os.path.join(user_home, '.idea')
        return app_deploy_dir

    @staticmethod
    def to_dict(obj: Optional[BaseModel], default=None) -> Dict:
        if obj is None:
            return default
        json_str = Utils.to_json(obj)
        return Utils.from_json(json_str)

    @staticmethod
    def is_binary_file(file: str) -> bool:
        """
        Check if a file has binary content or not.
        Reference: https://stackoverflow.com/questions/898669/how-can-i-detect-if-a-file-is-binary-non-text-in-python
        :param file: path to file
        :return: True if file has binary content, False otherwise.
        :raises FILE_NOT_FOUND
        """
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
        if not Utils.is_file(file):
            raise exceptions.file_not_found(file)
        with open(file, 'rb') as f:
            content = f.read(1024)
        return bool(content.translate(None, text_chars))

    @staticmethod
    def to_secure_filename(file: str) -> Optional[str]:
        r"""
        Pass it a filename and it will return a secure version of it.  This
        filename can then safely be stored on a regular file system and passed
        to :func:`os.path.join`.  The filename returned is an ASCII only string
        for maximum portability.

        Source:
        this is a stripped down version of the below method from Flask framework.
        https://github.com/pallets/werkzeug/blob/main/src/werkzeug/utils.py - secure_filename()

        :param file:
        :return:
        """
        filename = unicodedata.normalize('NFKD', file)
        filename = filename.encode('ascii', 'ignore').decode('ascii')

        for sep in os.path.sep, os.path.altsep:
            if sep:
                filename = filename.replace(sep, ' ')
                filename = str(FILENAME_ASCII_STRIP_RE.sub('', '_'.join(filename.split()))).strip('._')

        if Utils.is_empty(filename):
            return None

        return filename

    @staticmethod
    def ec2_hostname_to_ipv4(hostname: str):
        if Utils.is_empty(hostname):
            return ''

        return hostname.replace('ip-', '').replace('-', '.')

    @staticmethod
    def ipv4_to_ec2_hostname(private_ip: str):
        if Utils.is_empty(private_ip):
            return ''

        transformed_ip = private_ip.replace('.', '-')
        return f'ip-{transformed_ip}'

    @staticmethod
    def build_package_download_url(cluster_s3_bucket: str, module_name: str, module_version: str):
        return f's3://{cluster_s3_bucket}/idea/releases/idea-{module_name}-{module_version}.tar.gz'

    @staticmethod
    def check_and_convert_decimal_value(value: Any) -> Any:
        """
        since the ddb table resource returns all Number (N) types as decimals, additional processing is required to distinguish between int and float

        if value is of type Decimal, return it's applicable int or float value
        if value is a list of Decimals, converts all values in the list to applicable int of float

        see: https://github.com/boto/boto3/issues/369
        below implementation will not work for very large decimal numbers and exponent values for float
        :param value: Any
        :return: value with Decimal types converted to float of int if applicable
        """
        if value is None:
            return value
        updated_value = None
        if isinstance(value, Decimal):
            string_val = str(value)
            if '.' in string_val:
                updated_value = float(string_val)
            else:
                updated_value = int(string_val)
        elif isinstance(value, list):
            list_entry = value
            if len(list_entry) > 0 and isinstance(list_entry[0], Decimal):
                updated_list = []
                for list_val in list_entry:
                    string_val = str(list_val)
                    if '.' in string_val:
                        updated_list.append(float(string_val))
                    else:
                        updated_list.append(int(string_val))
                    updated_list.append(value)
                updated_value = updated_list
        if updated_value is None:
            return value
        return updated_value

    @staticmethod
    def convert_custom_tags_to_key_value_pairs(custom_tags: List[str]) -> Dict:
        result = {}
        for custom_tag in custom_tags:
            tokens = custom_tag.split(',', 1)
            key = tokens[0].split('Key=')[1].strip()
            value = tokens[1].split('Value=')[1].strip()
            if Utils.is_empty(key):
                continue
            if Utils.is_empty(value):
                continue
            result[key] = value
        return result

    @staticmethod
    def convert_tags_dict_to_aws_tags(tags: Dict) -> List[Dict]:
        """
        utility method to convert a dictionary of tags to a format used by many AWS to accept tags

        eg::
            {
                'k1': 'v1',
                'k2': 'v2'
            }

        will be converted to::
            [
                {
                    'Key': 'k1',
                    'Value': 'v1'
                },
                {
                    'Key': 'k2',
                    'Value': 'v2'
                }
            ]

        empty keys or values will be ignored.

        :param tags:
        :return: List[Dict] with Key and Value
        """
        result = []
        for key, value in tags.items():
            if Utils.is_empty(key):
                continue
            if Utils.is_empty(value):
                continue
            result.append({
                'Key': key,
                'Value': Utils.get_as_string(value)
            })
        return result
    
    @staticmethod
    def convert_to_dict(obj):
        """
        Recursively converts an object to a dictionary.
        """
        if isinstance(obj, dict):
            return {k: Utils.convert_to_dict(v) for k, v in obj.items()}
        elif hasattr(obj, "__dict__"):
            return {key: Utils.convert_to_dict(value) for key, value in obj.__dict__.items() if not key.startswith("_")}
        elif isinstance(obj, list):
            return [Utils.convert_to_dict(item) for item in obj]
        else:
            return obj

    @staticmethod
    def convert_tags_list_of_dict_to_tags_dict(list: list[dict]) -> dict:
        result = {}
        if (not Utils.is_empty(list)):
            for tag_pair in list:
                key = tag_pair.get("session_tags_keys")
                value = tag_pair.get("session_tags_values")
                if key and value is not None:
                    result[key] = value
        return result

    @staticmethod
    def create_boto_session(aws_region: str, aws_profile: Optional[str] = None):
        """
        creates a botocore session
        central place throughout the code base to create a botocore session
        ensures the solution id is available in all API calls for metrics collection

        :param aws_region: name of the aws region
        :param aws_profile: name of the aws profile
        :return: boto3.Session
        """
        botocore_session = botocore.session.Session(profile=aws_profile)
        botocore_session.user_agent_extra = f'AwsSolution/{constants.AWS_SOLUTION_ID}/{ideasdk.__version__}'
        return boto3.Session(botocore_session=botocore_session, region_name=aws_region)

    @staticmethod
    def get_platform(base_os: str) -> str:
        """
        returns the name of the platform given a supported base os
        raises INVALID_PARAMS for an unsupported OS
        """
        if base_os in constants.SUPPORTED_LINUX_OS:
            return constants.PLATFORM_LINUX
        elif base_os == constants.OS_WINDOWS:
            return constants.PLATFORM_WINDOWS
        raise exceptions.invalid_params(f'unable to determine platform for base_os: {base_os}')

    @staticmethod
    def get_ec2_block_device_name(base_os: str) -> str:
        """
        returns the ec2 block device name given a supported base os
        """
        if base_os == constants.OS_AMAZONLINUX2:
            return '/dev/xvda'
        else:
            return '/dev/sda1'

    @staticmethod
    def print_directory_tree(directory: pathlib.Path, prefix: str = ''):
        """A recursive generator, given a directory Path object
        will yield a visual tree structure line by line
        with each line prefixed by the same characters

        Source: https://stackoverflow.com/questions/9727673/list-directory-tree-structure-in-python
        """
        contents = list(directory.iterdir())
        # contents each get pointers that are ├── with a final └── :
        pointers = [DIRECTORY_TREE_TEE] * (len(contents) - 1) + [DIRECTORY_TREE_LAST]
        for pointer, path in zip(pointers, contents):
            yield prefix + pointer + path.name
            if path.is_dir():  # extend the prefix and recurse:
                extension = DIRECTORY_TREE_BRANCH if pointer == DIRECTORY_TREE_TEE else DIRECTORY_TREE_SPACE
                # i.e. space because last, └── , above so no more |
                yield from Utils.print_directory_tree(path, prefix=prefix + extension)

    @staticmethod
    def flatten_dict(dictionary: dict, parent_key='', separator='.'):
        """
        Takes in a nested dictionary and returns a flattened dict

        Source: https://stackoverflow.com/questions/6027558/flatten-nested-dictionaries-compressing-keys
        """
        items = []
        for key, value in dictionary.items():
            new_key = parent_key + separator + key if parent_key else key
            if isinstance(value, MutableMapping):
                items.extend(Utils.flatten_dict(value, new_key, separator=separator).items())
            else:
                items.append((new_key, value))
        return dict(items)

    @staticmethod
    def is_test_mode() -> bool:
        return Utils.get_as_bool(EnvironmentUtils.res_test_mode(), False)
