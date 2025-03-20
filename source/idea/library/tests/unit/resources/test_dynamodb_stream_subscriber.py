#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock

from res.clients.ad_sync import ad_sync_client  # type: ignore
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME
from res.resources.dynamodb_stream_subscriber import get_table_stream_subscriber

CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER = get_table_stream_subscriber(
    CLUSTER_SETTINGS_TABLE_NAME
)

ENTRY_WITH_REQUIRED_AD_KEY = {
    "key": "directoryservice.name",
    "value": "value",
}
ENTRY_WITH_OPTIONAL_AD_KEY = {
    "key": "directoryservice.sssd.additional_sssd_configs",
    "value": "value",
}
ENTRY_WITH_NON_AD_KEY = {
    "key": "test",
    "value": "value",
}
OLD_ENTRY_WITH_REQUIRED_AD_KEY = {
    "key": "directoryservice.name",
    "value": "old_value",
}
OLD_ENTRY_WITH_OPTIONAL_AD_KEY = {
    "key": "directoryservice.sssd.additional_sssd_configs",
    "value": "old_value",
}
OLD_ENTRY_WITH_NON_AD_KEY = {
    "key": "test",
    "value": "old_value",
}


def test_cluster_settings_table_stream_subscriber_on_create_required_ad_key_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_create(ENTRY_WITH_REQUIRED_AD_KEY)
    start_ad_sync_mock.assert_called_once()


def test_cluster_settings_table_stream_subscriber_on_create_optional_ad_key_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_create(ENTRY_WITH_OPTIONAL_AD_KEY)
    start_ad_sync_mock.assert_called_once()


def test_cluster_settings_table_stream_subscriber_on_create_non_ad_key_skip_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_create(ENTRY_WITH_NON_AD_KEY)
    start_ad_sync_mock.assert_not_called()


def test_cluster_settings_table_stream_subscriber_on_update_required_ad_key_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_update(
        OLD_ENTRY_WITH_REQUIRED_AD_KEY, ENTRY_WITH_REQUIRED_AD_KEY
    )
    start_ad_sync_mock.assert_called_once()


def test_cluster_settings_table_stream_subscriber_on_update_optional_ad_key_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_update(
        OLD_ENTRY_WITH_OPTIONAL_AD_KEY, ENTRY_WITH_OPTIONAL_AD_KEY
    )
    start_ad_sync_mock.assert_called_once()


def test_cluster_settings_table_stream_subscriber_on_update_non_ad_key_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_update(
        OLD_ENTRY_WITH_NON_AD_KEY, ENTRY_WITH_NON_AD_KEY
    )
    start_ad_sync_mock.assert_not_called()


def test_cluster_settings_table_stream_subscriber_on_delete_required_ad_key_skip_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_delete(ENTRY_WITH_REQUIRED_AD_KEY)
    start_ad_sync_mock.assert_not_called()


def test_cluster_settings_table_stream_subscriber_on_delete_optional_ad_key_start_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_delete(ENTRY_WITH_OPTIONAL_AD_KEY)
    start_ad_sync_mock.assert_called_once()


def test_cluster_settings_table_stream_subscriber_on_delete_non_ad_key_skip_ad_sync(
    monkeypatch,
):
    start_ad_sync_mock = Mock()
    monkeypatch.setattr(ad_sync_client, "start_ad_sync", start_ad_sync_mock)
    CLUSTER_SETTINGS_TABLE_STREAM_SUBSCRIBER.on_delete(ENTRY_WITH_NON_AD_KEY)
    start_ad_sync_mock.assert_not_called()
