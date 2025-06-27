#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import os
import random
import time

from res.resources import ad_automation, cluster_settings
from res.utils import logging_utils, sssd_utils

BASE_OS = os.getenv("RES_BASE_OS")
if BASE_OS == "windows":
    from ideabootstrap.directory_service.windows import active_directory as active_directory_platform
else:
    from ideabootstrap.directory_service.linux import active_directory as active_directory_platform

MAX_AD_JOIN_ATTEMPTS = 180

logger = logging_utils.get_logger("bootstrap")


def configure(force_join=True):
    if not cluster_settings.get_setting(sssd_utils.DOMAIN_NAME_KEY):
        logger.info("AD configuration has not been provided. Skipping.")
        return

    if cluster_settings.get_setting(sssd_utils.DISABLE_AD_JOIN_KEY) == "true":
        active_directory_platform.configure_sssd(logger)
        return

    if not force_join and active_directory_platform.is_in_active_directory(logger):
        logger.info("VDI has already joined AD. Skipping.")
        return

    if not ad_automation.request_ad_authorization():
        logger.error("Failed to request AD authorization")
        return

    attempt_count = 0

    while attempt_count <= MAX_AD_JOIN_ATTEMPTS:
        auth_entry = ad_automation.get_authorization()
        if auth_entry:
            if auth_entry["status"] == "success":
                active_directory_platform.join_active_directory(auth_entry, logger)

                return
            else:
                logger.error(
                    f"Authorization failed: ({auth_entry['error_code']}) {auth_entry['message']}"
                )

                return

        sleep_time = random.randint(8, 40)
        logger.info(
            f"({attempt_count} of {MAX_AD_JOIN_ATTEMPTS}) waiting for AD authorization, retrying in {sleep_time} seconds ..."
        )
        time.sleep(sleep_time)
        attempt_count += 1
