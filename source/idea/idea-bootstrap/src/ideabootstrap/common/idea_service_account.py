#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.utils import logging_utils
import subprocess

logger = logging_utils.get_logger("bootstrap")

def setup_account():
    logger.info("Checking for ideaserviceaccount exists")
    try:
        subprocess.run(["id", "ideaserviceaccount"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("ideaserviceaccount already exists in system")
    except subprocess.CalledProcessError:
        logger.info("Creating ideaserviceaccount system user")
        try:
            subprocess.run(
                ["useradd", "--system", "--shell", "/bin/false", "ideaserviceaccount"],
                check=True
            )
            logger.info("Successfully created ideaserviceaccount")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create ideaserviceaccount: {e}")
