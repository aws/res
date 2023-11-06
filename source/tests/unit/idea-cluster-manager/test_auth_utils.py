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

"""
Test Cases for AccountsService
"""

from typing import Optional

import pytest
import validators
from ideaclustermanager import AppContext
from ideaclustermanager.app.accounts.account_tasks import (
    CreateUserHomeDirectoryTask,
    SyncGroupInDirectoryServiceTask,
    SyncUserInDirectoryServiceTask,
)
from ideaclustermanager.app.accounts.auth_utils import AuthUtils as auth_utils
from ideaclustermanager.app.accounts.user_home_directory import UserHomeDirectory
from ideasdk.utils import Utils
from ideatestutils import IdeaTestProps

from ideadatamodel import (
    Group,
    ListUsersRequest,
    User,
    constants,
    errorcodes,
    exceptions,
)


def test_auth_utils_santize_sub_with_empty_argument_should_fail():
    """
    empty sub raises exception
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        auth_utils.sanitize_sub(sub="")
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "sub is required" in exc_info.value.message


def test_auth_utils_santize_sub_without_uuid_should_fail():
    with pytest.raises(exceptions.SocaException) as exc_info:
        auth_utils.sanitize_sub(sub="hello")
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "invalid sub(expected UUID): hello" in exc_info.value.message


def test_auth_utils_santize_sub_with_uuid_should_pass(monkeypatch):
    monkeypatch.setattr(validators, "uuid", lambda x: "1234")
    rc = auth_utils.sanitize_sub(sub="HeLlO")
    assert rc == "hello"


def test_auth_utils_invalid_operation_should_raise_exception():
    result = auth_utils.invalid_operation(message="hello")
    assert result.error_code == errorcodes.AUTH_INVALID_OPERATION
    assert result.message == "hello"
