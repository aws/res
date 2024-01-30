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
            type="AWS::SSM::Parameter::Value<String>",
            description=(
                "Please provide parameter store path to contain id of a home file system to be mounted on all VDI instances."
            ),
        )
    )


class SharedStorageParameterGroups:
    parameter_group_for_shared_storage: dict[str, Any] = {
        "Label": {"default": "Shared Storage details"},
        "Parameters": [
            SharedStorageKey.SHARED_HOME_FILESYSTEM_ID,
        ],
    }
