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

import logging
import threading
import time
from typing import Any, Dict, Optional

from tests.integration.framework.utils.remote_command_runner import RemoteCommandRunner

logger = logging.getLogger(__name__)


class SetTestModeThread(threading.Thread):
    """
    Custom Thread Class for setting the test mode on a server instance
    """

    def __init__(
        self, remote_command_runner: RemoteCommandRunner, instance_id: str, enable: bool
    ):
        super().__init__()

        self._remote_command_runner = remote_command_runner
        self._instance_id = instance_id
        self._enable = enable
        self._exc: Optional[BaseException] = None

    def set_test_mode(self) -> None:
        set_test_mode_commands = [
            "sudo sed -i '/^RES_TEST_MODE/d' /etc/environment && "
            f"echo 'RES_TEST_MODE={str(self._enable)}' | sudo tee -a /etc/environment && "
            "sudo service supervisord restart && "
            "sudo /opt/idea/python/3.9.16/bin/supervisorctl start all"
        ]
        health_check_commands = ["curl https://localhost:8443/healthcheck -k"]

        self._remote_command_runner.run(self._instance_id, set_test_mode_commands)

        start_time = time.process_time()
        while time.process_time() - start_time < 30:
            try:
                output = self._remote_command_runner.run(
                    self._instance_id, health_check_commands
                )
                assert output == '{"success":true}'
                logger.debug(
                    f"server is relaunched successfully. instance id: {self._instance_id}"
                )
                return
            except:
                logger.debug(
                    f"continue waiting for the server to respond. instance id: {self._instance_id}"
                )
                time.sleep(1)

        assert (
            False
        ), f"failed to relaunch server in 30 seconds. instance id: {self._instance_id}"

    def run(self) -> None:
        try:
            self.set_test_mode()
        except BaseException as e:
            self._exc = e

    def join(self, timeout: Optional[float] = None) -> None:
        threading.Thread.join(self, timeout)
        if self._exc:
            raise self._exc


def set_test_mode_for_all_servers(
    region: str,
    server_instances: list[Dict[str, Any]],
    enable: bool,
) -> None:
    remote_command_runner = RemoteCommandRunner(region)

    threads = [
        SetTestModeThread(remote_command_runner, instance.get("InstanceId", ""), enable)
        for instance in server_instances
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
