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
from enum import Enum
from typing import List, Dict

from ideadatamodel import Scripts, Script, ScriptEvents
from ideasdk.utils import Utils


class ScriptOSType(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"


class ScriptEventType(str, Enum):
    ON_VDI_START = 'on_vdi_start'
    ON_VDI_CONFIGURED = 'on_vdi_configured'


class LaunchScriptsHelper:

    @staticmethod
    def is_https_url(url: str) -> bool:
        return Utils.is_url(url, 'https')

    @staticmethod
    def is_s3_url(url: str) -> bool:
        return Utils.is_url(url, 's3')

    @staticmethod
    def is_local_path(path: str) -> bool:
        return path.startswith('file://')

    @staticmethod
    def is_valid_script_location(script_location: str) -> bool:
        return LaunchScriptsHelper.is_s3_url(script_location) or LaunchScriptsHelper.is_local_path(script_location) or LaunchScriptsHelper.is_https_url(script_location)

    @staticmethod
    def validate_scripts(scripts: Scripts) -> bool:
        all_scripts = []
        for script_list in [scripts.linux, scripts.windows]:
            if script_list:
                all_scripts.extend(script_list.on_vdi_start or [])
                all_scripts.extend(script_list.on_vdi_configured or [])

        for script in all_scripts:
            if not LaunchScriptsHelper.is_valid_script_location(script.script_location):
                return False
        return True

    @staticmethod
    def get_supported_os_types() -> List[str]:
        return [ScriptOSType.WINDOWS, ScriptOSType.LINUX]

    @staticmethod
    def get_supported_script_events() -> List[str]:
        return [ScriptEventType.ON_VDI_START, ScriptEventType.ON_VDI_CONFIGURED]

    @staticmethod
    def convert_scripts_to_dict(scripts: Scripts) -> Dict:
        db_scripts = {}

        if scripts.linux:
            db_scripts[ScriptOSType.LINUX] = LaunchScriptsHelper.convert_script_events_to_dict(scripts.linux)
        if scripts.windows:
            db_scripts[ScriptOSType.WINDOWS] = LaunchScriptsHelper.convert_script_events_to_dict(scripts.windows)

        return db_scripts

    @staticmethod
    def convert_script_events_to_dict(script_events: ScriptEvents) -> Dict:
        script_event_dict = {}

        if script_events.on_vdi_start:
            script_event_dict[ScriptEventType.ON_VDI_START] = LaunchScriptsHelper.convert_scripts_to_list(script_events.on_vdi_start)
        if script_events.on_vdi_configured:
            script_event_dict[ScriptEventType.ON_VDI_CONFIGURED] = LaunchScriptsHelper.convert_scripts_to_list(script_events.on_vdi_configured)

        return script_event_dict

    @staticmethod
    def convert_scripts_to_list(scripts: List[Script]) -> List[Dict]:
        return [{'script_location': script.script_location, 'arguments': script.arguments} for script in scripts]
