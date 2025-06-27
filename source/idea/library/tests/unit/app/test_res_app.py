#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import threading
import time
from unittest.mock import Mock

from res.app.res_app import ResApp, SignalOrchestrator

APP_WARMUP_INVOKED = False
APP_INITIALIZE_INVOKED = False
APP_START_INVOKED = False
APP_STOP_INVOKED = False
MAX_WAIT_TIME_IN_SECONDS = 5


class TestApp(ResApp):
    """
    Virtual desktop app
    """

    def __init__(self):
        super().__init__("test", Mock())

    def app_warmup(self, delay, max_retries, error_wait_seconds):
        global APP_WARMUP_INVOKED
        APP_WARMUP_INVOKED = True

    def app_initialize(self):
        global APP_INITIALIZE_INVOKED
        APP_INITIALIZE_INVOKED = True

    def app_start(self):
        global APP_START_INVOKED
        APP_START_INVOKED = True

    def app_stop(self):
        global APP_STOP_INVOKED
        APP_STOP_INVOKED = True


def launch_app(app: TestApp):
    app.launch()


def test_res_app_lifecycle(monkeypatch) -> None:
    setup_termination = Mock()
    setup_reload = Mock()

    monkeypatch.setattr(SignalOrchestrator, "setup_termination", setup_termination)
    monkeypatch.setattr(SignalOrchestrator, "setup_reload", setup_reload)
    app = TestApp()

    app_thread = threading.Thread(target=launch_app, args=(app,), daemon=True)
    app_thread.start()

    start = time.time()
    while not app.is_running() and (time.time() - start < MAX_WAIT_TIME_IN_SECONDS):
        # Wait for the app to enter RUNNING state
        time.sleep(1)

    assert app.is_running()
    assert APP_WARMUP_INVOKED, "app_warmup is not invoked"
    assert APP_INITIALIZE_INVOKED, "app_initialize is not invoked"
    assert APP_START_INVOKED, "app_start is not invoked"
    assert not APP_STOP_INVOKED, "app_stop is invoked"
    setup_termination.assert_called_once()
    setup_reload.assert_called_once()

    app.stop()
    assert APP_STOP_INVOKED, "app_stop is not invoked"
