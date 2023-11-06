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

from abc import abstractmethod
import sys
import time
import signal
from typing import Optional
from threading import Event


class SignalOrchestrator:
    def __init__(self, app: 'SocaApp'):
        self.app = app

    @property
    def app_name(self):
        return self.app.app_name

    def termination_handler(self, signum, _):
        self.app.logger.info(f'Received termination signal: ({signal.Signals(signum).name})')
        if not self.app.is_running():
            self.app.logger.warning(f'{self.app_name} termination is already in progress.')
            return
        self.app.on_terminate_signal()

    def reload_handler(self, signum, _):
        self.app.logger.info(f'Received reload signal: ({signal.Signals(signum).name})')
        if self.app.is_reload():
            self.app.logger.warning(f'{self.app_name} reload is already in progress.')
            return
        self.app.on_reload_signal()

    def setup_termination(self):
        termination_signals = [
            signal.SIGINT,
            signal.SIGTERM,
            signal.SIGQUIT,
            signal.SIGHUP
        ]
        for termination_signal in termination_signals:
            signal.signal(termination_signal, self.termination_handler)

    def setup_reload(self):
        reload_signals = [
            signal.SIGUSR1
        ]

        for reload_signal in reload_signals:
            signal.signal(reload_signal, self.reload_handler)


class SocaApp(SocaBaseProtocol):
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

    @property
    def app_name(self):
        return self.context.module_id()

    def is_running(self) -> bool:
        return self._is_running.is_set()

    def is_reload(self) -> bool:
        return self._is_reload.is_set()

    def on_terminate_signal(self):
        self.logger.warning(f'Initiating {self.app_name} shutdown ...')
        self._is_running.clear()

    def on_reload_signal(self):
        self.logger.warning(f'Initiating {self.app_name} reload ...')
        self._is_reload.set()

    def warm_up(self, delay=0.1, max_retries=3, error_wait_seconds=5):

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
                    self.app_warmup()

                success = True
            except Exception as e:
                self.logger.error(f'warm-up failed: {e}. Retrying in ({error_wait_seconds}) seconds ...')
                time.sleep(error_wait_seconds)

        if not success:
            raise exceptions.SocaException(
                error_code=errorcodes.GENERAL_ERROR,
                message=f'Failed to warm-up dependencies after ({max_retries}) retries. Exit.'
            )

    def app_warmup(self):
        # to be overridden by child classes if required
        pass

    def initialize(self):
        self.logger.info(f'Initializing {self.app_name} with configuration: {os.linesep}{self.context.config().as_yaml()}')

        # warm up dependencies
        self.warm_up()

        self.server = SocaServer(
            context=self.context,
            api_invoker=self._api_invoker,
            options=self._server_options
        )
        self.server.initialize()

        self.app_initialize()

    def app_initialize(self):
        # to be overridden by child classes if required
        pass

    def start(self):

        try:
            self.logger.info(f'Starting {self.app_name} ...')

            # app start
            self.app_start()

            self.server.start()

            self._is_running.set()

            self.logger.info(f'{self.app_name} started successfully.')

        except Exception as e:
            self._is_running.clear()
            raise e

    @abstractmethod
    def app_start(self):
        ...

    def stop(self):

        try:

            self.logger.info(f'Stopping {self.app_name} ...')

            if self.server is not None:
                self.logger.info('Stopping idea-server ...')
                self.server.stop()
                self.server = None

            self.app_stop()

            analytics_service = self.context.service_registry().get_service(constants.SERVICE_ID_ANALYTICS)
            if analytics_service is not None:
                analytics_service.stop()

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

            self.logger.info(f'{self.app_name} stopped successfully.')

        except Exception as e:
            raise e

    @abstractmethod
    def app_stop(self):
        ...

    def launch(self):

        success = False

        try:

            self.initialize()

            signal_orchestrator = SignalOrchestrator(app=self)
            signal_orchestrator.setup_termination()
            signal_orchestrator.setup_reload()

            self.start()

            while self.is_running():
                time.sleep(1)

            success = True
        except BaseException as e:
            self.logger.exception(f'failed to start app: {e}')
        finally:
            try:
                self.stop()
            except BaseException as e:
                self.logger.error(f'failed to stop app: {e}')

        exitcode = 0 if success else 1
        self.logger.info(f'exit code: {exitcode}')
        sys.exit(exitcode)
