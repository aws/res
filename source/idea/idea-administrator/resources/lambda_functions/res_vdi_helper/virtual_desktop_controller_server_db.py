#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the 'License'). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.
import logging
import os
from typing import Any, Dict, Optional

import boto3

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

SERVER_DB_HASH_KEY = os.environ.get('SERVER_HASH_KEY')
SERVER_DB_IDEA_SESSION_OWNER_KEY = os.environ.get('SERVER_DB_IDEA_SESSION_OWNER_KEY')
SERVER_DB_IDEA_SESSION_ID_KEY = os.environ.get('SERVER_DB_IDEA_SESSION_ID_KEY')
SERVER_TABLE_NAME = 'vdc.controller.servers'

# TODO: Replace this with table utils table() once migrated
def table(table_name: str) -> Any: 
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(f"{os.environ.get('CLUSTER_NAME')}.{table_name}")

# TODO: Replace this with table utils get_item() once migrated to shared library
def get_item(table_name: str, key: Dict[str, str]) -> Optional[Dict[str, Any]]:

    item: Optional[Dict[str, Any]] = (
        table(table_name).get_item(Key=key).get("Item", None)
    )
    return item

def get_server(instance_id: str) -> Dict[str, Any]:
    """
    Retrieve server from DDB
    :param instance_id: Ec2 instance id
    :return: server details
    """
    logger.info(f"Getting server details for {SERVER_DB_HASH_KEY}: {instance_id}")

    server: Dict[str, Any] = get_item(
        SERVER_TABLE_NAME, key={SERVER_DB_HASH_KEY: instance_id}
    )
    if not server:
        raise ValueError(
            f"Server not found: {instance_id}",
        )
    return server

def get_owner_id_and_session_id(instance_id):
    server = get_server(instance_id)
    item = server.get("Item")
    if item:
        return {
            "owner_id": item.get(SERVER_DB_IDEA_SESSION_OWNER_KEY),
            "session_id": item.get(SERVER_DB_IDEA_SESSION_ID_KEY)
        }
    return None
