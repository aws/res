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
    'soca_exception',
    'invalid_job',
    'invalid_params',
    'exceeded_max_retries',
    'not_supported',
    'file_not_found',
    'unauthorized_access',
    'general_exception',
    'app_not_found',
    'invalid_session',
    'cluster_config_error',
    'table_import_failed',
    'table_merge_failed',
    'table_rollback_failed'
)

from ideadatamodel.exceptions import SocaException
from ideadatamodel import errorcodes

from typing import Optional, Any


def soca_exception(error_code: str, message: str,
                   exc: BaseException = None,
                   file: str = None, ref: Any = None):
    return SocaException(
        error_code=error_code,
        message=message,
        exc=exc,
        file=file,
        ref=ref
    )


def exceeded_max_retries(info: Optional[str] = None) -> SocaException:
    message = 'exceeded max retries'
    if info is not None:
        message += f': {info}'
    return SocaException(
        error_code=errorcodes.EXCEEDED_MAX_RETRIES,
        message=message
    )


def invalid_job(info: Optional[str] = None) -> SocaException:
    message = 'Invalid Job'
    if info is not None:
        message += f': {info}'
    return SocaException(
        error_code=errorcodes.SOCA_SCHEDULER_INVALID_JOB,
        message=message
    )


def invalid_session(info: Optional[str] = None) -> SocaException:
    message = 'Invalid session'
    if info is not None:
        message += f': {info}'
    return SocaException(
        error_code=errorcodes.INVALID_SESSION,
        message=message
    )


def invalid_params(info: Optional[str] = None) -> SocaException:
    message = 'Invalid parameters'
    if info is not None:
        message += f': {info}'
    return SocaException(
        error_code=errorcodes.INVALID_PARAMS,
        message=message
    )


def cluster_config_error(info: Optional[str] = None) -> SocaException:
    message = 'cluster configuration error'
    if info is not None:
        message += f': {info}'
    return SocaException(
        error_code=errorcodes.CONFIG_ERROR,
        message=message
    )


def file_not_found(info: Optional[str] = None) -> SocaException:
    message = 'File not found'
    if info is not None:
        message += f': {info}'
    return SocaException(
        error_code=errorcodes.FILE_NOT_FOUND,
        message=message
    )


def not_supported(info: Optional[str] = None) -> SocaException:
    message = 'Not supported'
    if info is not None:
        message += f': {info}'
    return SocaException(
        error_code=errorcodes.NOT_SUPPORTED,
        message=message
    )


def unauthorized_access(info: Optional[str] = None) -> SocaException:
    message = 'Unauthorized Access'
    if info is not None:
        message += f': {info}'
    return SocaException(
        error_code=errorcodes.UNAUTHORIZED_ACCESS,
        message=message
    )


def general_exception(message: str) -> SocaException:
    return SocaException(
        error_code=errorcodes.GENERAL_ERROR,
        message=message
    )


def app_not_found(message: str) -> SocaException:
    return SocaException(
        error_code=errorcodes.APP_NOT_FOUND,
        message=message
    )
    
def table_import_failed(message: str) -> SocaException:
    return SocaException(
        error_code=errorcodes.TABLE_IMPORT_FAILED,
        message=message
    )

def table_merge_failed(message: str) -> SocaException:
    return SocaException(
        error_code=errorcodes.TABLE_MERGE_FAILED,
        message=message
    )

def table_rollback_failed(message: str) -> SocaException:
    return SocaException(
        error_code=errorcodes.TABLE_ROLLBACK_FAILED,
        message=message
    )
