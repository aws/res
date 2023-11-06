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
    'User',
    'Group',
    'AuthResult',
    'DecodedToken'
)

from ideadatamodel import SocaBaseModel

from typing import Optional, List
from datetime import datetime


class User(SocaBaseModel):
    username: Optional[str]
    password: Optional[str]
    email: Optional[str]
    uid: Optional[int]
    gid: Optional[int]
    group_name: Optional[str]
    ds_group_name: Optional[str]
    additional_groups: Optional[List[str]]
    login_shell: Optional[str]
    home_dir: Optional[str]
    sudo: Optional[bool]
    status: Optional[str]
    enabled: Optional[bool]
    password_last_set: Optional[datetime]
    password_max_age: Optional[float]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]
    synced_on: Optional[datetime]
    role: Optional[str]
    is_active: Optional[bool]


class Group(SocaBaseModel):
    title: Optional[str]
    description: Optional[str]
    name: Optional[str]
    ds_name: Optional[str]
    gid: Optional[int]
    group_type: Optional[str]
    ref: Optional[str]
    enabled: Optional[bool]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]
    synced_on: Optional[datetime]
    type: Optional[str]
    role: Optional[str]


class AuthResult(SocaBaseModel):
    access_token: Optional[str]
    id_token: Optional[str]
    refresh_token: Optional[str]
    expires_in: Optional[int]
    token_type: Optional[str]


class DecodedToken(SocaBaseModel):
    pass
