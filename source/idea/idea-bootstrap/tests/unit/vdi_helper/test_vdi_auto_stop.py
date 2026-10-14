#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest.mock import Mock

import pytest

# vdi-helper is not an importable package (hyphenated dir), so import the script directly
vdi_helper_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../resources/scripts/vdi-helper",
    )
)
sys.path.insert(0, vdi_helper_path)

import vdi_auto_stop


@pytest.mark.parametrize("os_name", ["posix", "nt"])
def test_get_cpu_utilization_uses_blocking_interval(monkeypatch, os_name):
    # Without an interval, psutil measures since import: a cron process's own startup.
    cpu_percent = Mock(return_value=0.0)
    monkeypatch.setattr(vdi_auto_stop.psutil, "cpu_percent", cpu_percent)
    monkeypatch.setattr(vdi_auto_stop.os, "name", os_name)

    vdi_auto_stop._get_cpu_utilization()

    _, kwargs = cpu_percent.call_args
    assert kwargs.get("interval", 0) > 0


def test_is_not_idle_when_cpu_above_threshold(monkeypatch):
    monkeypatch.setattr(vdi_auto_stop.psutil, "cpu_percent", Mock(return_value=90.0))
    monkeypatch.setattr(vdi_auto_stop, "_get_dcv_latest_interaction_time", lambda: 0)

    assert vdi_auto_stop._is_idle(cpu_threshold=30) is False
