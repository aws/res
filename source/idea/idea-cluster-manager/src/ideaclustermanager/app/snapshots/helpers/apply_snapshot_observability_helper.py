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
from logging import Logger
from typing import Optional


class ApplyResourceStatus(Enum):
    APPLIED = "applied",
    APPLIED_SOFT_DEP = "applied_soft_dep"
    SKIPPED_SOFT_DEP = "skipped_soft_dep"
    SKIPPED = "skipped",
    FAILED_APPLY = "failed_apply",
    FAILED_ROLLBACK = "failed_rollback",
    ROLLBACKED = "rollbacked"


class ApplySnapshotObservabilityHelper:
    """
    Helper class for formatting the ApplySnapshot logs.
    TODO: Log messages in JSON format for easy querying.
    """
    def __init__(self, logger: Logger):
        self.logger = logger

    def info(self, table_name: str, resource_id: str, status: Optional[ApplyResourceStatus] = None, reason: Optional[str] = None) -> None:
        """
        Log message at INFO level
        :param table_name: Name of the table to merge
        :param resource_id: ID for the resource to merge
        :param status: Status of the merge operation
        :param reason: Reason for the status
        :return: None
        """
        self.logger.info(self.message(table_name, resource_id, status, reason))

    def warning(self, table_name: str, resource_id: str, status: Optional[ApplyResourceStatus] = None, reason: Optional[str] = None) -> None:
        """
        Log message at WARN level
        :param table_name: Name of the table to merge
        :param resource_id: ID for the resource to merge
        :param status: Status of the merge operation
        :param reason: Reason for the status
        :return: None
        """
        self.logger.warning(self.message(table_name, resource_id, status, reason))

    def error(self, table_name: str, resource_id: str, status: Optional[ApplyResourceStatus] = None, reason: Optional[str] = None) -> None:
        """
        Log message at ERROR level
        :param table_name: Name of the table to merge
        :param resource_id: ID for the resource to merge
        :param status: Status of the merge operation
        :param reason: Reason for the failure
        :return: None
        """
        self.logger.error(self.message(table_name, resource_id, status, reason))

    def debug(self, table_name: str, resource_id: str, status: Optional[ApplyResourceStatus] = None, reason: Optional[str] = None) -> None:
        """
        Log message at DEBUG level
        :param table_name: Name of the table to merge
        :param resource_id: ID for the resource to merge
        :param status: Status of the merge operation
        :param reason: Reason for the status
        :return: None
        """
        self.logger.debug(self.message(table_name, resource_id, status, reason))

    @staticmethod
    def message(table_name: str, resource_id: str, status: Optional[ApplyResourceStatus] = None, reason: Optional[str] = None) -> str:
        """
        Construct the log message
        :param table_name: Name of the table to merge
        :param resource_id: ID for the resource to merge
        :param status: Status of the merge operation
        :param reason: Reason for the status
        :return: the constructed message
        """
        message = f"{table_name}/{resource_id}"
        if status:
            message = f"{message} {status.name}"
        if reason:
            message = f"{message} because: {reason}"
        return message
