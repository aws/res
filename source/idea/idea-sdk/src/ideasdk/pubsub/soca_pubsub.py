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

from ideasdk.protocols import SocaPubSubProtocol, SubscriptionListener

from blinker import signal
from typing import Optional


class SocaPubSub(SocaPubSubProtocol):
    def __init__(self, topic: str, logger=None):
        self._signal = signal(topic)
        self._logger = logger

    def publish(self, sender: str, **kwargs):
        self._signal.send(sender, **kwargs)

    def subscribe(self, listener: SubscriptionListener, sender: Optional[str] = None):
        if self._logger:
            self._logger.debug(f'subscribe - topic: {self._signal.name}, listener: {listener}')

        if sender is None:
            self._signal.connect(listener)
        else:
            self._signal.connect(listener, sender=sender)

    def unsubscribe(self, listener: SubscriptionListener, sender: Optional[str] = None):
        if self._logger:
            self._logger.debug(f'unsubscribe - topic: {self._signal.name}, listener: {listener}')

        if sender is None:
            self._signal.disconnect(listener)
        else:
            self._signal.disconnect(listener, sender=sender)
