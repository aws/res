#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import shutil
from ideabootstrap.bootstrap_common import get_base_os
from res.utils import logging_utils
import os
import subprocess

logger = logging_utils.get_logger("bootstrap")

chrony_conf = """
# use the local instance NTP service, if available
server 169.254.169.123 prefer iburst minpoll 4 maxpoll 4

# Use public servers from the pool.ntp.org project.
# Please consider joining the pool (http://www.pool.ntp.org/join.html).
# !!! [BEGIN] IDEA REQUIREMENT
# You will need to open UDP egress traffic on your security group if you want to enable public pool
#pool 2.amazon.pool.ntp.org iburst
# !!! [END] IDEA REQUIREMENT
# Record the rate at which the system clock gains/losses time.
driftfile /var/lib/chrony/drift

# Allow the system clock to be stepped in the first three updates
# if its offset is larger than 1 second.
makestep 1.0 3

# Specify file containing keys for NTP authentication.
keyfile /etc/chrony.keys

# Specify directory for log files.
logdir /var/log/chrony

# save data between restarts for fast re-load
dumponexit
dumpdir /var/run/chrony
"""

def configure():
    base_os = get_base_os()
    try:
        if base_os in ["amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"]:
            logger.info(f"Configuring chronyd for {base_os}")

            subprocess.run(['yum', 'remove', '-y', 'ntp'], check=True)
            logger.info("Removed ntp package")

            # Back up original chrony.conf
            if os.path.exists('/etc/chrony.conf'):
                shutil.move('/etc/chrony.conf', '/etc/chrony.conf.original')
                logger.info("Backed up original chrony.conf")

            with open('/etc/chrony.conf', 'w') as f:
                f.write(chrony_conf)

            logger.info("Created new chrony.conf")

            # Enable chronyd service
            subprocess.run(['systemctl', 'enable', 'chronyd'], check=True)
            logger.info("Chronyd configuration completed successfully")
        else:
            logger.error(f"Error on chronyd configuration: Unsupported OS '{base_os}'")
    except Exception as e:
        logger.error(f"Error configuring chronyd: {str(e)}")


