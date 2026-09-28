#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.resources.sessions import ScriptEventType, ScriptOSType
from res.utils import script_utils


def test_store_commands_as_linux_script():
    """Test _store_commands_as_linux_script creates proper bash script."""
    commands = ["echo 'Hello'", "ls -la"]
    result = script_utils._store_commands_as_linux_script(commands, "test_script")

    assert len(result) == 1
    assert "#!/bin/bash" in result[0]
    assert "echo 'Hello'" in result[0]
    assert "scripts/virtual-desktop-host/linux/test_script.sh" in result[0]


def test_store_commands_as_windows_script():
    """Test _store_commands_as_windows_script creates proper PowerShell script."""
    commands = ["Write-Host 'Hello'", "Get-ChildItem"]
    result = script_utils._store_commands_as_windows_script(commands, "test_script")

    assert len(result) == 1
    assert "Write-Host 'Hello'" in result[0]
    assert "test_script.ps1" in result[0]


def test_retrieve_rerun_on_reboot_linux_true():
    """Test _retrieve_rerun_on_reboot returns True for Linux when set."""
    project = {"scripts": {"linux": {"rerun_on_reboot": True}}}
    result = script_utils._retrieve_rerun_on_reboot(project, ScriptOSType.LINUX)
    assert result is True


def test_retrieve_rerun_on_reboot_no_scripts():
    """Test _retrieve_rerun_on_reboot returns False when no scripts."""
    project = {}
    result = script_utils._retrieve_rerun_on_reboot(project, ScriptOSType.LINUX)
    assert result is False


def test_retrieve_scripts_as_commands_linux():
    """Test _retrieve_scripts_as_commands for Linux."""
    project = {
        "scripts": {
            "linux": {
                "on_vdi_start": [
                    {
                        "script_location": "s3://bucket/script.sh",
                        "arguments": ["arg1", "arg2"],
                    }
                ]
            }
        }
    }
    result = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.LINUX, ScriptEventType.ON_VDI_START
    )

    assert len(result) == 1
    assert "s3://bucket/script.sh" in result[0]
    assert "arg1 arg2" in result[0]


def test_retrieve_scripts_as_commands_windows():
    """Test _retrieve_scripts_as_commands for Windows."""
    project = {
        "scripts": {
            "windows": {
                "on_vdi_start": [
                    {"script_location": "s3://bucket/script.ps1", "arguments": ["arg1"]}
                ]
            }
        }
    }
    result = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_START
    )

    assert len(result) == 2  # Import + script execution
    assert "Import-Module" in result[0]
    assert "s3://bucket/script.ps1" in result[1]


def test_escape_powershell_single_quoted_no_special_chars():
    """Test _escape_powershell_single_quoted with no special characters."""
    assert script_utils._escape_powershell_single_quoted("hello") == "hello"


def test_escape_powershell_single_quoted_with_single_quotes():
    """Test _escape_powershell_single_quoted doubles single quotes."""
    assert script_utils._escape_powershell_single_quoted("it's") == "it''s"
    assert script_utils._escape_powershell_single_quoted("a'b'c") == "a''b''c"


def test_escape_powershell_single_quoted_empty_string():
    """Test _escape_powershell_single_quoted with empty string."""
    assert script_utils._escape_powershell_single_quoted("") == ""


def test_retrieve_scripts_as_commands_windows_escapes_single_quotes_in_location():
    """Test that script_location with single quotes is escaped for Windows."""
    project = {
        "scripts": {
            "windows": {
                "on_vdi_start": [
                    {
                        "script_location": "s3://bucket/it's a script.ps1",
                        "arguments": [],
                    }
                ]
            }
        }
    }
    result = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_START
    )

    # The single quote in the location should be doubled
    assert "it''s a script.ps1" in result[1]
    # Should NOT contain the unescaped single quote that could break out
    assert "it's a script.ps1" not in result[1]


def test_retrieve_scripts_as_commands_windows_escapes_single_quotes_in_arguments():
    """Test that arguments with single quotes are escaped for Windows."""
    project = {
        "scripts": {
            "windows": {
                "on_vdi_start": [
                    {
                        "script_location": "s3://bucket/script.ps1",
                        "arguments": ["--name=it's", "val'ue"],
                    }
                ]
            }
        }
    }
    result = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_START
    )

    # Arguments with single quotes should be doubled
    assert "--name=it''s" in result[1]
    assert "val''ue" in result[1]


def test_retrieve_scripts_as_commands_windows_injection_prevention():
    """Test that a malicious argument cannot break out of single quotes."""
    project = {
        "scripts": {
            "windows": {
                "on_vdi_start": [
                    {
                        "script_location": "s3://bucket/script.ps1",
                        "arguments": ["'; Invoke-Evil; '"],
                    }
                ]
            }
        }
    }
    result = script_utils._retrieve_scripts_as_commands(
        project, ScriptOSType.WINDOWS, ScriptEventType.ON_VDI_START
    )

    # The injected single quotes should be escaped (doubled)
    assert "''; Invoke-Evil; ''" in result[1]
