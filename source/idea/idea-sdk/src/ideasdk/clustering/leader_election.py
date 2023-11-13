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
from ideadatamodel.constants import SERVICE_ID_LEADER_ELECTION
from ideasdk.protocols import SocaContextProtocol
from ideasdk.service import SocaService
from ideasdk.shell import ShellInvoker
from ideasdk.clustering import leader_election_constants

from threading import Thread, Event
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockError


class LeaderElection(SocaService):

    def __init__(self, context: SocaContextProtocol, leader_election_interval: int = 30):
        super().__init__(context)
        self.context = context
        self.logger = context.logger('leader-election')

        self.leader_election_interval = leader_election_interval

        self._exit = Event()

        self.LEADER_ELECTION_KEY = f'{self.context.module_id()}-leader-node'
        self._is_leader = Event()

        self.shell = ShellInvoker()

        self.leader_election_thread = Thread(
            target=self.loop,
            name='leader-election'
        )
        self.leader_election_thread.start()

    def service_id(self) -> str:
        return SERVICE_ID_LEADER_ELECTION

    def _set_leader(self):
        self._is_leader.set()
        self.context.broadcast().publish(self.service_id(), message=leader_election_constants.LEADER_APPOINTED)

    def _unset_leader(self):
        self._is_leader.clear()
        self.context.broadcast().publish(self.service_id(), message=leader_election_constants.LEADER_DISMISSED)

    def loop(self):
        while not self._exit.is_set():
            try:

                if self.is_leader():
                    continue

                self.context.distributed_lock().acquire(key=self.LEADER_ELECTION_KEY)
                hostname = self.shell.invoke('hostname -s', shell=True)
                self.logger.info(f'leader appointed: {hostname.stdout}')
                self._set_leader()

            except DynamoDBLockError as e:
                if e.code == DynamoDBLockError.ACQUIRE_TIMEOUT:
                    pass
                else:
                    self.logger.exception(f'leader election failed: {e}')
            except Exception as e:
                self.logger.exception(f'leader election failed: {e}')
            finally:
                self._exit.wait(self.leader_election_interval)

    def is_leader(self) -> bool:
        return self._is_leader.is_set()

    def start(self):
        pass

    def stop(self):
        self.logger.info('stopping leader election ...')

        self._exit.set()

        self.context.distributed_lock().release(self.LEADER_ELECTION_KEY)
        self._unset_leader()

        if self.leader_election_thread.is_alive():
            self.leader_election_thread.join()
