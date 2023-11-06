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
import threading
from enum import Enum
from typing import Optional, Dict, List

from ideadatamodel import SocaBaseModel
from ideadatamodel.constants import SERVICE_ID_ANALYTICS
from ideasdk.aws.opensearch.aws_opensearch_client import AwsOpenSearchClient
from ideasdk.protocols import SocaContextProtocol, AnalyticsServiceProtocol
from ideasdk.service import SocaService
from ideasdk.utils import Utils


class EntryAction(str, Enum):
    UPDATE_ENTRY = 'UPDATE_ENTRY'
    DELETE_ENTRY = 'DELETE_ENTRY'
    CREATE_ENTRY = 'CREATE_ENTRY'


class EntryContent(SocaBaseModel):
    index_id: Optional[str]
    entry_record: Optional[dict]


class AnalyticsEntry(SocaBaseModel):
    entry_id: str
    entry_action: EntryAction
    entry_content: EntryContent


class AnalyticsService(SocaService, AnalyticsServiceProtocol):

    def __init__(self, context: SocaContextProtocol):
        super().__init__(context=context)
        self.MAX_BUFFER_SIZE = 20
        self.MAX_WAIT_TIME_MS = 1000
        self.context = context
        self._logger = context.logger('analytics-service')
        self._buffer_lock = threading.RLock()
        self._buffer_size_limit_reached_condition = threading.Condition()
        self._buffer: Optional[List[AnalyticsEntry]] = []
        self._buffer_processing_thread: Optional[threading.Thread] = None
        self._exit = threading.Event()
        self.os_client = AwsOpenSearchClient(self.context)
        self._initialize()

    def service_id(self) -> str:
        return SERVICE_ID_ANALYTICS

    def start(self):
        pass

    def _initialize(self):
        self._logger.info('Starting Analytics Service ...')
        # until I get positive status from Open Search -> wait here.
        self._buffer_processing_thread = threading.Thread(
            name='buffer-processing-thread',
            target=self._process_buffer
        )
        self._buffer_processing_thread.start()

    def _process_buffer(self):
        while not self._exit.is_set():
            self._buffer_size_limit_reached_condition.acquire()
            self._buffer_size_limit_reached_condition.wait(timeout=self.MAX_WAIT_TIME_MS / 1000)
            self._buffer_size_limit_reached_condition.release()
            self._post_entries_to_kinesis()

    def _post_entries_to_kinesis(self):
        with self._buffer_lock:
            records = []
            if Utils.is_empty(self._buffer):
                return

            for entry in self._buffer:
                records.append({
                    'Data': Utils.to_bytes(Utils.to_json({
                        'index_id': entry.entry_content.index_id,
                        'entry': entry.entry_content.entry_record,
                        'document_id': entry.entry_id,
                        'action': entry.entry_action,
                        'timestamp': Utils.current_time_ms()
                    })),
                    'PartitionKey': entry.entry_id
                })

            stream_name = self.context.config().get_string('analytics.kinesis.stream_name', required=True)
            self._logger.info(f'posting {len(records)} record(s) to analytics stream...')
            response = self.context.aws().kinesis().put_records(
                Records=records,
                StreamName=stream_name
            )
            # TODO: handle failure/success
            self._buffer = []

    def _enforce_buffer_processing(self):
        try:
            self._buffer_size_limit_reached_condition.acquire()
            self._buffer_size_limit_reached_condition.notify_all()
        finally:
            self._buffer_size_limit_reached_condition.release()

    def post_entry(self, document: AnalyticsEntry):
        with self._buffer_lock:
            self._buffer.append(document)
            self._logger.debug(f'Added entry to buffer ... Buffer Size: {len(self._buffer)}')

            if len(self._buffer) >= self.MAX_BUFFER_SIZE:
                self._enforce_buffer_processing()

    def initialize_template(self, template_name: str, template_body: Dict) -> int:
        new_version = Utils.get_value_as_int('version', template_body, default=1)
        self._logger.info(f'new template version for {template_name} is {new_version}')
        current_template = self.os_client.get_template(template_name)
        if Utils.is_not_empty(current_template):
            self._logger.info(f'current template is not empty')
            self._logger.debug(current_template)
            current_version = Utils.get_value_as_int('version', Utils.get_value_as_dict(template_name, current_template, {}), default=-1)
            self._logger.info(f'current version = {current_version}')
            if int(new_version) <= int(current_version):
                self._logger.info('Trying to add the same or older version of the template. Ignoring request.')
                return new_version

        response = self.os_client.put_template(template_name, template_body)
        if not Utils.get_value_as_bool('acknowledged', response, default=False):
            self._logger.info(f'There is some error. Need to check later. response: {response}')
        self._logger.error(f'new version being returned is {new_version}')
        return new_version

    def stop(self):
        self._logger.error('Stopping Analytics Service ...')
        self._exit.set()
        self._enforce_buffer_processing()
        if self._buffer_processing_thread is not None and self._buffer_processing_thread.is_alive():
            self._buffer_processing_thread.join()
