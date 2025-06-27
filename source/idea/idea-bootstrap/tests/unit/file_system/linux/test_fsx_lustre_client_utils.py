#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import subprocess
import tempfile
from unittest.mock import Mock, call

from ideabootstrap import bootstrap_common
from ideabootstrap.file_system.linux import constants, fsx_lustre_client_utils


def test_tune_fsx_lustre_pre_reboot(monkeypatch):
    monkeypatch.setattr(fsx_lustre_client_utils, "_get_num_processors", lambda: 65)
    monkeypatch.setattr(fsx_lustre_client_utils, "_get_memory_gb", lambda: 65)
    monkeypatch.setenv("RES_BASE_OS", "amzn2")
    set_reboot_required = Mock()
    monkeypatch.setattr(bootstrap_common, "set_reboot_required", set_reboot_required)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "MODPROBE_CONFIG_PATH", temp_file_name)

        fsx_lustre_client_utils.tune_fsx_lustre_pre_reboot()

        with open(temp_file_name, "r") as f:
            lines = f.readlines()

            assert "options ptlrpc ptlrpcd_per_cpt_max=32\n" in lines
            assert "options ksocklnd credits=2560\n" in lines

        set_reboot_required.assert_called_once()


def test_tune_fsx_lustre_post_mount(monkeypatch):
    monkeypatch.setattr(fsx_lustre_client_utils, "_get_num_processors", lambda: 65)
    monkeypatch.setattr(fsx_lustre_client_utils, "_get_memory_gb", lambda: 65)
    monkeypatch.setattr(bootstrap_common, "set_reboot_required", lambda _: None)
    monkeypatch.setenv("RES_BASE_OS", "amzn2")
    run_mock = Mock()
    monkeypatch.setattr(subprocess, "run", run_mock)

    fsx_lustre_client_utils.tune_fsx_lustre_post_mount()
    run_mock.assert_has_calls(
        [
            call(["lctl", "set_param", "osc.*OST*.max_rpcs_in_flight=32"], check=True),
            call(["lctl", "set_param", "mdc.*.max_rpcs_in_flight=64"], check=True),
            call(["lctl", "set_param", "mdc.*.max_mod_rpcs_in_flight=50"], check=True),
            call(
                ["lctl", "set_param", "ldlm.namespaces.*.lru_max_age=600000"],
                check=True,
            ),
        ]
    )
