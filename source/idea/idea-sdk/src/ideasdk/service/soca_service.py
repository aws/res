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

from ideadatamodel import constants
from ideasdk.protocols import SocaServiceProtocol, SocaContextProtocol

import abc


class SocaService(SocaServiceProtocol):

    def __init__(self, context: SocaContextProtocol):
        context.service_registry().register(service=self)

    def service_id(self) -> str:
        return self.__class__.__name__

    def on_broadcast(self, message: str):
        if constants.MESSAGE_RELOAD == message:
            self.on_reload()

    def on_reload(self):
        # inheriting services should override this if needed
        pass

    @abc.abstractmethod
    def start(self):
        ...

    @abc.abstractmethod
    def stop(self):
        pass
