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


from res.resources import cluster_settings

from ideabootstrap.common.constants import (
    WINDOWS_VDI_CONFIG_FINISHED_LOCK,
    WINDOWS_BOOTSTRAP_DIR,
)
from ideabootstrap.common import (
    cloudwatch_agent
)
from ideabootstrap.dcv import dcv
from ideabootstrap.file_system import shared_storage
from ideabootstrap.directory_service import active_directory
from ideavirtualdesktop.app.utils import send_sqs_host_messages
from ideavirtualdesktop.app.windows import post_reboot
from res.utils import logging_utils

import os
import subprocess
import time

logger = logging_utils.get_logger("boostrap")

def run():
    if not os.path.isfile(WINDOWS_VDI_CONFIG_FINISHED_LOCK):
        IDEA_WEB_PORTAL_URL = cluster_settings.get_setting('cluster.load_balancers.external_alb.load_balancer_arn')

        cloudwatch_agent.setup()

        desktop_hostname = os.environ.get("COMPUTERNAME")  # Current hostname

        if os.environ.get("COMPUTERNAME") != desktop_hostname:
            logger.info(f"Hostname detected {os.environ.get('COMPUTERNAME')}. Renaming Computer to {desktop_hostname}...")
            subprocess.run(["powershell", "-Command", f"Rename-Computer -NewName {desktop_hostname} -Force"], check=True)
            logger.info("Name has been changed, re-enabling user data as we are about to restart the system...")
            subprocess.run(["powershell", "-Command", "C:\\ProgramData\\Amazon\\EC2-Windows\\Launch\\Scripts\\InitializeInstance.ps1 -Schedule"], check=True)
            logger.info("Restarting Computer...")
            subprocess.run(['powershell', '-Command', 'Restart-Computer -Force'], check=True)

        active_directory.configure()

        subprocess.run(
        ['powershell',
        '-Command',
        'Set-ItemProperty "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "ConsentPromptBehaviorAdmin" -Value 00000000 -Force'
        ],
        check=True)

        admin_key = "HKLM:\\SOFTWARE\\Microsoft\\Active Setup\\Installed Components\\{A509B1A7-37EF-4b3f-8CFC-4F3A74704073}"
        user_key = "HKLM:\\SOFTWARE\\Microsoft\\Active Setup\\Installed Components\\{A509B1A8-37EF-4b3f-8CFC-4F3A74704073}"

        for key in [admin_key, user_key]:
            subprocess.run([
                'powershell',
                '-Command',
                f'if (-not (Test-Path "{key}")) {{ New-Item -Path "{key}" -Force | Out-Null }}'
            ], check=True)
            
            subprocess.run([
                'powershell',
                '-Command',
                f'Set-ItemProperty -Path "{key}" -Name "IsInstalled" -Value 0 -Force'
            ], check=True)

        logger.info("Create Shortcut to RES web interface")
        default_desktop_dir = "C:\\Users\\Default\\Desktop"
        os.makedirs(default_desktop_dir, exist_ok=True)

        shared_storage.configure()

        if os.environ.get("IDEA_SESSION_ID", "NONE") != "NONE":
            dcv.configure()

        os.makedirs("C:\\RES", exist_ok=True)

        on_vdi_configured()

        semaphore_dir = "C:\\IDEA\\Semaphore"
        os.makedirs(semaphore_dir, exist_ok=True)
        logger.info(f"Created semaphore directory: {semaphore_dir}")

        current_time = str(int(time.time()))

        with open(WINDOWS_VDI_CONFIG_FINISHED_LOCK, 'w') as f:
            f.write(current_time)

        logger.info(f"Configure File Written: {WINDOWS_VDI_CONFIG_FINISHED_LOCK}")

        register_hibernate_resume_task()

        logger.info("Finished Bootstrap Configuration")
        subprocess.run(["powershell", "-Command", "Restart-Computer -Force"], capture_output=True)
    else:
        logger.info(f"Configuration WINDOWS_VDI_CONFIG_FINISHED_LOCK file: {WINDOWS_VDI_CONFIG_FINISHED_LOCK} already exists")

        post_reboot.run()

def register_hibernate_resume_task():
    """Register a scheduled task to restart the VDI app on hibernate resume."""
    script_path = os.path.join(WINDOWS_BOOTSTRAP_DIR, "scripts", "virtual-desktop-host", "windows", "RegisterHibernateResume.ps1")
    subprocess.run(["powershell", "-File", script_path], check=True)

def on_vdi_configured():
    script_dir = os.path.join(WINDOWS_BOOTSTRAP_DIR, "scripts", "virtual-desktop-host", "windows")
    on_vdi_configured_script = os.path.join(script_dir, os.environ.get("ON_VDI_CONFIGURED_COMMANDS", ""))

    if os.path.isfile(on_vdi_configured_script):
        try:
            output = subprocess.run([
                "powershell",
                "-Command",
                f"& {on_vdi_configured_script}",
            ], check=True, capture_output=True, text=True)
            logger.info(output.stdout)
        except Exception as e:
            logger.error(f"Error running script {on_vdi_configured_script}: {e}")
    else:
        logger.info(f"Script not found: {on_vdi_configured_script}")
