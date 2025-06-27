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
import os

from ideadatamodel import exceptions, errorcodes, constants
from ideasdk.protocols import SocaContextProtocol
from ideasdk.protocols import ApiInvokerProtocol, SocaBaseProtocol
from ideasdk.server import SocaServer, SocaServerOptions
from ideasdk.utils import Utils
from ideasdk.config.cluster_config import ClusterConfig
from res.app.res_app import ResApp

from abc import abstractmethod
import time
from typing import Optional
from threading import Event


class SocaApp(ResApp):
    """
    Idea Application Base Class

    Applications are expected to extend SocaApp to initialize application specific context and functionality.
    """

    def __init__(self, context: SocaContextProtocol,
                 api_invoker: ApiInvokerProtocol,
                 server_options: SocaServerOptions = None,
                 **kwargs):
        self.context = context
        self.logger = context.logger(name=f'{context.module_id()}-app')
        self._api_invoker = api_invoker
        self._is_running = Event()
        self._is_reload = Event()

        self._server_options = server_options
        server_port = Utils.get_value_as_int('port', kwargs)
        if server_port is not None:
            if self._server_options is None:
                self._server_options = SocaServerOptions(port=server_port)
            else:
                self._server_options.port = server_port
        self.server: Optional[SocaServer] = None

        super().__init__(self.context.module_id(), self.logger)

    def app_warmup(self, delay=0.1, max_retries=3, error_wait_seconds=5):

        success = False
        retry_count = 0

        # indicates where to start from upon retry
        start = 0
        while not success and retry_count <= max_retries:
            try:

                if retry_count == 0:
                    self.logger.info(f'warm-up {self.app_name} dependencies ...')
                else:
                    self.logger.info(f'warm-up {self.app_name} dependencies - retry attempt: ({retry_count})')

                retry_count += 1

                # aws clients
                if start == 0:
                    supported_clients = self.context.aws().supported_clients()
                    for service_name in supported_clients:
                        self.context.aws().get_client(service_name=service_name)
                        time.sleep(delay)
                    start += 1

                # custom app warmup
                if start >= 1:
                    self.soca_app_warmup()

                success = True
            except Exception as e:
                self.logger.error(f'warm-up failed: {e}. Retrying in ({error_wait_seconds}) seconds ...')
                time.sleep(error_wait_seconds)

        if not success:
            raise exceptions.SocaException(
                error_code=errorcodes.GENERAL_ERROR,
                message=f'Failed to warm-up dependencies after ({max_retries}) retries. Exit.'
            )

    def soca_app_warmup(self):
        # to be overridden by child classes if required
        pass

    def app_initialize(self):
        self.logger.info(f'{self.app_name} configuration: {os.linesep}{self.context.config().as_yaml()}')

        self.server = SocaServer(
            context=self.context,
            api_invoker=self._api_invoker,
            options=self._server_options
        )
        self.server.initialize()

        self.soca_app_initialize()

    def soca_app_initialize(self):
        # to be overridden by child classes if required
        pass

    def app_start(self):
        self.soca_app_start()

        self.server.start()

    @abstractmethod
    def soca_app_start(self):
        ...

    def app_stop(self):
        if self.server is not None:
            self.logger.info('Stopping idea-server ...')
            self.server.stop()
            self.server = None

        self.soca_app_stop()

        leader_election_service = self.context.service_registry().get_service(constants.SERVICE_ID_LEADER_ELECTION)
        if leader_election_service is not None:
            leader_election_service.stop()

        distributed_lock_service = self.context.service_registry().get_service(constants.SERVICE_ID_DISTRIBUTED_LOCK)
        if distributed_lock_service is not None:
            distributed_lock_service.stop()

        metrics_service = self.context.service_registry().get_service(constants.SERVICE_ID_METRICS)
        if metrics_service is not None:
            metrics_service.stop()

        cluster_config = self.context.config()
        if isinstance(cluster_config, ClusterConfig):
            cluster_config.db.stop()

    @abstractmethod
    def soca_app_stop(self):
        ...
