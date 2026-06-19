#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess

import ideabootstrap.file_system.linux.constants as constants
def resume_logger():
    # Create systemd service
    service_name = f"resume_logger"
    service_file = os.path.join(
        constants.SYSTEMD_SERVICE_FILE_DIR, f"{service_name}.service"
    )

    service_content = f"""[Unit]
Description=Restart virtual-desktop-app after hibernate resume
After=hibernate.target

[Service]
Type=oneshot
ExecStartPre=/bin/sh -c 'echo "System resumed from hibernation" | systemd-cat -t resume-logger'
ExecStart=/bin/systemctl restart supervisord
RemainAfterExit=false

[Install]
WantedBy=hibernate.target
"""
    

    with open(service_file, "w") as f:
        f.write(service_content)

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", f"{service_name}.service"], check=True)
