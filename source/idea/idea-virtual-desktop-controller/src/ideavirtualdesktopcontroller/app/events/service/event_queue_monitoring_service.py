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
import math
import ideavirtualdesktopcontroller
from ideasdk.thread_pool.idea_thread import IdeaThread
from ideasdk.thread_pool.idea_threadpool_service import IdeaThreadpoolService
from ideasdk.utils import Utils
from ideavirtualdesktopcontroller.app.events.service.events_handler_thread import EventsHandlerThread


class EventsQueueMonitoringService(IdeaThreadpoolService):

    def __init__(self, context: ideavirtualdesktopcontroller.AppContext):
        super().__init__(context, enforcement_frequency_per_min=2)
        self.context = context
        self.MESSAGE_COUNT_PER_THREAD = 3

    def calculate_number_of_threads_required(self) -> int:
        min_threads = self.context.config().get_int('virtual-desktop-controller.controller.request_handler_threads.min', default=1)
        max_queue_monitor_threads = self.context.config().get_int('virtual-desktop-controller.controller.request_handler_threads.max', default=min_threads)

        response = self.context.aws().sqs().get_queue_attributes(
            QueueUrl=self.context.config().get_string('virtual-desktop-controller.events_sqs_queue_url', required=True),
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible', 'ApproximateNumberOfMessagesDelayed']
        )

        attributes = Utils.get_value_as_dict('Attributes', response, {})
        num_of_messages = Utils.get_value_as_int('ApproximateNumberOfMessages', attributes, 1)
        num_of_messages += Utils.get_value_as_int('ApproximateNumberOfMessagesNotVisible', attributes, 1)
        num_of_messages += Utils.get_value_as_int('ApproximateNumberOfMessagesDelayed', attributes, 1)

        self._logger.debug(f'ApproximateNumberOfMessages: {num_of_messages}')
        return min(max(min_threads, int(math.ceil(num_of_messages / self.MESSAGE_COUNT_PER_THREAD))), max_queue_monitor_threads)

    def provision_new_thread(self, thread_id: int) -> IdeaThread:
        return EventsHandlerThread(
            context=self.context,
            thread_number=thread_id,
            num_of_messages_to_retrieve_per_call=1,
            wait_time=20
        )
