#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from ideabootstrap.ssh import disable_ssh, restrict_ssh, ssh_keygen
from ideabootstrap.sudo import set_sudoers, sudoer_secure_path
from res.utils import logging_utils
from ideabootstrap.common.constants import (
    SEMAPHORE_DIR,
    LINUX_VDI_CONFIG_FINISHED_LOCK,
    LINUX_VDI_CONFIG_HOST_READY_LOCK
)

from ideabootstrap import bootstrap_common
from ideabootstrap.common import (
    cognito_modules,
    amazon_ssm_agent,
    idea_proxy,
    network_interface_tags,
    ebs_volume_tags,
    chronyd,
    idea_service_account,
    cloudwatch_agent,
    motd,
    hibernation,
    constants as bootstrap_constants,
)
from ideabootstrap.file_system import shared_storage
from ideabootstrap.directory_service import active_directory

from ideabootstrap.dcv import dcv

import os
import subprocess
import time
from ideavirtualdesktop.app.utils import send_sqs_host_messages
from ideavirtualdesktop.app.linux import post_reboot

logger = logging_utils.get_logger("boostrap")

def run():
    if not os.path.isfile(LINUX_VDI_CONFIG_FINISHED_LOCK):
        logger.info("Starting Linux Configuration")

        bootstrap_common.set_reboot_required("no")

        amazon_ssm_agent.configure()
        cloudwatch_agent.setup()

        idea_proxy.set_proxy()
        idea_service_account.setup_account()

        shared_storage.configure()

        path = "/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin"
        restrict_ssh.configure(session_owner=True)
        disable_ssh.configure()
        sudoer_secure_path.configure(path)

        ebs_volume_tags.setup()
        network_interface_tags.setup()

        chronyd.configure()
        bootstrap_common.disable_ulimit()
        bootstrap_common.disable_strict_host_check()
        bootstrap_common.disable_se_linux()
        motd.disable_update()

        messages = [f'{os.environ.get("IDEA_MODULE_NAME", "")} (v{os.environ.get("IDEA_MODULE_VERSION", "")}), Cluster: {os.environ.get("IDEA_CLUSTER_NAME", "")}']
        motd.update(messages)

        active_directory.configure()

        cognito_modules.configure()
        set_sudoers.configure()
        ssh_keygen.configure()
        hibernation.resume_logger()

        if os.environ.get("IDEA_SESSION_ID", "NONE") != "NONE":
            dcv.configure()

        customization_script = f"{os.environ.get('IDEA_CLUSTER_HOME', '')}/dcv_host/userdata_customizations.sh"
        if os.path.isfile(customization_script):
            log_file = f"{os.environ.get('IDEA_CLUSTER_HOME', '')}/logs/userdata_customizations.log"
            with open(log_file, 'a') as log:
                subprocess.run(
                    ["/bin/bash", customization_script],
                    stdout=log,
                    stderr=subprocess.STDOUT
                )

        bootstrap_common.source_launch_env_file('/etc/launch_script_environment')
        on_vdi_configured()

        send_sqs_host_messages("DCV_HOST_READY_EVENT")

        logger.info(f"Created semaphore directory: {SEMAPHORE_DIR}")
        os.makedirs(SEMAPHORE_DIR, exist_ok=True)
        with open(LINUX_VDI_CONFIG_FINISHED_LOCK, 'w') as f:
            f.write(str(int(time.time())))

        bootstrap_common.check_reboot_required()
    else:
        logger.info(f"Configuration LINUX_VDI_CONFIG_FINISHED_LOCK file: {LINUX_VDI_CONFIG_FINISHED_LOCK} already exists")

        bootstrap_common.source_launch_env_file('/etc/launch_script_environment')
        if os.environ.get('RERUN_ON_REBOOT') == "True" and os.path.isfile(LINUX_VDI_CONFIG_HOST_READY_LOCK):
            on_vdi_configured()
        else:
            logger.info("Skipping running ON_VDI_CONFIGURED_COMMANDS")

        post_reboot.run()


def on_vdi_configured():
    script_dir = os.path.join(bootstrap_constants.BOOTSTRAP_DIR, "latest", "scripts", "virtual-desktop-host", "linux")
    on_vdi_configured_script = os.path.join(script_dir, os.environ.get("ON_VDI_CONFIGURED_COMMANDS", ""))

    if os.path.isfile(on_vdi_configured_script):
        try:
            output = subprocess.run(["/bin/bash", on_vdi_configured_script], check=True, capture_output=True, text=True)
            logger.info(output.stdout)
        except Exception as e:
            logger.error(f"Error running script {on_vdi_configured_script}: {e}")
    else:
        logger.info(f"Script not found: {on_vdi_configured_script}")
