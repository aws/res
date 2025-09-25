#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

DCV_HOST_DB_HASH_KEY = os.environ.get("DCV_HOST_DB_HASH_KEY", "")
DCV_HOST_DB_IDEA_SESSION_OWNER_KEY = os.environ.get(
    "DCV_HOST_DB_IDEA_SESSION_OWNER_KEY", ""
)
DCV_HOST_DB_IDEA_SESSION_ID_KEY = os.environ.get("DCV_HOST_DB_IDEA_SESSION_ID_KEY", "")


class VirtualDesktopControllerServerDB:
    def __init__(self, cluster_name: str, module_id: str, logger: logging.Logger):
        self.cluster_name = cluster_name
        self.module_id = module_id
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)
        self.logger = logger

    @property
    def table_name(self) -> str:
        return f"{self.cluster_name}.{self.module_id}.controller.servers"

    def get_server(self, instance_id: str) -> Any:
        try:
            response = self.table.get_item(Key={DCV_HOST_DB_HASH_KEY: instance_id})
            # Extract the item from the response
            item = response.get("Item")
            return item
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error getting item from DynamoDB: {e}")
            return None

    def get_owner_id_and_session_id(self, instance_id: str) -> Optional[Dict[str, Any]]:
        item = self.get_server(instance_id)
        if item:
            return {
                "owner_id": item.get(DCV_HOST_DB_IDEA_SESSION_OWNER_KEY),
                "session_id": item.get(DCV_HOST_DB_IDEA_SESSION_ID_KEY),
            }
        return None
