#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

import res.exceptions as exceptions
from res.utils import table_utils, time_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

SERVER_TABLE_NAME = "vdc.controller.servers"
SERVER_DB_HASH_KEY = "instance_id"
SERVER_DB_UPDATED_ON_KEY = "updated_on"
SERVER_DB_STATE_KEY = "state"
SERVER_DB_SESSION_ID_KEY = "idea_session_id"
SERVER_DB_SESSION_OWNER_KEY = "idea_session_owner"


def get_server(instance_id: str) -> Dict[str, Any]:
    """
    Retrieve server from DDB
    :param instance_id: Ec2 instance id
    :return: server details
    """
    logger.info(f"Getting server details for {SERVER_DB_HASH_KEY}: {instance_id}")

    server: Dict[str, Any] = table_utils.get_item(
        SERVER_TABLE_NAME, key={SERVER_DB_HASH_KEY: instance_id}
    )
    if not server:
        raise exceptions.ServerNotFound(
            f"Server not found: {instance_id}",
        )
    return server


def update_server(server: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update Server DB
    :param server: Server dict value to update
    :return updated server
    """
    logger.info(
        f"Updating session for {SERVER_DB_HASH_KEY}: {server[SERVER_DB_HASH_KEY]}"
    )

    server[SERVER_DB_UPDATED_ON_KEY] = time_utils.current_time_ms()

    updated_server: Dict[str, Any] = table_utils.update_item(
        SERVER_TABLE_NAME,
        key={SERVER_DB_HASH_KEY: server[SERVER_DB_HASH_KEY]},
        item=server,
    )
    return updated_server


def delete_server(instance_id: str) -> None:
    """
    Delete server in DDB
    :param instance_id: Ec2 instance id
    :return None
    """

    if not instance_id:
        raise Exception("No instance id provided")

    table_utils.delete_item(SERVER_TABLE_NAME, key={SERVER_DB_HASH_KEY: instance_id})
