#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from unittest.mock import Mock

import boto3
from botocore.config import Config
from moto import mock_aws
from res.resources import ad_automation, cluster_settings
from res.utils import table_utils


@mock_aws
def test_request_ad_authorization_message_sent(monkeypatch):
    client = boto3.client("sqs")
    response = client.create_queue(
        QueueName="test.fifo",
        Attributes={
            "FifoQueue": "true",
            "ContentBasedDeduplication": "true",
        },
    )
    queue_url = response.get("QueueUrl")

    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: queue_url)
    monkeypatch.setattr(ad_automation, "ad_authorization_nonce", lambda: 1)
    monkeypatch.setattr(
        ad_automation, "ad_authorization_instance_id", lambda: "instance_id"
    )

    assert ad_automation.request_ad_authorization()

    response = client.receive_message(
        QueueUrl=queue_url,
        WaitTimeSeconds=1,
    )
    messages = response.get("Messages", [])
    assert len(messages) == 1


@mock_aws
def test_remove_ad_authorization_message_sent(monkeypatch):
    client = boto3.client("sqs")
    response = client.create_queue(
        QueueName="test.fifo",
        Attributes={
            "FifoQueue": "true",
            "ContentBasedDeduplication": "true",
        },
    )
    queue_url = response.get("QueueUrl")

    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: queue_url)

    ad_automation.remove_ad_authorization(["instance_id"])

    response = client.receive_message(
        QueueUrl=queue_url,
        WaitTimeSeconds=1,
    )
    messages = response.get("Messages", [])
    assert len(messages) == 1

    ad_automation


def test_get_authorization_query_ad_automation_table(monkeypatch):
    monkeypatch.setattr(ad_automation, "ad_authorization_nonce", lambda: 1)
    monkeypatch.setattr(
        ad_automation, "ad_authorization_instance_id", lambda: "instance_id"
    )
    get_item_mock = Mock()
    monkeypatch.setattr(table_utils, "get_item", get_item_mock)

    ad_automation.get_authorization()
    get_item_mock.assert_called_once_with(
        "ad-automation",
        key={
            "instance_id": "instance_id",
        },
    )
