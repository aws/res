#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import os

import boto3
import pytest
from moto import mock_aws
from res.constants import (
    AD_AUTOMATION_DB_HASH_KEY,
    AD_AUTOMATION_TABLE_NAME,
    AD_SYNC_LOCK_TABLE,
    AD_SYNC_STATUS_SUBMISSION_TIME_KEY,
    AD_SYNC_STATUS_TABLE,
    AD_SYNC_STATUS_TASK_ID_KEY,
    ENVIRONMENT_NAME_KEY,
)
from res.resources import (
    cluster_settings,
    email_templates,
    modules,
    permission_profiles,
    schedules,
    session_permissions,
    sessions,
    software_stacks,
)

ENVIRONMENT_NAME = "res-test"


def _create_tables():
    """Create all DynamoDB tables needed by RES library unit tests."""
    client = boto3.client("dynamodb", region_name="us-west-1")

    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.accounts.users",
        AttributeDefinitions=[
            {"AttributeName": "username", "AttributeType": "S"},
            {"AttributeName": "role", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "role-index",
                "KeySchema": [{"AttributeName": "role", "KeyType": "HASH"}],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["additional_groups", "username"],
                },
            },
            {
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": ["role", "username", "is_active", "enabled"],
                },
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.accounts.groups",
        AttributeDefinitions=[{"AttributeName": "group_name", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "group_name", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.accounts.group-members",
        AttributeDefinitions=[
            {"AttributeName": "group_name", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "group_name", "KeyType": "HASH"},
            {"AttributeName": "username", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.authz.role-assignments",
        AttributeDefinitions=[
            {"AttributeName": "actor_key", "AttributeType": "S"},
            {"AttributeName": "resource_key", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "actor_key", "KeyType": "HASH"},
            {"AttributeName": "resource_key", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "resource-key-index",
                "KeySchema": [
                    {"AttributeName": "resource_key", "KeyType": "HASH"},
                    {"AttributeName": "actor_key", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.projects",
        AttributeDefinitions=[
            {"AttributeName": "project_id", "AttributeType": "S"},
            {"AttributeName": "name", "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": "project_id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "project-name-index",
                "KeySchema": [{"AttributeName": "name", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{sessions.SESSIONS_TABLE_NAME}",
        AttributeDefinitions=[
            {"AttributeName": sessions.SESSION_DB_HASH_KEY, "AttributeType": "S"},
            {"AttributeName": sessions.SESSION_DB_RANGE_KEY, "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": sessions.SESSION_DB_HASH_KEY, "KeyType": "HASH"},
            {"AttributeName": sessions.SESSION_DB_RANGE_KEY, "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{cluster_settings.CLUSTER_SETTINGS_TABLE_NAME}",
        AttributeDefinitions=[
            {
                "AttributeName": cluster_settings.CLUSTER_SETTINGS_HASH_KEY,
                "AttributeType": "S",
            }
        ],
        KeySchema=[
            {
                "AttributeName": cluster_settings.CLUSTER_SETTINGS_HASH_KEY,
                "KeyType": "HASH",
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{session_permissions.SESSION_PERMISSION_TABLE_NAME}",
        AttributeDefinitions=[
            {
                "AttributeName": session_permissions.SESSION_PERMISSION_DB_HASH_KEY,
                "AttributeType": "S",
            },
            {
                "AttributeName": session_permissions.SESSION_PERMISSION_DB_RANGE_KEY,
                "AttributeType": "S",
            },
        ],
        KeySchema=[
            {
                "AttributeName": session_permissions.SESSION_PERMISSION_DB_HASH_KEY,
                "KeyType": "HASH",
            },
            {
                "AttributeName": session_permissions.SESSION_PERMISSION_DB_RANGE_KEY,
                "KeyType": "RANGE",
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{schedules.SCHEDULE_DB_TABLE_NAME}",
        AttributeDefinitions=[
            {"AttributeName": schedules.SCHEDULE_DB_HASH_KEY, "AttributeType": "S"},
            {"AttributeName": schedules.SCHEDULE_DB_RANGE_KEY, "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": schedules.SCHEDULE_DB_HASH_KEY, "KeyType": "HASH"},
            {"AttributeName": schedules.SCHEDULE_DB_RANGE_KEY, "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{AD_SYNC_LOCK_TABLE}",
        KeySchema=[{"AttributeName": "lock_key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "lock_key", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{AD_AUTOMATION_TABLE_NAME}",
        KeySchema=[{"AttributeName": AD_AUTOMATION_DB_HASH_KEY, "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": AD_AUTOMATION_DB_HASH_KEY, "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{AD_SYNC_STATUS_TABLE}",
        AttributeDefinitions=[
            {"AttributeName": AD_SYNC_STATUS_TASK_ID_KEY, "AttributeType": "S"},
            {"AttributeName": AD_SYNC_STATUS_SUBMISSION_TIME_KEY, "AttributeType": "N"},
        ],
        KeySchema=[
            {"AttributeName": AD_SYNC_STATUS_TASK_ID_KEY, "KeyType": "HASH"},
            {"AttributeName": AD_SYNC_STATUS_SUBMISSION_TIME_KEY, "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{permission_profiles.PERMISSION_PROFILE_TABLE_NAME}",
        KeySchema=[
            {
                "AttributeName": permission_profiles.PERMISSION_PROFILE_DB_HASH_KEY,
                "KeyType": "HASH",
            }
        ],
        AttributeDefinitions=[
            {
                "AttributeName": permission_profiles.PERMISSION_PROFILE_DB_HASH_KEY,
                "AttributeType": "S",
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.modules",
        KeySchema=[
            {"AttributeName": modules.MODULES_TABLE_HASH_KEY, "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": modules.MODULES_TABLE_HASH_KEY, "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{software_stacks.SOFTWARE_STACK_TABLE_NAME}",
        KeySchema=[
            {
                "AttributeName": software_stacks.SOFTWARE_STACK_DB_HASH_KEY,
                "KeyType": "HASH",
            },
            {
                "AttributeName": software_stacks.SOFTWARE_STACK_DB_RANGE_KEY,
                "KeyType": "RANGE",
            },
        ],
        AttributeDefinitions=[
            {
                "AttributeName": software_stacks.SOFTWARE_STACK_DB_HASH_KEY,
                "AttributeType": "S",
            },
            {
                "AttributeName": software_stacks.SOFTWARE_STACK_DB_RANGE_KEY,
                "AttributeType": "S",
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{email_templates.EMAIL_TEMPLATE_TABLE_NAME}",
        KeySchema=[
            {
                "AttributeName": email_templates.EMAIL_TEMPLATE_DB_NAME_KEY,
                "KeyType": "HASH",
            }
        ],
        AttributeDefinitions=[
            {
                "AttributeName": email_templates.EMAIL_TEMPLATE_DB_NAME_KEY,
                "AttributeType": "S",
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture(autouse=True)
def aws_env():
    """Set AWS environment variables for all tests."""
    os.environ[ENVIRONMENT_NAME_KEY] = ENVIRONMENT_NAME
    os.environ["AWS_DEFAULT_REGION"] = "us-west-1"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(autouse=True, scope="module")
def context():
    """Module-scoped mock_aws + DDB tables. Tests within a file share state."""
    with mock_aws():
        boto3.setup_default_session(region_name="us-west-1")
        _create_tables()
        yield
