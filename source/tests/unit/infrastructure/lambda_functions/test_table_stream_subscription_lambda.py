#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
import json
from unittest.mock import Mock

from res.clients.ad_sync import ad_sync_client
from res.resources.dynamodb import dynamodb_stream_subscription

from idea.infrastructure.resources.lambda_functions.table_stream_subscription_lambda import (
    table_stream_subscription_handler,
)
from idea.infrastructure.resources.lambda_functions.table_stream_subscription_lambda.table_stream_subscription_handler import (
    ADConfigEventSubscriber,
)

EVENTS = {
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
        },
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
        },
    ]
}

AD_CONFIG_EVENT_SUBSCRIBER = ADConfigEventSubscriber()
ENTRY_WITH_DOMAIN_NAME_KEY = {
    "key": "directoryservice.name",
    "value": "value",
}
ENTRY_WITH_ADDITIONAL_SSSD_CONFIGS_KEY = {
    "key": "directoryservice.sssd.additional_sssd_configs",
    "value": "value",
}
ENTRY_WITH_NON_AD_KEY = {
    "key": "test",
    "value": "value",
}
OLD_ENTRY_WITH_DOMAIN_NAME_KEY = {
    "key": "directoryservice.name",
    "value": "old_value",
}


def test_table_stream_subscription_lambda_handle_stream_event_invoked():
    handle_record_data_mock = Mock()
    dynamodb_stream_subscription.handle_record_data = handle_record_data_mock

    table_stream_subscription_handler.handle(EVENTS, {})
    assert handle_record_data_mock.call_count == 3


def test_ad_config_event_subscriber_required_ad_key_is_monitored(
    monkeypatch,
):
    assert AD_CONFIG_EVENT_SUBSCRIBER.is_entry_monitored(ENTRY_WITH_DOMAIN_NAME_KEY)


def test_ad_config_event_subscriber_optional_ad_key_is_monitored(
    monkeypatch,
):
    assert AD_CONFIG_EVENT_SUBSCRIBER.is_entry_monitored(
        ENTRY_WITH_ADDITIONAL_SSSD_CONFIGS_KEY
    )


def test_ad_config_event_subscriber_non_ad_key_skipped(
    monkeypatch,
):
    assert not AD_CONFIG_EVENT_SUBSCRIBER.is_entry_monitored(ENTRY_WITH_NON_AD_KEY)


def test_ad_config_event_subscriber_on_create_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    AD_CONFIG_EVENT_SUBSCRIBER.on_create(ENTRY_WITH_DOMAIN_NAME_KEY)
    start_ad_sync_mock.assert_called_once()


def test_ad_config_event_subscriber_on_update_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    AD_CONFIG_EVENT_SUBSCRIBER.on_update(
        OLD_ENTRY_WITH_DOMAIN_NAME_KEY, ENTRY_WITH_DOMAIN_NAME_KEY
    )
    start_ad_sync_mock.assert_called_once()


def test_ad_config_event_subscriber_on_delete_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    AD_CONFIG_EVENT_SUBSCRIBER.on_delete(ENTRY_WITH_ADDITIONAL_SSSD_CONFIGS_KEY)
    start_ad_sync_mock.assert_called_once()
