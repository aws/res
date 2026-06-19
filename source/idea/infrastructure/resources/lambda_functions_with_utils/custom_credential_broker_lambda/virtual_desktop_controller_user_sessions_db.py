#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Optional

from botocore.exceptions import BotoCoreError, ClientError
from res.clients.aws import get_aws_provider  # type: ignore

USER_SESSION_OWNER_KEY = os.environ.get("USER_SESSION_OWNER_KEY", "")
USER_SESSION_SESSION_ID_KEY = os.environ.get("USER_SESSION_SESSION_ID_KEY", "")


class VirtualDesktopControllerUserSessionsDB:
    def __init__(self, cluster_name: str, module_id: str, logger: logging.Logger):
        self.cluster_name = cluster_name
        self.module_id = module_id
        self.dynamodb = get_aws_provider().dynamodb_table()
        self.table = self.dynamodb.Table(self.table_name)
        self.logger = logger

    @property
    def table_name(self) -> str:
        return f"{self.cluster_name}.{self.module_id}.controller.user-sessions"

    def get_user_session(self, owner_id: str, session_id: str) -> Any:
        try:
            response = self.table.get_item(
                Key={
                    USER_SESSION_OWNER_KEY: owner_id,
                    USER_SESSION_SESSION_ID_KEY: session_id,
                }
            )
            # Extract the item from the response
            item = response.get("Item")
            return item
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error getting item from DynamoDB: {e}")
            return None

    def get_project_id(self, owner_id: str, session_id: str) -> Optional[Any]:
        item = self.get_user_session(owner_id, session_id)
        if item:
            project_item = item.get("project")
            if project_item:
                return project_item.get("name")
        return None
