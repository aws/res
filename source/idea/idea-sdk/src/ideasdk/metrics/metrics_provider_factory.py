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

from ideadatamodel import constants, errorcodes, exceptions
from ideasdk.metrics.cloudwatch.cloudwatch_metrics import CloudWatchMetrics
from ideasdk.metrics.prometheus.prometheus_metrics import PrometheusMetrics
from ideasdk.metrics.null_metrics_provider import NullMetrics
from ideasdk.protocols import MetricsProviderFactoryProtocol, MetricsProviderProtocol, SocaContextProtocol
from ideasdk.utils import Utils

from typing import Dict
from threading import RLock


class MetricsProviderFactory(MetricsProviderFactoryProtocol):

    def __init__(self, context: SocaContextProtocol):
        self.context = context
        self.logger = context.logger()

        self._lock = RLock()
        self._metrics_providers: Dict[str, MetricsProviderProtocol] = {}

    def get_provider(self, namespace: str) -> MetricsProviderProtocol:

        if namespace in self._metrics_providers:
            return self._metrics_providers[namespace]

        provider_name = self.context.config().get_string('metrics.provider')
        if Utils.is_empty(provider_name):
            return NullMetrics(context=self.context)

        metrics_provider = None
        if provider_name == constants.METRICS_PROVIDER_CLOUDWATCH:
            metrics_provider = CloudWatchMetrics(context=self.context, namespace=namespace)
        elif provider_name in (constants.METRICS_PROVIDER_AMAZON_MANAGED_PROMETHEUS, constants.METRICS_PROVIDER_PROMETHEUS):
            metrics_provider = PrometheusMetrics(context=self.context, namespace=namespace)

        if metrics_provider is None:
            raise exceptions.SocaException(
                error_code=errorcodes.METRICS_PROVIDER_NOT_FOUND,
                message=f'metrics provider not found: {provider_name}'
            )

        with self._lock:
            self._metrics_providers[namespace] = metrics_provider

        return metrics_provider

    def flush(self):
        for namespace in self._metrics_providers:
            provider = self._metrics_providers[namespace]
            provider.flush()
