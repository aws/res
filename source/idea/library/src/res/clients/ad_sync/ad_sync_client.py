#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Optional

import boto3
import res.exceptions as exceptions
from pydantic import BaseModel
from res.constants import (
    AD_CONFIGURATION_REQUIRED_KEYS,
    AD_SYNC_LOCK_KEY,
    AD_SYNC_LOCK_TABLE,
    CLUSTER_NETWORK_PRIVATE_SUBNETS,
    VPC_ID_KEY,
)
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME, get_settings
from res.utils import table_utils, time_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class ADSyncStatus(BaseModel):
    task_id: str
    submission_time: int
    update_time: int
    status: str


def start_ad_sync() -> str:
    """
    Start the AD Sync ECS task if there's not an active task.
    Otherwise throw an exception.
    :return: Task id
    """
    cluster_settings = get_settings()
    if any(
        key not in cluster_settings or not cluster_settings[key]
        for key in AD_CONFIGURATION_REQUIRED_KEYS
    ):
        raise exceptions.ADSyncConfigurationNotFound(
            "AD configuration is not available in the ClusterSettings table yet. Skip the AD sync request."
        )

    logger.info(f"Attempting to start the AD Sync ECS task...")

    ecs_client = boto3.client("ecs")
    lock_client = table_utils.get_distributed_lock_client(AD_SYNC_LOCK_TABLE)

    lock = lock_client.acquire_lock(partition_key=AD_SYNC_LOCK_KEY)
    try:
        if get_running_task_id():
            raise exceptions.ADSyncInProcess(f"An AD Sync task is already running")

        task_response = ecs_client.run_task(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            taskDefinition=f"{os.environ.get('environment_name')}-ad-sync-task-definition",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": table_utils.get_item(
                        table_name=CLUSTER_SETTINGS_TABLE_NAME,
                        key={"key": CLUSTER_NETWORK_PRIVATE_SUBNETS},
                    )["value"],
                    "securityGroups": [get_ad_sync_security_group_id()],
                },
            },
            count=1,
            launchType="FARGATE",
        )

        task_id = task_response["tasks"][0]["taskArn"]
        logger.info(
            f"No running AD Sync task found, start a new AD Sync ECS task with ID: {task_id}"
        )
        return task_id
    finally:
        lock.release()


def stop_ad_sync(task_id: Optional[str] = None) -> Optional[str]:
    """
    Stop the AD Sync ECS task.
    :param task_id: Task id. If no ID is provided, stop current running task if any.
    :return: task ID or None.
    """
    logger.info(f"Attempting to stop the AD Sync ECS task...")

    ecs_client = boto3.client("ecs")
    lock_client = table_utils.get_distributed_lock_client(AD_SYNC_LOCK_TABLE)

    lock = lock_client.acquire_lock(partition_key=AD_SYNC_LOCK_KEY)
    try:
        if not task_id:
            logger.info(
                "No AD Sync task ID provided, attempt to stop the current running task"
            )
            task_id = get_running_task_id()
            if not task_id:
                logger.info("No running AD Sync task found, exit...")
                return None

        logger.info(f"Stopping AD Sync ECS task with ID: {task_id}")
        ecs_client.stop_task(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            task=task_id,
        )
        return task_id
    finally:
        lock.release()


# TODO: Implement a function to get ad sync task status from the AD sync status DDB table once it is created
def get_ad_sync_status(task_id: Optional[str] = None) -> ADSyncStatus:
    """
    Get status of the AD Sync ECS task.
    :param task_id: Task id. If no ID is provided, status of the last AD sync task will be returned.
    """
    pass


def get_running_task_id() -> Optional[str]:
    """
    Get running task ID. If no task is running, return None.
    :return: task ID or None
    """
    ecs_client = boto3.client("ecs")

    response = ecs_client.list_tasks(
        cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
        family=f"{os.environ.get('environment_name')}-ad-sync-task-definition",
        desiredStatus="RUNNING",
    )

    running_task = response["taskArns"]
    if not running_task:
        return None

    task_id = running_task[0]
    logger.info(f"Found running AD Sync task with ID: {task_id}")
    return task_id


# TODO: Store ad sync related resources in the cluster settings table and read from the table when needed.
def get_ad_sync_security_group_id() -> str:
    client = boto3.client("ec2")
    group_name = f"{os.environ.get('environment_name')}-ad-sync-security-group"
    vpc_id = table_utils.get_item(
        table_name=CLUSTER_SETTINGS_TABLE_NAME, key={"key": VPC_ID_KEY}
    )["value"]

    try:
        response = client.describe_security_groups(
            Filters=[
                {"Name": "group-name", "Values": [group_name]},
                {"Name": "vpc-id", "Values": [vpc_id]},
            ]
        )
        if response["SecurityGroups"]:
            security_group_id = response["SecurityGroups"][0]["GroupId"]
            return security_group_id
        else:
            raise Exception(
                "No security group found with the specified group name and VPC ID."
            )

    except Exception as e:
        logger.exception(f"Error fetching security group: {str(e)}")


# TODO: Replace this method by using get_ad_sync_status once it's ready
def is_task_terminated(task_id: str) -> bool:
    """
    Check if the task is terminated.
    :param task_id: Task id.
    :return: True if the task is terminated, False otherwise.
    """
    ecs_client = boto3.client("ecs")
    response = ecs_client.describe_tasks(
        cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
        tasks=[task_id],
    )
    return response["tasks"][0]["lastStatus"] in ["STOPPED", "DELETED"]
