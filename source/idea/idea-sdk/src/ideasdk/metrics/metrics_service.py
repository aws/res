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
from ideadatamodel.constants import SERVICE_ID_METRICS
from ideasdk.service import SocaService
from ideasdk.protocols import MetricsServiceProtocol, MetricsAccumulatorProtocol, SocaContextProtocol
from ideasdk.metrics.metrics_provider_factory import MetricsProviderFactory
from ideasdk.utils import Utils

from typing import Optional, List, Dict
import queue
from threading import Thread, Event
from collections import OrderedDict

BACKLOG_WAIT_TIMEOUT_SECS = 1
FLUSH_AFTER_SECS = 10
BACKLOG_MAX_SIZE = 10000

ACCUMULATED_METRICS_INTERVAL_SECS = 60  # do not change!


class MetricsService(SocaService, MetricsServiceProtocol):

    def __init__(self, context: SocaContextProtocol, default_namespace: Optional[str] = None):
        super().__init__(context=context)
        self._context = context
        self._logger = context.logger('metrics-service')

        if Utils.is_empty(default_namespace):
            default_namespace = f'{context.cluster_name()}/{context.module_id()}'
        self.default_namespace = default_namespace

        self._exit = Event()

        self._accumulators: Optional[OrderedDict[str, MetricsAccumulatorProtocol]] = OrderedDict()
        self._factory = MetricsProviderFactory(context=self._context)
        self._metrics_backlog_queue = queue.Queue(maxsize=BACKLOG_MAX_SIZE)

        self._backlog_processor_thread = Thread(
            name='metrics-backlog',
            target=self._poll_backlog
        )
        self._system_metrics_thread = Thread(
            name='accumulated-metrics',
            target=self._accumulated_metrics_loop
        )

        self._backlog_processor_thread.start()
        self._system_metrics_thread.start()

    def service_id(self) -> str:
        return SERVICE_ID_METRICS

    def _poll_backlog(self):
        current = 0
        while not self._exit.is_set():
            try:
                metric_data = self._metrics_backlog_queue.get(block=True, timeout=BACKLOG_WAIT_TIMEOUT_SECS)
                if metric_data is None or len(metric_data) == 0:
                    continue

                namespaces = {}
                for entry in metric_data:
                    namespace = Utils.get_value_as_string('Namespace', entry)
                    if namespace is None:
                        namespace = self.default_namespace
                        entry['Namespace'] = self.default_namespace

                    if namespace in namespaces:
                        namespace_metrics = namespaces[namespace]
                    else:
                        namespace_metrics = []
                        namespaces[namespace] = namespace_metrics
                    namespace_metrics.append(entry)

                for namespace, namespace_metrics in namespaces.items():
                    provider = self._factory.get_provider(namespace)
                    provider.log(metric_data=namespace_metrics)

                current += 1
            except queue.Empty:
                # flush any pending entries after 10 seconds delay
                # in high volume scenarios, this should not occur frequently
                if current >= FLUSH_AFTER_SECS:
                    self._factory.flush()
                    current = 0
            except Exception as e:
                self._logger.exception(f'exception while processing metrics backlog: {e}')

        try:
            self._factory.flush()
        except Exception as e:
            self._logger.exception(f'failed to flush any pending metrics: {e}')

    def _accumulated_metrics_loop(self):
        while not self._exit.is_set():
            try:

                # publish accumulated metrics only from the leader node
                if not self._context.is_leader():
                    self._logger.debug('not a leader node. skip publishing accumulated metrics.')
                    continue

                for accumulator_id, accumulator in self._accumulators.items():
                    try:
                        self._logger.debug(f'publishing accumulated metrics: {accumulator_id}')
                        accumulator.publish_metrics()
                    except Exception as e:
                        self._logger.exception(f'failed to collect metrics from: {accumulator_id}, error: {e}')

            except Exception as e:
                self._logger.exception(f'exception while collecting system metrics: {e}')
            finally:
                self._exit.wait(ACCUMULATED_METRICS_INTERVAL_SECS)

    def publish(self, metric_data: List[Dict]):
        if metric_data is None:
            return
        self._metrics_backlog_queue.put(metric_data)

    def register_accumulator(self, accumulator: MetricsAccumulatorProtocol):
        self._logger.info(f'registering metrics accumulator: {accumulator.accumulator_id}')
        self._accumulators[accumulator.accumulator_id] = accumulator

    def start(self):
        pass

    def stop(self):
        self._logger.info('stopping metrics service ...')
        self._exit.set()
        if self._backlog_processor_thread.is_alive():
            self._backlog_processor_thread.join()
        if self._system_metrics_thread.is_alive():
            self._system_metrics_thread.join()
