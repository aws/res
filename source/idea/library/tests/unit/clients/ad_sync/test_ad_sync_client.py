#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import boto3
import pytest
import res.exceptions as exceptions
from moto import mock_aws
from res.clients.ad_sync import ad_sync_client
from res.constants import (
    AD_CONFIGURATION_REQUIRED_KEYS,
    AD_SYNC_LOCK_KEY,
    CLUSTER_NETWORK_PRIVATE_SUBNETS,
    VPC_ID_KEY,
)
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME
from res.utils import table_utils, time_utils


@mock_aws
@pytest.mark.usefixtures("context")
class TestADSyncClient(TestCase):

    def setUp(self) -> None:
        os.environ["AWS_DEFAULT_REGION"] = "us-west-1"

        self.ecs_client = boto3.client("ecs")
        self.ec2_client = boto3.client("ec2")

        vpc = self.ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc["Vpc"]["VpcId"]

        self.subnets = []
        subnet_1a = self.ec2_client.create_subnet(
            CidrBlock="10.0.1.0/24", VpcId=vpc_id, AvailabilityZone="us-west-1a"
        )
        self.subnets.append(subnet_1a["Subnet"]["SubnetId"])

        subnet_1b = self.ec2_client.create_subnet(
            CidrBlock="10.0.2.0/24", VpcId=vpc_id, AvailabilityZone="us-west-1b"
        )
        self.subnets.append(subnet_1b["Subnet"]["SubnetId"])

        security_group = self.ec2_client.create_security_group(
            Description="AD Sync Security Group",
            GroupName=f'{os.environ.get("environment_name")}-ad-sync-security-group',
            VpcId=vpc_id,
        )
        self.security_group_id = security_group["GroupId"]

        self.ecs_client.create_cluster(
            clusterName=f"{os.environ.get('environment_name')}-ad-sync-cluster"
        )

        self.ecs_client.register_task_definition(
            family=f"{os.environ.get('environment_name')}-ad-sync-task-definition",
            networkMode="awsvpc",
            containerDefinitions=[
                {
                    "name": "test-container",
                    "image": "test-image",
                    "essential": True,
                    "memory": 1024,
                    "cpu": 512,
                }
            ],
        )

        table_utils.create_item(
            CLUSTER_SETTINGS_TABLE_NAME,
            item={
                "key": VPC_ID_KEY,
                "value": vpc_id,
            },
        )

        table_utils.create_item(
            CLUSTER_SETTINGS_TABLE_NAME,
            item={
                "key": CLUSTER_NETWORK_PRIVATE_SUBNETS,
                "value": self.subnets,
            },
        )

        for key in AD_CONFIGURATION_REQUIRED_KEYS:
            table_utils.create_item(
                CLUSTER_SETTINGS_TABLE_NAME,
                item={
                    "key": key,
                    "value": "test_value",
                },
            )

    def tearDown(self) -> None:
        self.ecs_client.delete_cluster(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster"
        )
        os.unsetenv("AWS_DEFAULT_REGION")

    @patch("python_dynamodb_lock.python_dynamodb_lock.DynamoDBLockClient.acquire_lock")
    def test_start_ad_sync_without_running_task(self, mock_lock) -> None:
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()

        task_id = ad_sync_client.start_ad_sync()
        mock_lock.assert_called_once_with(partition_key=AD_SYNC_LOCK_KEY)

        self.assertIsNotNone(task_id)
        self.assertTrue(task_id.startswith("arn:aws:ecs:"))

    @patch("python_dynamodb_lock.python_dynamodb_lock.DynamoDBLockClient.acquire_lock")
    def test_start_ad_sync_with_running_task(self, mock_lock) -> None:
        self.ecs_client.run_task(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            taskDefinition=f"{os.environ.get('environment_name')}-ad-sync-task-definition",
            count=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": self.subnets,
                    "securityGroups": [self.security_group_id],
                }
            },
        )

        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()

        with self.assertRaises(exceptions.ADSyncInProcess) as context:
            ad_sync_client.start_ad_sync()

        mock_lock.assert_called_once_with(partition_key=AD_SYNC_LOCK_KEY)
        self.assertEqual(str(context.exception), "An AD Sync task is already running")

    @patch("python_dynamodb_lock.python_dynamodb_lock.DynamoDBLockClient.acquire_lock")
    def test_stop_ad_sync_with_task_id(self, mock_lock) -> None:
        response = self.ecs_client.run_task(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            taskDefinition=f"{os.environ.get('environment_name')}-ad-sync-task-definition",
            count=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": self.subnets,
                    "securityGroups": [self.security_group_id],
                }
            },
        )
        task_id = response["tasks"][0]["taskArn"]
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()

        ad_sync_client.stop_ad_sync(task_id=task_id)

        mock_lock.assert_called_once_with(partition_key=AD_SYNC_LOCK_KEY)
        response = self.ecs_client.describe_tasks(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            tasks=[task_id],
        )
        task_status = response["tasks"][0]["lastStatus"]
        self.assertEqual(task_status, "STOPPED")

    @patch("python_dynamodb_lock.python_dynamodb_lock.DynamoDBLockClient.acquire_lock")
    def test_stop_ad_sync_without_task_id_with_running_task(self, mock_lock) -> None:
        response = self.ecs_client.run_task(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            taskDefinition=f"{os.environ.get('environment_name')}-ad-sync-task-definition",
            count=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": self.subnets,
                    "securityGroups": [self.security_group_id],
                }
            },
        )
        task_id = response["tasks"][0]["taskArn"]
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()

        ad_sync_client.stop_ad_sync()

        mock_lock.assert_called_once_with(partition_key=AD_SYNC_LOCK_KEY)
        response = self.ecs_client.describe_tasks(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            tasks=[task_id],
        )
        task_status = response["tasks"][0]["lastStatus"]
        self.assertEqual(task_status, "STOPPED")

    @patch("python_dynamodb_lock.python_dynamodb_lock.DynamoDBLockClient.acquire_lock")
    def test_stop_ad_sync_without_task_id_without_running_task(self, mock_lock) -> None:
        mock_lock.__enter__ = MagicMock()
        mock_lock.__exit__ = MagicMock()
        ad_sync_client.stop_ad_sync()

        mock_lock.assert_called_once_with(partition_key=AD_SYNC_LOCK_KEY)
        tasks = self.ecs_client.list_tasks(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster"
        )
        self.assertEqual(len(tasks["taskArns"]), 0)

    def test_get_running_task_id_without_running_task(self) -> None:
        task_id = ad_sync_client.get_running_task_id()
        self.assertIsNone(task_id)

    def test_get_running_task_id_with_running_task(self) -> None:
        self.ecs_client.run_task(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            taskDefinition=f"{os.environ.get('environment_name')}-ad-sync-task-definition",
            count=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": self.subnets,
                    "securityGroups": [self.security_group_id],
                }
            },
        )

        task_id = ad_sync_client.get_running_task_id()
        self.assertIsNotNone(task_id)
        self.assertTrue(task_id.startswith("arn:aws:ecs:"))
