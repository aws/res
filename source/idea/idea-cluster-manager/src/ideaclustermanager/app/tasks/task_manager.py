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

from ideasdk.context import SocaContext
from ideasdk.service import SocaService
from ideasdk.utils import Utils

from ideaclustermanager.app.tasks.base_task import BaseTask

from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor
import threading

MAX_WORKERS = 1  # must be between 1 and 10


class TaskManager(SocaService):

    def __init__(self, context: SocaContext, tasks: List[BaseTask]):
        super().__init__(context)

        self.context = context
        self.logger = context.logger('task-manager')

        self.tasks: Dict[str, BaseTask] = {}
        for task in tasks:
            self.tasks[task.get_name()] = task

        self.exit = threading.Event()

        self.task_monitor_thread = threading.Thread(
            target=self.task_queue_listener,
            name='task-monitor'
        )
        self.task_executors = ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix='task-executor'
        )

    def get_task_queue_url(self) -> str:
        return self.context.config().get_string('cluster-manager.task_queue_url', required=True)

    def execute_task(self, sqs_message: Dict):
        task_name = None
        try:
            message_body = Utils.get_value_as_string('Body', sqs_message)
            receipt_handle = Utils.get_value_as_string('ReceiptHandle', sqs_message)
            task_message = Utils.from_json(message_body)
            task_name = task_message['name']
            task_payload = task_message['payload']
            self.logger.info(f'executing task: {task_name}, payload: {Utils.to_json(task_payload)}')

            if task_name not in self.tasks:
                self.logger.warning(f'not task registered for task name: {task_name}')
                return

            task = self.tasks[task_name]

            task.invoke(task_payload)

            self.context.aws().sqs().delete_message(
                QueueUrl=self.get_task_queue_url(),
                ReceiptHandle=receipt_handle
            )

        except Exception as e:
            self.logger.exception(f'failed to execute task: {task_name} - {e}')

    def task_queue_listener(self):
        while not self.exit.is_set():
            try:
                result = self.context.aws().sqs().receive_message(
                    QueueUrl=self.get_task_queue_url(),
                    MaxNumberOfMessages=MAX_WORKERS,
                    WaitTimeSeconds=20
                )
                messages = Utils.get_value_as_list('Messages', result, [])
                if len(messages) == 0:
                    continue
                self.logger.info(f'received {len(messages)} messages')
                for message in messages:
                    self.task_executors.submit(lambda message_: self.execute_task(message_), message)

            except Exception as e:
                self.logger.exception(f'failed to poll queue: {e}')

    def send(self, task_name: str, payload: Dict, message_group_id: str = None, message_dedupe_id: str = None):
        task_message = {
            'name': task_name,
            'payload': payload
        }

        if Utils.is_empty(message_group_id):
            message_group_id = task_name
        if Utils.is_empty(message_dedupe_id):
            message_dedupe_id = Utils.sha256(Utils.to_json(task_message))

        self.logger.debug(f'send task: {task_name}, message group id: {message_group_id}, DedupeId: {message_dedupe_id}')
        self.context.aws().sqs().send_message(
            QueueUrl=self.get_task_queue_url(),
            MessageBody=Utils.to_json(task_message),
            MessageDeduplicationId=message_dedupe_id,
            MessageGroupId=message_group_id
        )

    def start(self):
        self.task_monitor_thread.start()

    def stop(self):
        self.exit.set()
        if self.task_monitor_thread.is_alive():
            self.task_monitor_thread.join()
        self.task_executors.shutdown(wait=True)
