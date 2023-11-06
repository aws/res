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

from ideasdk.protocols import MetricsProviderProtocol, SocaContextProtocol
from ideasdk.utils import Utils

from typing import List, Dict
from prometheus_client import Counter, Summary
from threading import RLock


class PrometheusMetrics(MetricsProviderProtocol):
    """
    Expose IDEA Custom Metrics as Prometheus Metrics
    """

    def __init__(self, context: SocaContextProtocol, namespace: str):
        self.context = context
        self.logger = context.logger('prometheus-metrics')
        self.namespace = namespace
        tokens = namespace.split('/')

        self.cluster_name = None
        self.module = None
        self.component = None
        if len(tokens) > 0:
            self.cluster_name = tokens[0]
        if len(tokens) > 1:
            self.module = tokens[1]
        if len(tokens) > 2:
            self.component = tokens[2]

        self._metrics = {}
        self._lock = RLock()

    @staticmethod
    def _build_metric_key(entry: Dict) -> str:
        keys = [
            entry['Namespace'],
            entry['MetricName'],
            entry['MetricType']
        ]
        dimensions = Utils.get_value_as_list('Dimensions', entry)
        if dimensions is not None:
            for dimension in dimensions:
                keys.append(dimension['Name'])

        return Utils.sha256(';'.join(keys))

    def _get_or_create_metric(self, entry: Dict):

        key = self._build_metric_key(entry)

        metric = None
        with self._lock:
            if key in self._metrics:
                return self._metrics[key]

        metric_type = entry['MetricType']
        metric_name = entry['MetricName']
        documentation = Utils.get_value_as_string('Description', entry, '')

        labels = []
        namespace_tokens = self.namespace.split('/')
        for index, token in enumerate(namespace_tokens):
            if index == 0:
                labels.append('cluster_name')
                continue
            if index == 1:
                labels.append('module_id')
                continue
            if index == 2:
                labels.append('component')

        dimensions = Utils.get_value_as_list('Dimensions', entry)
        if dimensions is not None:
            for dimension in dimensions:
                labels.append(dimension['Name'])

        unit = Utils.get_value_as_string('Unit', entry, '')
        unit = unit.lower()
        if unit == 'count':
            unit = 'total'

        prometheus_metric_name = f'{metric_name}_{unit}'

        if metric_type == 'Counter':
            metric = Counter(
                name=prometheus_metric_name,
                documentation=documentation,
                labelnames=labels
            )
        elif metric_type == 'Summary':
            metric = Summary(
                name=prometheus_metric_name,
                documentation=documentation,
                labelnames=labels
            )

        if metric is not None:
            with self._lock:
                self._metrics[key] = metric

        return metric

    def _process_metric(self, entry: Dict):

        metric = self._get_or_create_metric(entry)

        if metric is None:
            metric_type = entry.get('MetricType')
            self.logger.warning(f'metric not supported for metric type: {metric_type}')
            return

        labels = []
        namespace_tokens = self.namespace.split('/')
        for index, token in enumerate(namespace_tokens):
            if index == 0:
                labels.append(token)
                continue
            if index == 1:
                labels.append(token)
                continue
            if index == 2:
                labels.append(token)

        dimensions = Utils.get_value_as_list('Dimensions', entry)
        if dimensions is not None:
            for dimension in dimensions:
                labels.append(dimension['Value'])

        value = entry['Value']
        if isinstance(metric, Counter):
            metric.labels(*labels).inc(value)
        elif isinstance(metric, Summary):
            metric.labels(*labels).observe(value)

    def log(self, metric_data: List[Dict]):
        for entry in metric_data:
            self._process_metric(entry)

    def flush(self):
        pass
