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
    'FileData',
    'FileList'
)

from ideadatamodel import SocaBaseModel

from typing import Optional, List
from datetime import datetime


class FileData(SocaBaseModel):
    owner: Optional[str]
    group: Optional[str]
    file_id: Optional[str]
    name: Optional[str]
    ext: Optional[str]
    is_dir: Optional[bool]
    is_hidden: Optional[bool]
    is_sym_link: Optional[bool]
    is_encrypted: Optional[bool]
    size: Optional[int]
    mod_date: Optional[datetime]
    children_count: Optional[int]
    color: Optional[str]
    icon: Optional[str]
    folder_chain_icon: Optional[str]
    thumbnail_url: Optional[str]


class FileList(SocaBaseModel):
    cwd: Optional[str]
    files: Optional[List[FileData]]
