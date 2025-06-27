#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.constants import GLOBAL_ALLOWED_INSTANCE_TYPES_KEY
from res.resources.dynamodb.dynamodb_stream_subscriber import IDynamoDBStreamSubscriber
from res.resources.software_stacks import update_software_stack_allowed_instance_types

from typing import Any, Dict, Optional


class GlobalAllowedInstanceTypesEventSubscriber(IDynamoDBStreamSubscriber):
    def on_create(self, entry: Dict[str, Any]) -> None:
        pass

    def on_update(self, old_entry: Dict[str, Any], new_entry: Dict[str, Any]) -> None:
        update_software_stack_allowed_instance_types(new_entry.get("value"))

    def on_delete(self, entry: Dict[str, Any]) -> None:
        pass

    def is_entry_monitored(self, entry: Dict[str, Any]) -> bool:
        return entry["key"] == GLOBAL_ALLOWED_INSTANCE_TYPES_KEY

    @property
    def subscriber_name(self) -> Optional[str]:
        return "global_allowed_instance_types"
