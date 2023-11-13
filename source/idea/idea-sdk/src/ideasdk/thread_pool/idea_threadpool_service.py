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
from abc import abstractmethod
from threading import Thread, Event
from typing import Optional, Set, List

from ideasdk.protocols import SocaContextProtocol
from ideasdk.service import SocaService
from ideasdk.thread_pool.idea_thread import IdeaThread
from ideasdk.utils import Utils


class IdeaThreadpoolService(SocaService):

    def __init__(self, context: SocaContextProtocol, enforcement_frequency_per_min: int):
        super().__init__(context)
        self.ENFORCEMENT_FREQUENCY_PER_MIN = enforcement_frequency_per_min
        self._logger = context.logger('idea-threadpool-service')
        self._is_running = False
        self._service_thread: Optional[Thread] = None
        self._all_threads: Set[IdeaThread] = set()
        self._active_threads: List[IdeaThread] = []
        self._exit = Event()

    def _initialize(self):
        self._service_thread = Thread(
            name='service-thread',
            target=self._adjust_thread_counts
        )
        self._service_thread.start()

    def _cleanup_inactive_threads(self):
        if Utils.is_empty(self._all_threads):
            return

        threads_to_remove = []
        for thread in self._all_threads:
            if not thread.is_alive():
                threads_to_remove.append(thread)

        for thread in threads_to_remove:
            self._all_threads.remove(thread)

    def _adjust_thread_counts(self):
        while not self._exit.is_set():
            try:
                self._cleanup_inactive_threads()
                count = self.calculate_number_of_threads_required()
                self._enforce_thread_count(count)
            except Exception as e:
                self._logger.exception(f'failed to process sqs queue: {e}')
            finally:
                self._exit.wait(60 // self.ENFORCEMENT_FREQUENCY_PER_MIN)

    def _enforce_thread_count(self, count: int):
        self._logger.debug(f'Enforcing Thread count: {count}')
        if len(self._all_threads) == count:
            self._logger.debug('The count is the same, we do not need to do anything. NO=OP. Returning.')
            return

        if len(self._all_threads) > count:
            self._logger.debug(f'Current thread count: {len(self._all_threads)}. Required: {count}. Need to terminate threads')
            # need to mark certain threads for termination
            if len(self._active_threads) > count:
                # there are actual threads that need to be marked for termination
                self._logger.debug('Marked a thread for termination')
                for i in range(len(self._active_threads) - count):
                    self._active_threads.pop().exit.set()
            else:
                # we have already marked them for termination, they just haven't terminated yet.
                # we can eventually add more logic here. But for now. NO-OP
                self._logger.debug('No=OP case, where threads are already marked for termination')
                pass
        else:
            # need to provision new threads.
            self._logger.debug(f'Current thread count: {len(self._all_threads)}. Required: {count}. Need to provision new threads')
            for i in range(len(self._all_threads), count):
                self._logger.debug(f'creating thread with id: {i}')
                thread = self.provision_new_thread(i)
                thread.start()
                self._all_threads.add(thread)
                self._active_threads.append(thread)

    @abstractmethod
    def calculate_number_of_threads_required(self) -> int:
        ...

    @abstractmethod
    def provision_new_thread(self, thread_id: int) -> IdeaThread:
        ...

    def start(self):
        if self._is_running:
            return
        self._initialize()
        self._is_running = True

    def stop(self):
        self._logger.info('stopping idea-threadpool-service ...')
        self._exit.set()
        self._is_running = False
        self._service_thread.join()

        if Utils.is_not_empty(self._all_threads):
            for thread in self._all_threads:
                thread.exit.set()
                thread.join()
