#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import signal
import sys
import time
from abc import ABC, abstractmethod
from logging import Logger
from threading import Event


class SignalOrchestrator:
    def __init__(self, app: "ResApp"):
        self.app = app

    @property
    def app_name(self):
        return self.app.app_name

    def termination_handler(self, signum, _):
        self.app.logger.info(
            f"Received termination signal: ({signal.Signals(signum).name})"
        )
        if not self.app.is_running():
            self.app.logger.warning(
                f"{self.app_name} termination is already in progress."
            )
            return
        self.app.on_terminate_signal()

    def reload_handler(self, signum, _):
        self.app.logger.info(f"Received reload signal: ({signal.Signals(signum).name})")
        if self.app.is_reload():
            self.app.logger.warning(f"{self.app_name} reload is already in progress.")
            return
        self.app.on_reload_signal()

    def setup_termination(self):
        termination_signals = [
            signal.SIGINT,
            signal.SIGTERM,
        ]
        if not os.getenv("RES_BASE_OS") == "windows":
            # SIGQUIT and SIGHUP signals are not supported on Windows
            # TODO: Implement a different mechanism for handling the shut down event on Windows
            termination_signals.append(signal.SIGQUIT)
            termination_signals.append(signal.SIGHUP)

        for termination_signal in termination_signals:
            signal.signal(termination_signal, self.termination_handler)

    def setup_reload(self):
        reload_signals = []
        if not os.getenv("RES_BASE_OS") == "windows":
            # SIGUSR1 signal is not supported on Windows
            reload_signals.append(signal.SIGUSR1)

        for reload_signal in reload_signals:
            signal.signal(reload_signal, self.reload_handler)


class ResApp(ABC):
    """
    RES Application Base Class

    Applications are expected to extend ResApp to initialize application specific context and functionality.
    """

    def __init__(self, module_id: str, logger: Logger):
        self._is_running = Event()
        self._is_reload = Event()

        self._module_id = module_id
        self.logger = logger

    @property
    def app_name(self):
        return self._module_id

    def is_running(self) -> bool:
        return self._is_running.is_set()

    def is_reload(self) -> bool:
        return self._is_reload.is_set()

    def on_terminate_signal(self):
        self.logger.warning(f"Initiating {self.app_name} shutdown ...")
        self._is_running.clear()

    def on_reload_signal(self):
        self.logger.warning(f"Initiating {self.app_name} reload ...")
        self._is_reload.set()

    def warm_up(self, delay=0.1, max_retries=3, error_wait_seconds=5):
        self.app_warmup(delay, max_retries, error_wait_seconds)

    def app_warmup(self, delay, max_retries, error_wait_seconds):
        # to be overridden by child classes if required
        pass

    def initialize(self):
        self.logger.info(f"Initializing {self.app_name}")

        # warm up dependencies
        self.warm_up()

        self.app_initialize()

    def app_initialize(self):
        # to be overridden by child classes if required
        pass

    def start(self):
        try:
            self.logger.info(f"Starting {self.app_name} ...")

            # app start
            self.app_start()

            self._is_running.set()

            self.logger.info(f"{self.app_name} started successfully.")

        except Exception as e:
            self._is_running.clear()
            raise e

    @abstractmethod
    def app_start(self): ...

    def stop(self):
        self.logger.info(f"Stopping {self.app_name} ...")

        self.app_stop()

        self.logger.info(f"{self.app_name} stopped successfully.")

    @abstractmethod
    def app_stop(self): ...

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
            self.logger.exception(f"failed to start app: {e}")
        finally:
            try:
                self.stop()
            except BaseException as e:
                self.logger.error(f"failed to stop app: {e}")

        exitcode = 0 if success else 1
        self.logger.info(f"exit code: {exitcode}")
        sys.exit(exitcode)
