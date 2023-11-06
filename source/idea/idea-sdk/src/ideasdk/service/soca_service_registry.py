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

from ideasdk.protocols import SocaServiceRegistryProtocol, SocaServiceProtocol, SocaContextProtocol
from ideadatamodel import constants
from ideasdk.pubsub import SocaPubSub

from collections import OrderedDict
from typing import Optional


class SocaServiceRegistry(SocaServiceRegistryProtocol):
    def __init__(self, context: SocaContextProtocol):
        self._context = context
        self._logger = context.logger()
        self._services: OrderedDict[str, SocaServiceProtocol] = OrderedDict()
        self._broadcast = SocaPubSub(topic=constants.TOPIC_BROADCAST)
        self._broadcast.subscribe(listener=self.broadcast_handler)

    def broadcast_handler(self, sender, message):
        self._logger.info(f'received broadcast message from {sender}: {message}')
        for service in self.services():
            service.on_broadcast(message=message)

    def register(self, service: SocaServiceProtocol):
        service_id = service.service_id()
        self._logger.info(f'registering service: {service_id}')
        self._services[service_id] = service

    def get_service(self, service_id) -> Optional[SocaServiceProtocol]:
        if service_id in self._services:
            return self._services[service_id]
        return None

    def services(self):
        return self._services.values()
