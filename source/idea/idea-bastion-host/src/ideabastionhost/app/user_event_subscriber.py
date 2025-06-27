#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from logging import Logger
from typing import Dict, List, Optional

import res.constants as constants
from res.resources.dynamodb.dynamodb_stream_subscriber import IDynamoDBStreamSubscriber
from res.utils import logging_utils

SSHD_CONFIG_FILE = "/etc/ssh/sshd_config"

logger = logging_utils.get_logger(constants.MODULE_ID_BASTION_HOST)


class UserEventSubscriber(IDynamoDBStreamSubscriber):
    def __init__(
        self,
        logger_: Logger = None,
        module_id: str = None,
    ) -> None:
        self.logger = logger_ if logger_ else logger
        self.module_id = module_id
        self.sssd_settings = None

    def on_create(self, entry: Dict):
        pass

    def on_update(self, old_entry: Dict, new_entry: Dict):
        old_enabled_state = old_entry.get("enabled")
        new_enabled_state = new_entry.get("enabled")
        if old_enabled_state and not new_enabled_state:
            # User was disabled
            self.deny_ssh_access([new_entry.get("username")])
        elif new_enabled_state and not old_enabled_state:
            # User was enabled
            self._allow_ssh_access([new_entry.get("username")])

    def on_delete(self, entry: Dict):
        self.deny_ssh_access([entry.get("username")])

    def is_entry_monitored(self, entry: Dict) -> bool:
        return True

    @property
    def subscriber_name(self) -> Optional[str]:
        return "user_event"

    def deny_ssh_access(self, usernames: List[str]):
        if not usernames:
            return

        try:
            logger.info(f"Denying SSH access for users {usernames}")

            config_lines = self.get_sshd_configs()
            modified = False
            deny_users_exists = False
            for i, line in enumerate(config_lines):
                if line.strip().startswith("DenyUsers"):
                    # Add user to DenyUsers
                    deny_users_exists = True
                    denied_users = line.strip().split()[1:]

                    for username in usernames:
                        if username in denied_users:
                            logger.info(
                                f"No changes needed - user {username} has already been denied"
                            )
                        else:
                            denied_users.append(username)
                            modified = True

                    config_lines[i] = f"DenyUsers {' '.join(denied_users)}\n"
                    break

            # If no DenyUsers line exists, add new one
            if not deny_users_exists:
                config_lines.append(f"DenyUsers {' '.join(usernames)}\n")
                modified = True

            if modified:
                with open(SSHD_CONFIG_FILE, "w") as file:
                    file.writelines(config_lines)

                subprocess.run(["systemctl", "restart", "sshd"], check=True)
                logger.info(f"Successfully denied SSH access for users: {usernames}")

        except Exception as e:
            logger.error(f"Failed to deny SSH access for users {usernames}: {e}")

    def _allow_ssh_access(self, usernames: List[str]):
        if not usernames:
            return

        try:
            logger.info(f"Enabling SSH access for users {usernames}")

            config_lines = self.get_sshd_configs()
            modified = False
            deny_users_index = -1
            for i, line in enumerate(config_lines):
                if line.strip().startswith("DenyUsers"):
                    # Remove user from DenyUsers if present
                    denied_users = line.strip().split()[1:]

                    for username in usernames:
                        if username in denied_users:
                            denied_users.remove(username)
                            modified = True
                        else:
                            logger.info(
                                f"No changes needed - user {username} already has proper SSH access"
                            )

                    if denied_users:
                        config_lines[i] = f"DenyUsers {' '.join(denied_users)}\n"
                    else:
                        deny_users_index = i
                    break

            # Remove the DenyUsers line if the user list is empty
            if deny_users_index >= 0:
                config_lines.pop(deny_users_index)

            if modified:
                with open(SSHD_CONFIG_FILE, "w") as file:
                    file.writelines(config_lines)

                subprocess.run(["systemctl", "restart", "sshd"], check=True)
                logger.info(f"Successfully allowed SSH access for users: {usernames}")

        except Exception as e:
            logger.error(f"Failed to allow SSH access for user {usernames}: {e}")

    @staticmethod
    def get_sshd_configs() -> List[str]:
        if not os.path.exists(SSHD_CONFIG_FILE):
            raise FileNotFoundError(f"SSHD config file not found at {SSHD_CONFIG_FILE}")

        with open(SSHD_CONFIG_FILE, "r") as file:
            config_lines = file.readlines()

        return config_lines
