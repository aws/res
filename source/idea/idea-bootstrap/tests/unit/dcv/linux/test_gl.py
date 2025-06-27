#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile
from unittest.mock import Mock, call
import pytest
from ideabootstrap.dcv import constants
from ideabootstrap.dcv.linux import gl


@pytest.mark.parametrize(
    "instance_family, expected_result",
    [
        ("g4dn", True),
        ("t3", False),
    ],
)
def test_is_gpu_instance_type(monkeypatch, instance_family, expected_result) -> None:
    monkeypatch.setenv("INSTANCE_FAMILY", instance_family)
    monkeypatch.setattr(
        "res.resources.cluster_settings.get_setting", lambda x: ["g4dn", "p3"]
    )

    assert gl._is_gpu_instance_type() == expected_result


@pytest.mark.parametrize(
    "base_os, machine",
    [
        ("amzn2", "x86_64"),
        ("rhel8", "aarch64"),
        ("rhel9", "x86_64"),
        ("rocky9", "x86_64"),
        ("ubuntu2204", "x86_64"),
    ],
)
def test_configure_gl(monkeypatch, base_os, machine) -> None:
    monkeypatch.setenv("MACHINE", machine)
    mock_run = Mock()
    mock_configure_rc = Mock()

    monkeypatch.setattr("os.makedirs", Mock())
    monkeypatch.setattr("ideabootstrap.dcv.linux.gl.which", lambda x: "dcvgladmin")
    monkeypatch.setattr(gl, "_configure_rc_service", mock_configure_rc)
    monkeypatch.setattr("subprocess.run", mock_run)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        temp_file_initial_content = "test\n"
        temp_file.write(temp_file_initial_content)
        temp_file.flush()
        monkeypatch.setattr(constants, "RC_LOCAL_DEBIAN_PATH", temp_file_name)
        monkeypatch.setattr(constants, "RC_LOCAL_RHEL_PATH", temp_file_name)

        gl._configure_gl(base_os)
        with open(temp_file_name, "r") as f:
            content = f.read()
            if machine != "x86_64" or base_os == "amzn2":
                assert "dcvgladmin" not in content
                assert mock_run.call_args_list == []
            else:
                assert "dcvgladmin" in content
                if base_os == "ubuntu2204":
                    assert "test" not in content
                    mock_configure_rc.assert_called_once_with(temp_file_name)
                    assert mock_run.call_args_list == []
                else:
                    assert "test" in content
                    mock_configure_rc.call_count == 0
                    assert mock_run.call_args_list == [
                        call(["systemctl", "enable", "rc-local"], check=True)
                    ]


def test_configure_rc_service(monkeypatch) -> None:
    mock_run = Mock()
    monkeypatch.setattr("os.chmod", Mock())
    monkeypatch.setattr("subprocess.run", mock_run)

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(constants, "RC_LOCAL_SERVICE_PATH", temp_file_name)

        gl._configure_rc_service(temp_file_name)
        with open(temp_file_name, "r") as f:
            content = f.read()

    assert f"{temp_file_name} start" in content
    assert mock_run.call_args_list == [
        call(["systemctl", "enable", "rc-local.service"], check=True)
    ]


@pytest.mark.parametrize(
    "base_os, is_gpu_instance",
    [
        ("amzn2", True),
        ("rhel8", False),
        ("rhel9", True),
        ("rocky9", True),
        ("invalid_os", True),
    ],
)
def test_configure_all(monkeypatch, base_os, is_gpu_instance) -> None:
    monkeypatch.setenv("RES_BASE_OS", base_os)
    mock_is_gpu_instance = Mock(return_value=is_gpu_instance)
    mock_configure_gl = Mock()
    monkeypatch.setattr(gl, "_is_gpu_instance_type", mock_is_gpu_instance)
    monkeypatch.setattr(gl, "_configure_gl", mock_configure_gl)

    gl.configure()

    if base_os == "invalid_os":
        mock_is_gpu_instance.assert_not_called()
        mock_configure_gl.assert_not_called()
    elif not is_gpu_instance:
        mock_is_gpu_instance.assert_called_once()
        mock_configure_gl.assert_not_called()
    else:
        mock_is_gpu_instance.assert_called_once()
        mock_configure_gl.assert_called_once_with(base_os)
