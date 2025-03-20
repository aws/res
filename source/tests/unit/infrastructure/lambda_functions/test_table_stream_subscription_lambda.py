#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
import json
import os
from typing import Dict

from res.resources.dynamodb_stream_subscriber import (
    IDynamoDBStreamSubscriber,
    register_table_stream_subscriber,
)

from idea.infrastructure.resources.lambda_functions.table_stream_subscription_lambda import (
    table_stream_subscription_handler,
)

ON_CREATE_INVOKED = False
ON_UPDATE_INVOKED = False
ON_DELETE_INVOKED = False

TEST_TABLE_NAME = "test_table_name"
INSERT_EVENTS = {
    "Records": [
        {
            "kinesis": {
                "data": base64.b64encode(
                    json.dumps(
                        {
                            "eventName": "INSERT",
                            "dynamodb": {
                                "NewImage": {
                                    "value": {"S": "test_value"},
                                    "key": {"S": "test_key"},
                                },
                            },
                        }
                    ).encode("utf-8")
                )
            },
        },
    ]
}
MODIFY_EVENTS = {
    "Records": [
        {
            "kinesis": {
                "data": base64.b64encode(
                    json.dumps(
                        {
                            "eventName": "MODIFY",
                            "dynamodb": {
                                "NewImage": {
                                    "value": {"S": "new_test_value"},
                                    "key": {"S": "new_test_key"},
                                },
                                "OldImage": {
                                    "value": {"S": "old_test_value"},
                                    "key": {"S": "old_test_key"},
                                },
                            },
                        }
                    ).encode("utf-8")
                )
            },
        }
    ]
}
DELETE_EVENTS = {
    "Records": [
        {
            "kinesis": {
                "data": base64.b64encode(
                    json.dumps(
                        {
                            "eventName": "REMOVE",
                            "dynamodb": {
                                "OldImage": {
                                    "value": {"S": "test_value"},
                                    "key": {"S": "test_key"},
                                },
                            },
                        }
                    ).encode("utf-8")
                )
            },
        }
    ]
}


@register_table_stream_subscriber(TEST_TABLE_NAME)
class MockStreamSubscriber(IDynamoDBStreamSubscriber):
    def on_create(self, entry: Dict):
        global ON_CREATE_INVOKED
        ON_CREATE_INVOKED = True

    def on_update(self, old_entry: Dict, new_entry: Dict):
        global ON_UPDATE_INVOKED
        ON_UPDATE_INVOKED = True

    def on_delete(self, entry: Dict):
        global ON_DELETE_INVOKED
        ON_DELETE_INVOKED = True


def test_handle_insert_event_on_create_invoked():
    os.environ["TABLE_NAME"] = TEST_TABLE_NAME

    table_stream_subscription_handler.handle(INSERT_EVENTS, {})
    global ON_CREATE_INVOKED
    assert ON_CREATE_INVOKED, "on_create is not invoked"

    os.environ.pop("TABLE_NAME", None)
    ON_CREATE_INVOKED = False


def test_handle_insert_event_on_update_invoked():
    os.environ["TABLE_NAME"] = TEST_TABLE_NAME

    table_stream_subscription_handler.handle(MODIFY_EVENTS, {})
    global ON_UPDATE_INVOKED
    assert ON_UPDATE_INVOKED, "on_update is not invoked"

    os.environ.pop("TABLE_NAME", None)
    ON_UPDATE_INVOKED = False


def test_handle_insert_event_on_delete_invoked():
    os.environ["TABLE_NAME"] = TEST_TABLE_NAME

    table_stream_subscription_handler.handle(DELETE_EVENTS, {})
    global ON_DELETE_INVOKED
    assert ON_DELETE_INVOKED, "on_delete is not invoked"

    os.environ.pop("TABLE_NAME", None)
    ON_DELETE_INVOKED = False
