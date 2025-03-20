#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

import boto3
import requests
import res.exceptions as exceptions
from res.constants import (
    AD_CONFIGURATION_REQUIRED_KEYS,
    AD_SYNC_LOCK_KEY,
    AD_SYNC_LOCK_TABLE,
    AD_SYNC_SECURITY_GROUP_ID_KEY,
    AD_SYNC_STATUS_RECORD_EXPIRE_TIME_IN_SEC,
    AD_SYNC_STATUS_STATUS_KEY,
    AD_SYNC_STATUS_SUBMISSION_TIME_KEY,
    AD_SYNC_STATUS_TABLE,
    AD_SYNC_STATUS_TASK_ID_KEY,
    AD_SYNC_STATUS_TTL_KEY,
    AD_SYNC_STATUS_UPDATE_TIME_KEY,
    CLUSTER_NETWORK_PRIVATE_SUBNETS,
    VPC_ID_KEY,
)
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME, get_settings
from res.utils import table_utils, time_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class ADSyncStatus(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    PENDING = "PENDING"
    TERMINATED = "TERMINATED"


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

    _lock = lock_client.acquire_lock(partition_key=AD_SYNC_LOCK_KEY)
    try:
        if _get_running_task_id():
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
                    "securityGroups": [
                        table_utils.get_item(
                            table_name=CLUSTER_SETTINGS_TABLE_NAME,
                            key={"key": AD_SYNC_SECURITY_GROUP_ID_KEY},
                        )["value"]
                    ],
                },
            },
            count=1,
            launchType="FARGATE",
        )

        task_id = _get_task_id_from_task_arn(task_response["tasks"][0]["taskArn"])
        logger.info(
            f"No running AD Sync task found, start a new AD Sync ECS task with ID: {task_id}"
        )
        set_ad_sync_status(ADSyncStatus.PENDING, task_id)
        return task_id
    finally:
        lock_client.close(release_locks=True)


def stop_ad_sync(task_id: Optional[str] = None) -> Optional[str]:
    """
    Stop the AD Sync ECS task.
    :param task_id: Task id. If no ID is provided, stop current running task if any.
    :return: task ID or None.
    """
    logger.info(f"Attempting to stop the AD Sync ECS task...")

    ecs_client = boto3.client("ecs")
    lock_client = table_utils.get_distributed_lock_client(AD_SYNC_LOCK_TABLE)

    _lock = lock_client.acquire_lock(partition_key=AD_SYNC_LOCK_KEY)
    try:
        if not task_id:
            logger.info(
                "No AD Sync task ID provided, attempt to stop the current running task"
            )
            task_id = _get_running_task_id()
            if not task_id:
                logger.info("No running AD Sync task found, exit...")
                return None

        logger.info(f"Stopping AD Sync ECS task with ID: {task_id}")
        ecs_client.stop_task(
            cluster=f"{os.environ.get('environment_name')}-ad-sync-cluster",
            task=task_id,
        )
        set_ad_sync_status(ADSyncStatus.TERMINATED, task_id)
        return task_id
    finally:
        lock_client.close(release_locks=True)


def get_ad_sync_status(task_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get status of the AD Sync ECS task.
    :param task_id: Task id. If no ID is provided, status of the last AD sync task will be returned.
    """
    logger.info("Fetching AD Sync task status...")
    if task_id:
        results = table_utils.query(
            table_name=AD_SYNC_STATUS_TABLE,
            attributes={AD_SYNC_STATUS_TASK_ID_KEY: task_id},
            limit=1,
        )
    else:
        # DynamoDB arranges items in numeric order when the sort key's data type is Number
        # Check https://aws.amazon.com/blogs/database/effective-data-sorting-with-amazon-dynamodb/
        results = table_utils.scan(table_name=AD_SYNC_STATUS_TABLE)

    if not results:
        logger.info(f"No AD Sync task found with task ID {task_id}")
        return None

    return sorted(
        results, key=lambda status: status.get("submission_time"), reverse=True
    )[0]


def set_ad_sync_status(status: ADSyncStatus, task_id: Optional[str] = None) -> None:
    if not task_id and os.environ.get("ECS_CONTAINER_METADATA_URI_V4"):
        # Retrieve the task ID from the ECS container metadata
        response = requests.get(f"{os.environ['ECS_CONTAINER_METADATA_URI_V4']}/task")
        if response.status_code == 200:
            task_metadata = response.json()
        else:
            raise Exception("Failed to retrieve ECS container metadata")

        logger.info(task_metadata)
        task_id = _get_task_id_from_task_arn(task_metadata.get("TaskARN"))

    task_status = get_ad_sync_status(task_id)
    if task_status:
        task_status[AD_SYNC_STATUS_STATUS_KEY] = status
        task_status[AD_SYNC_STATUS_UPDATE_TIME_KEY] = time_utils.current_time_ms()
        if status == ADSyncStatus.STOPPED or status == ADSyncStatus.ERROR:
            task_status[AD_SYNC_STATUS_TTL_KEY] = (
                task_status[AD_SYNC_STATUS_UPDATE_TIME_KEY]
                + AD_SYNC_STATUS_RECORD_EXPIRE_TIME_IN_SEC
            )
        table_utils.update_item(
            table_name=AD_SYNC_STATUS_TABLE,
            key={
                AD_SYNC_STATUS_TASK_ID_KEY: task_id,
                AD_SYNC_STATUS_SUBMISSION_TIME_KEY: task_status[
                    AD_SYNC_STATUS_SUBMISSION_TIME_KEY
                ],
            },
            item=task_status,
        )
    else:
        current_time_in_ms = time_utils.current_time_ms()
        item = {
            AD_SYNC_STATUS_TASK_ID_KEY: task_id,
            AD_SYNC_STATUS_SUBMISSION_TIME_KEY: current_time_in_ms,
            AD_SYNC_STATUS_UPDATE_TIME_KEY: current_time_in_ms,
            AD_SYNC_STATUS_STATUS_KEY: status,
        }
        table_utils.create_item(table_name=AD_SYNC_STATUS_TABLE, item=item)


def _get_running_task_id() -> Optional[str]:
    """
    Get running task ID. If no task is running, return None.
    :return: task ID or None
    """
    ecs_client = boto3.client("ecs")
    environment_name = os.environ.get("environment_name")

    # check pending task first
    response = ecs_client.list_tasks(
        cluster=f"{environment_name}-ad-sync-cluster",
        family=f"{environment_name}-ad-sync-task-definition",
        desiredStatus="PENDING",
    )
    pending_task = response["taskArns"]
    if pending_task:
        task_id = _get_task_id_from_task_arn(pending_task[0])
        logger.info(f"Found pending AD Sync task with ID: {task_id}")
        return task_id

    #  check running task if no pending task
    response = ecs_client.list_tasks(
        cluster=f"{environment_name}-ad-sync-cluster",
        family=f"{environment_name}-ad-sync-task-definition",
        desiredStatus="RUNNING",
    )

    running_task = response["taskArns"]
    if not running_task:
        return None

    task_id = _get_task_id_from_task_arn(running_task[0])
    logger.info(f"Found running AD Sync task with ID: {task_id}")
    return task_id


def _get_task_id_from_task_arn(task_arn: str) -> str:
    return task_arn.split("/")[-1]


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
