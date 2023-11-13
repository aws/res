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

from ideasdk.protocols import SocaContextProtocol, MetricsServiceProtocol, MetricsAccumulatorProtocol
from abc import abstractmethod
from typing import Optional


class BaseAccumulator(MetricsAccumulatorProtocol):

    def __init__(self, context: SocaContextProtocol):
        metrics_service: Optional[MetricsServiceProtocol] = context.service_registry().get_service('metrics-service')
        if metrics_service is not None:
            metrics_service.register_accumulator(self)

    @property
    @abstractmethod
    def accumulator_id(self):
        ...

    @abstractmethod
    def publish_metrics(self) -> None:
        ...
