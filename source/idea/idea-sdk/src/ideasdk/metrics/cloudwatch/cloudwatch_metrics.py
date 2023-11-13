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

from typing import List, Dict

# This is defined by CloudWatch
PAGE_SIZE = 20


class CloudWatchMetrics(MetricsProviderProtocol):
    """
    Publish IDEA Custom Metrics to CloudWatch
    """

    def __init__(self, context: SocaContextProtocol, namespace: str, storage_resolution: int = None, max_items=PAGE_SIZE * 5):
        """
        :param context: ApplicationContext
        :param namespace: metrics namespace
        :param int storage_resolution: Valid values are 1 and 60. Setting this to 1 specifies this metric as a high-resolution metric,
        so that CloudWatch stores the metric with sub-minute resolution down to one second.
        Setting this to 60 specifies this metric as a regular-resolution metric, which CloudWatch stores at 1-minute resolution.
        :param max_items:
        """
        self._context = context
        self._logger = context.logger(name='cloudwatch-metrics')
        self.max_items = max_items
        self.namespace = namespace
        self.storage_resolution = storage_resolution
        self.buffers = {}

    def _send_metrics_to_cloudwatch(self, metric_data):
        if not metric_data or len(metric_data) == 0:
            return
        try:
            self._context.aws().cloudwatch().put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data,
            )
        except Exception as e:
            self._logger.error(f'failed to send metrics to cloudwatch: {e}')

    def _record_metric(self, metric_data):
        size = self._size()

        num_allowed = self.max_items - size
        if num_allowed < len(metric_data):
            num_dropped = len(metric_data) - num_allowed
            self._logger.warning(f'Dropping {num_dropped} out of {len(metric_data)} metrics')

        buffer = self.buffers.get(self.namespace, [])
        self.buffers[self.namespace] = buffer  # in case it wasn't set

        buffer += metric_data[:num_allowed]

        # clear as much WIP as possible
        self.flush(send_partial=False)

    def _size(self):
        return sum([len(buffer) for buffer in self.buffers.values()])

    def flush(self, send_partial=True):
        """
        Sends as much data as possible to CloudWatch. If send_partial is set to False,
        this only sends full pages. This way, it minimizes the API usage at the cost of
        delaying data.
        """

        for namespace, buffer in self.buffers.items():
            full_pages = len(buffer) // PAGE_SIZE
            for i in range(full_pages):
                start = i * PAGE_SIZE
                end = (i + 1) * PAGE_SIZE
                page = buffer[start:end]

                # ship it
                self._send_metrics_to_cloudwatch(page)
                self._logger.debug(f'published {len(page)} metrics to cloudwatch')

            start = full_pages * PAGE_SIZE
            end = len(buffer) % PAGE_SIZE
            if send_partial:
                # ship remaining items
                page = buffer[start:end]
                if len(page) > 0:
                    # ship it
                    self._send_metrics_to_cloudwatch(page)
                    self._logger.debug(f'published {len(page)} metrics to cloudwatch (partial)')

                # clear buffer
                self.buffers[namespace] = []

            # This condition isn't needed for correctness, it could be an else, it just
            # reduces memory churn. You should get the same result either way.
            elif full_pages > 0:
                # clear shipped items from buffer
                self.buffers[namespace] = buffer[start:]

        return self

    def log(self, metric_data: List[Dict]):
        for entry in metric_data:
            if self.storage_resolution is not None:
                entry['StorageResolution'] = self.storage_resolution
            if 'MetricType' in entry:
                del entry['MetricType']
            if 'Namespace' in entry:
                del entry['Namespace']
        self._record_metric(metric_data)
