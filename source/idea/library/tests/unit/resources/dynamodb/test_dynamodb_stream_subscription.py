#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Dict
from unittest.mock import Mock

from boto3.dynamodb.types import TypeDeserializer
from res.resources.dynamodb.dynamodb_stream_subscriber import IDynamoDBStreamSubscriber
from res.resources.dynamodb.dynamodb_stream_subscription import handle_record_data

DDB_TYPE_DESERIALIZER = TypeDeserializer()

ON_CREATE_INVOKED = False
ON_UPDATE_INVOKED = False
ON_DELETE_INVOKED = False

INSERT_EVENT_DATA = {
    "eventName": "INSERT",
    "dynamodb": {
        "NewImage": {
            "value": {"S": "test_value"},
            "key": {"S": "test_key"},
        },
    },
}
MODIFY_EVENT_DATA = {
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
DELETE_EVENT_DATA = {
    "eventName": "REMOVE",
    "dynamodb": {
        "OldImage": {
            "value": {"S": "test_value"},
            "key": {"S": "test_key"},
        },
    },
}


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


MOCK_SUBSCRIBER = MockStreamSubscriber()


def test_handle_insert_event_on_create_invoked():
    handle_record_data(
        INSERT_EVENT_DATA, DDB_TYPE_DESERIALIZER, [MOCK_SUBSCRIBER], Mock()
    )
    global ON_CREATE_INVOKED
    assert ON_CREATE_INVOKED, "on_create is not invoked"

    ON_CREATE_INVOKED = False


def test_handle_insert_event_on_update_invoked():
    handle_record_data(
        MODIFY_EVENT_DATA, DDB_TYPE_DESERIALIZER, [MOCK_SUBSCRIBER], Mock()
    )
    global ON_UPDATE_INVOKED
    assert ON_UPDATE_INVOKED, "on_update is not invoked"

    ON_UPDATE_INVOKED = False


def test_handle_insert_event_on_delete_invoked():
    handle_record_data(
        DELETE_EVENT_DATA, DDB_TYPE_DESERIALIZER, [MOCK_SUBSCRIBER], Mock()
    )
    global ON_DELETE_INVOKED
    assert ON_DELETE_INVOKED, "on_delete is not invoked"

    ON_DELETE_INVOKED = False
