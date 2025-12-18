#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock, call, patch

from idea.infrastructure.resources.lambda_functions.delete_dcv_broker_tables_lambda import (
    delete_dcv_broker_tables_handler,
)


@patch("boto3.client")
def test_delete_dcv_broker_tables(mock_boto_client: Mock) -> None:
    ddb_client = Mock()
    ddb_client.list_tables.return_value = {
        "TableNames": [
            "res-env.vdc.dcv-broker.AgentKeyPair",
            "res-env.vdc.dcv-broker.AgentOAuth2Clients",
            "someRandomTable",
        ]
    }
    ddb_client.delete_table.return_value = {}
    mock_boto_client.return_value = ddb_client

    delete_dcv_broker_tables_handler.delete_dcv_broker_tables(
        {
            "RequestType": "Delete",
            "ResourceProperties": {"environment_name": "res-env"},
        },
        None,
    )
    client_calls = [
        call.list_tables(),
        call.delete_table(TableName="res-env.vdc.dcv-broker.AgentKeyPair"),
        call.delete_table(TableName="res-env.vdc.dcv-broker.AgentOAuth2Clients"),
    ]
    ddb_client.assert_has_calls(client_calls)
