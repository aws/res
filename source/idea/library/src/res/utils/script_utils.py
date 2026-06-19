#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List

from res.resources.sessions import ScriptEventType, ScriptOSType


def _store_commands_as_linux_script(commands: List[str], script_name: str) -> List[str]:
    begin = "#!/bin/bash"
    script = "\n".join([begin] + commands)
    return [f'echo "{script}" > scripts/virtual-desktop-host/linux/{script_name}.sh']


def _store_commands_as_windows_script(
    commands: List[str], script_name: str
) -> List[str]:
    script = "`n".join(commands)
    return [f'"{script}" | Out-File -FilePath {script_name}.ps1']


def _retrieve_rerun_on_reboot(project, os_type: ScriptOSType) -> bool:
    scripts = project.get("scripts")
    if not scripts:
        return False

    script_type = None

    if os_type == ScriptOSType.LINUX:
        script_type = scripts.get("linux")
    elif os_type == ScriptOSType.WINDOWS:
        script_type = scripts.get("windows")

    if not script_type:
        return False

    return script_type.get("rerun_on_reboot", False)


def _retrieve_scripts_as_commands(
    project, os_type: ScriptOSType, script_event: ScriptEventType
) -> List[str]:
    scripts = project.get("scripts")
    if not scripts:
        return []

    script_type = None
    scripts_as_commands = []
    command_prefix = ""
    if os_type == ScriptOSType.LINUX:
        script_type = scripts.get("linux")
        boostrap_dir = "/root/bootstrap"
        command_prefix = f"/bin/bash {boostrap_dir}/latest/scripts/virtual-desktop-host/linux/download_and_execute_script.sh"
    elif os_type == ScriptOSType.WINDOWS:
        script_type = scripts.get("windows")
        command_prefix = "Download-And-Execute-Script -uri"
        boostrap_dir = "$env:SystemDrive\\Users\\Administrator\\RES\\Bootstrap"
        scripts_as_commands.append(
            f"Import-Module {boostrap_dir}\\scripts\\virtual-desktop-host\\windows\\DownloadAndExecuteScript.ps1 -force"
        )

    if not script_type:
        return []

    event_scripts = script_type.get(script_event.value)
    if not event_scripts:
        return []

    if os_type == ScriptOSType.LINUX:
        scripts_as_commands.extend(
            [
                f"{command_prefix} {script.get('script_location')} {' '.join(script.get('arguments', []))}"
                for script in event_scripts
            ]
        )
    elif os_type == ScriptOSType.WINDOWS:
        scripts_as_commands.extend(
            [
                f"{command_prefix} {script.get('script_location')} -arguments '{' '.join(script.get('arguments', []))}'"
                for script in event_scripts
            ]
        )

    return scripts_as_commands
