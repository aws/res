#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Any

from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class SharedStorageKey(Key):
    SHARED_HOME_FILESYSTEM_ID = "SharedHomeFileSystemId"


@dataclass
class SharedStorageParameters(Base):
    existing_home_fs_id: str = Base.parameter(
        Attributes(
            id=SharedStorageKey.SHARED_HOME_FILESYSTEM_ID,
            type="String",
            description=(
                "Please provide id of a home file system to be mounted on all VDI instances."
            ),
            allowed_pattern="fs-[0-9a-f]{17}",
            constraint_description="SharedHomeFileSystemId must begin with 'fs-', only contain letters (a-f) or numbers(0-9) "
            "and must be 20 characters in length",
        )
    )


class SharedStorageParameterGroups:
    parameter_group_for_shared_storage: dict[str, Any] = {
        "Label": {"default": "Shared Storage details"},
        "Parameters": [
            SharedStorageKey.SHARED_HOME_FILESYSTEM_ID,
        ],
    }
