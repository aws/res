#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

import ideabootstrap.sudo.constants as constants
from ideabootstrap.bootstrap_common import overwrite_file, get_base_os
from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")

def configure(path: str = None) -> None:
    """
    Configure sudoers secure path
    """
    base_os = get_base_os()
    
    if not path:
        path = constants.PATH
    
    try:
        if base_os in ("amzn2", "amzn2023", "rhel8", "rhel9", "rocky9"):
            logger.info(f"Base OS Supported: {base_os}")
            content = f'Defaults secure_path="{path}"'
            
            overwrite_file(
                content,
                constants.SUDOER_SECURE_PATH_FILE,
            )
        else:
            logger.info(f"Base OS Unsupported: {base_os}")
        logger.info(f"Update sudoer secure path successfully. Base OS: {base_os}")
    except Exception as e:
        logger.error(f"Failed to setup sudoers: {str(e)}")
