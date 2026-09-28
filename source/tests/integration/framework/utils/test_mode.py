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
from typing import Any, Dict, List, Optional

from res.utils import ssm_utils  # type: ignore[import]

logger = logging.getLogger(__name__)


class SetTestModeThread(threading.Thread):
    """
    Custom Thread Class for setting the test mode on a server instance
    """

    def __init__(self, instance_id: str, enable: bool):
        super().__init__()

        self._instance_id = instance_id
        self._enable = enable
        self._exc: Optional[BaseException] = None

    def _run_command(self, commands: List[str]) -> str:
        result = ssm_utils.send_command(
            instance_ids=[self._instance_id],
            commands=commands,
            base_os="linux",
            output_to_s3=False,
        )
        invocation = ssm_utils.wait_for_command(result["CommandId"], self._instance_id)
        return str(invocation.get("StandardOutputContent", ""))

    def set_test_mode(self) -> None:
        set_test_mode_commands = [
            "sudo sed -i '/^RES_TEST_MODE/d' /etc/environment && "
            f"echo 'RES_TEST_MODE={str(self._enable)}' | sudo tee -a /etc/environment && "
            "sudo service supervisord restart && "
            "sudo /opt/idea/python/latest/bin/supervisorctl start all"
        ]
        health_check_commands = ["curl https://localhost:8443/healthcheck -k"]

        self._run_command(set_test_mode_commands)

        start_time = time.process_time()
        while time.process_time() - start_time < 30:
            try:
                output = self._run_command(health_check_commands)
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
    server_instances: list[Dict[str, Any]],
    enable: bool,
) -> None:
    threads = [
        SetTestModeThread(instance.get("InstanceId", ""), enable)
        for instance in server_instances
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
