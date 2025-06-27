#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock, call
from ideabootstrap.dcv import constants
from ideabootstrap.dcv.windows import start_dcv_service


def test_configure(monkeypatch) -> None:
    mock_rmtree = Mock()
    mock_run = Mock()
    expected_calls = [
        call(
            ["powershell.exe", "-Command", "Start-Service -Name dcvserver"], check=True
        ),
        call(
            [
                "powershell.exe",
                "-Command",
                "Start-Service -Name DcvSessionManagerAgentService",
            ],
            check=True,
        ),
    ]

    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("shutil.rmtree", mock_rmtree)
    monkeypatch.setattr("subprocess.run", mock_run)

    start_dcv_service.configure()

    mock_rmtree.assert_called_once_with(constants.WINDOWS_DCV_CERT_DIR)
    mock_run.call_args_list == expected_calls


def test_configure_no_cert_dir(monkeypatch) -> None:
    mock_rmtree = Mock()
    mock_run = Mock()

    monkeypatch.setattr("os.path.exists", lambda x: False)
    monkeypatch.setattr("shutil.rmtree", mock_rmtree)
    monkeypatch.setattr("subprocess.run", mock_run)

    start_dcv_service.configure()

    mock_rmtree.call_count == 0
    mock_run.call_count == 2
