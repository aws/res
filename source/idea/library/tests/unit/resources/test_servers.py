#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Dict, Optional

import pytest
import res as res
import res.exceptions as exceptions
from res.resources import servers
from res.utils import table_utils, time_utils

TEST_INSTANCE_ID = "test_instance_id"
TEST_STATE = "test_state"
UPDATED_STATE = "updates_state"
RANDOM_INSTANCE_ID = "random_instance_id"


class ServersTestContext:
    server: Optional[Dict]


class TestServers(unittest.TestCase):

    def setUp(self):
        self.context: ServersTestContext = ServersTestContext()
        self.context.server = {
            servers.SERVER_DB_HASH_KEY: TEST_INSTANCE_ID,
            servers.SERVER_DB_STATE_KEY: TEST_STATE,
        }
        table_utils.create_item(servers.SERVER_TABLE_NAME, item=self.context.server)

    def test_servers_get_servers_invalid_instance_id_should_fail(self):
        """
        get server failure
        """
        with pytest.raises(exceptions.ServerNotFound) as exc_info:
            servers.get_server(instance_id=RANDOM_INSTANCE_ID)
        assert f"Server not found: {RANDOM_INSTANCE_ID}" == exc_info.value.args[0]

    def test_servers_get_server_valid_instance_id_should_pass(self):
        """
        get server happy path
        """
        result = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert result is not None
        assert result.get(servers.SERVER_DB_HASH_KEY) == TEST_INSTANCE_ID
        assert result.get(servers.SERVER_DB_STATE_KEY) == TEST_STATE

    def test_servers_update_server_should_pass(self):
        """
        update server happy path
        """
        assert self.context.server is not None
        updated_server = self.context.server
        updated_server["state"] = UPDATED_STATE
        servers.update_server(updated_server)
        server = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert server is not None
        assert server.get(servers.SERVER_DB_HASH_KEY) == TEST_INSTANCE_ID
        assert server.get(servers.SERVER_DB_STATE_KEY) == UPDATED_STATE

        curr_time = time_utils.current_time_ms()
        assert server.get(servers.SERVER_DB_UPDATED_ON_KEY) is not None
        assert server.get(servers.SERVER_DB_UPDATED_ON_KEY) <= curr_time

    def test_servers_delete_server_fail(self):
        """
        delete server fail
        """
        with pytest.raises(Exception) as exc_info:
            servers.delete_server("")
        assert "No instance id provided" == exc_info.value.args[0]

    def test_servers_delete_server_pass(self):
        """
        delete server happy path
        """
        server = servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert server is not None
        assert server.get(servers.SERVER_DB_HASH_KEY) == TEST_INSTANCE_ID
        assert server.get(servers.SERVER_DB_STATE_KEY) == TEST_STATE

        servers.delete_server(TEST_INSTANCE_ID)

        with pytest.raises(exceptions.ServerNotFound) as exc_info:
            servers.get_server(instance_id=TEST_INSTANCE_ID)
        assert f"Server not found: {TEST_INSTANCE_ID}" == exc_info.value.args[0]
