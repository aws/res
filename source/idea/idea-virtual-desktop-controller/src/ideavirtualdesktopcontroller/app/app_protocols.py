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
from abc import abstractmethod
from typing import Dict, List

from ideadatamodel import (
    VirtualDesktopSession,
    VirtualDesktopSessionConnectionInfo,
    VirtualDesktopSessionScreenshot
)
from ideasdk.protocols import SocaBaseProtocol


class DCVClientProtocol(SocaBaseProtocol):

    @abstractmethod
    def get_active_counts_for_sessions(self, sessions: List[VirtualDesktopSession]) -> List[VirtualDesktopSession]:
        ...

    @abstractmethod
    def describe_sessions(self, sessions: List[VirtualDesktopSession]) -> Dict:
        ...

    @abstractmethod
    def describe_servers(self) -> Dict:
        ...

    @abstractmethod
    def create_session(self, session: VirtualDesktopSession) -> VirtualDesktopSession:
        ...

    @abstractmethod
    def resume_session(self, session: VirtualDesktopSession) -> VirtualDesktopSession:
        ...

    @abstractmethod
    def get_session_connection_data(self, dcv_session_id: str, username: str) -> VirtualDesktopSessionConnectionInfo:
        ...

    @abstractmethod
    def get_session_screenshots(self, screenshots: List[VirtualDesktopSessionScreenshot]) -> (List[VirtualDesktopSessionScreenshot], List[VirtualDesktopSessionScreenshot]):
        ...

    @abstractmethod
    def delete_sessions(self, sessions: List[VirtualDesktopSession]) -> (List[VirtualDesktopSession], List[VirtualDesktopSession]):
        ...

    @abstractmethod
    def enforce_session_permissions(self, session: VirtualDesktopSession):
        ...


class VirtualDesktopQueueMessageHandlerProtocol(SocaBaseProtocol):

    @abstractmethod
    def handle_event(self, message_id: str, sender_id: str, message_body: Dict) -> bool:
        ...


class VirtualDesktopNotifiableDBProtocol(SocaBaseProtocol):

    @abstractmethod
    def trigger_update_event(self, hash_key: str, range_key: str, old_entry: dict, new_entry: dict) -> dict:
        ...

    @abstractmethod
    def trigger_delete_event(self, hash_key: str, range_key: str, deleted_entry: dict) -> dict:
        ...

    @abstractmethod
    def trigger_create_event(self, hash_key: str, range_key: str, new_entry: dict) -> dict:
        ...
