#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IDynamoDBStreamSubscriber(ABC):

    def __eq__(self, other) -> None:
        return self.subscriber_name == other.subscriber_name

    @abstractmethod
    def on_create(self, entry: Dict[str, Any]) -> None: ...

    @abstractmethod
    def on_update(self, old_entry: Dict, new_entry: Dict) -> None: ...

    @abstractmethod
    def on_delete(self, entry: Dict) -> None: ...

    def is_entry_monitored(self, entry: Dict) -> bool:
        return True

    @property
    def subscriber_name(self) -> Optional[str]:
        return None
