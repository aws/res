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

from ideasdk.protocols import SocaContextProtocol, MetricsServiceProtocol
from ideasdk.metrics import FastWriteCounter, MetricTimer
from ideasdk.utils import Utils
from ideadatamodel import constants

from typing import List, Optional, Dict
import arrow


class BaseMetrics:
    """
    Base class for IDEA metrics

    modules are expected to subclass `BaseMetrics` and create concrete metric definitions to avoid any metric
    discrepancies related to typos across the code

    The implementation of this class is "inspired" from https://github.com/awslabs/cloudwatch-fluent-metrics
    """

    def __init__(self, context: SocaContextProtocol, namespace: str = None, use_stream_id: bool = False, split_dimensions: bool = True):
        self._context = context
        self._logger = context.logger()
        self.required_dimensions = []
        self.dimensions = []
        self.timers = {}
        self.dimension_stack = []
        self.namespace = namespace
        self.stream_id = None
        self.use_stream_id = use_stream_id
        self.split_dimensions = split_dimensions
        if self.use_stream_id:
            self.stream_id = Utils.uuid()
            self.with_dimension('MetricStreamId', self.stream_id)
        else:
            self.stream_id = None

        self.counters: List[FastWriteCounter] = []

    @property
    def metrics_provider(self) -> str:
        return self._context.config().get_string('metrics.provider')

    def is_metrics_collection_enabled(self) -> bool:
        return Utils.is_not_empty(self.metrics_provider)

    def build_counter(self, name: str) -> FastWriteCounter:
        counter = FastWriteCounter(name=name)
        self.counters.append(counter)
        return counter

    def with_stream_id(self, stream_id: str):
        self.stream_id = stream_id
        self.with_dimension('MetricStreamId', self.stream_id)
        return self

    def with_dimension(self, name, value):
        self.without_dimension(name)
        self.dimensions.append({'Name': name, 'Value': value})
        return self

    def with_required_dimension(self, name, value):
        self.without_required_dimension(name)
        self.required_dimensions.append({'Name': name, 'Value': value})
        return self

    def without_dimension(self, name):
        if not self.does_dimension_exist(name):
            return
        self.dimensions = [item for item in self.dimensions if not item['Name'] == name]
        return self

    def without_required_dimension(self, name):
        if not self.does_required_dimension_exist(name):
            return
        self.required_dimensions = [item for item in self.required_dimensions if not item['Name'] == name]
        return self

    def does_dimension_exist(self, name):
        d = [item for item in self.dimensions if item['Name'] == name]
        if d:
            return True
        else:
            return False

    def does_required_dimension_exist(self, name):
        d = [item for item in self.required_dimensions if item['Name'] == name]
        if d:
            return True
        else:
            return False

    def get_dimension_value(self, name):
        d = [item for item in self.dimensions if item['Name'] == name]
        if d:
            return d[0]['Value']
        else:
            return None

    def get_required_dimension_value(self, name):
        d = [item for item in self.required_dimensions if item['Name'] == name]
        if d:
            return d[0]['Value']
        else:
            return None

    def with_timer(self, timer):
        self.timers[timer] = MetricTimer()
        return self

    def without_timer(self, timer):
        if timer in self.timers.keys():
            del self.timers[timer]
        return self

    def get_timer(self, timer):
        if timer in self.timers.keys():
            return self.timers[timer]
        else:
            return None

    def push_dimensions(self):
        self.dimension_stack.append(self.dimensions)
        self.dimensions = []
        if self.use_stream_id and self.stream_id:
            self.with_stream_id(self.stream_id)
        return self

    def pop_dimensions(self):
        self.dimensions = self.dimension_stack.pop()
        return self

    def elapsed(self, **kwargs):
        timer_name = kwargs.get('TimerName')
        metric_name = kwargs.get('MetricName')

        if timer_name not in self.timers.keys():
            self._logger.warning(f'No timer named {timer_name}')
            return self

        self.milliseconds(
            MetricName=metric_name,
            Value=self.timers[timer_name].elapsed_in_ms()
        )
        return self

    def milliseconds(self, **kwargs):
        if not self.is_metrics_collection_enabled():
            return self

        if self.metrics_provider == constants.METRICS_PROVIDER_CLOUDWATCH:
            return self._log(**kwargs, MetricType='Counter', Unit='Milliseconds')
        else:
            return self._log(**kwargs, MetricType='Summary', Unit='Milliseconds')

    def seconds(self, **kwargs):
        if not self.is_metrics_collection_enabled():
            return self

        if self.metrics_provider == constants.METRICS_PROVIDER_CLOUDWATCH:
            return self._log(**kwargs, MetricType='Counter', Unit='Seconds')
        else:
            return self._log(**kwargs, MetricType='Summary', Unit='Seconds')

    def count(self, **kwargs):
        return self._log(**kwargs, MetricType='Counter', Unit='Count')

    def invocation(self, **kwargs):
        """
        there is no better way to represent a Prometheus Summary in CloudWatch Metrics.
        Summary in prometheus are computed client side, but with cloudwatch aggregation is performed on the timestream on server based on StorageResolution
        :param kwargs:
        :return:
        """
        if not self.is_metrics_collection_enabled():
            return self

        if self.metrics_provider == constants.METRICS_PROVIDER_CLOUDWATCH:
            metric_name = kwargs.get('MetricName')
            metric_name_count = f'{metric_name}_count'
            metric_name_duration = f'{metric_name}_duration'
            self.count(MetricName=metric_name_count, Value=1)
            duration_ms = kwargs.get('Value', 1)
            self.milliseconds(MetricName=metric_name_duration, Value=duration_ms)
        else:
            self._log(**kwargs, MetricType='Summary', Unit='Milliseconds')

    def _log(self, **kwargs):

        if not self.is_metrics_collection_enabled():
            return self

        timestamp = kwargs.get('Timestamp', arrow.utcnow().format('YYYY-MM-DD HH:mm:ss ZZ'))
        value = float(kwargs.get('Value', 1))
        unit = kwargs.get('Unit')
        namespace = self.namespace
        description = kwargs.get('description')
        md = []

        def build_metric(dimensions: List[Dict]) -> Dict:
            metric = {
                'MetricType': kwargs['MetricType'],
                'MetricName': kwargs['MetricName'],
                'Dimensions': dimensions,
                'Timestamp': timestamp,
                'Value': value,
                'Unit': unit
            }
            if namespace is not None:
                metric['Namespace'] = self.namespace
            if description is not None:
                metric['Description'] = description
            return metric

        if self.split_dimensions:
            for dimension in self.dimensions:
                md.append(build_metric(dimensions=self.required_dimensions + [dimension]))

        md.append(build_metric(dimensions=self.required_dimensions + self.dimensions))

        metrics_service: Optional[MetricsServiceProtocol] = self._context.service_registry().get_service('metrics-service')
        if metrics_service is not None:
            metrics_service.publish(md)

        return self
