#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import os
import time

import boto3
import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideatestutils.dynamodb.dynamodb_local import DynamoDBLocal
from res.constants import AD_SYNC_LOCK_TABLE, ENVIRONMENT_NAME_KEY
from res.resources import (
    cluster_settings,
    email_templates,
    modules,
    permission_profiles,
    schedules,
    servers,
    session_permissions,
    sessions,
    software_stacks,
)

# initialize monkey patch globally, so that it can be used inside session scoped context fixtures
# this allows session scoped monkey patches to be applicable across all unit tests
# monkeypatch.undo() is called at the end of context fixture
monkeypatch = MonkeyPatch()


@pytest.fixture(scope="session")
def ddb_local():
    ddb_local = DynamoDBLocal(db_name="ad-sync", reset=True)
    ddb_local.start()

    # wait for ddb local server to start ...
    time.sleep(1)

    yield ddb_local

    ddb_local.stop()


@pytest.fixture(scope="session")
def context(ddb_local):
    os.environ[ENVIRONMENT_NAME_KEY] = "res-test"
    ENVIRONMENT_NAME = "res-test"
    boto3.setup_default_session(
        region_name="us-west-1", aws_access_key_id="test", aws_secret_access_key="test"
    )

    # Override the endpoint for boto3.resource("dynamodb") to use DynamoDB local
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:9000")

    def _resource(service_name: str):
        if service_name == "dynamodb":
            return dynamodb

    monkeypatch.setattr(boto3, "resource", _resource)

    # Create all the tables in DynamoDB local
    dynamodb_client = boto3.client("dynamodb", endpoint_url="http://localhost:9000")
    dynamodb_client.create_table(
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

    dynamodb_client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.accounts.groups",
        AttributeDefinitions=[{"AttributeName": "group_name", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "group_name", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )

    dynamodb_client.create_table(
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

    dynamodb_client.create_table(
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

    dynamodb_client.create_table(
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

    # Create sessions table
    dynamodb_client.create_table(
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

    # Create servers table
    dynamodb_client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{servers.SERVER_TABLE_NAME}",
        AttributeDefinitions=[
            {"AttributeName": servers.SERVER_DB_HASH_KEY, "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": servers.SERVER_DB_HASH_KEY, "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Create cluster settings table
    dynamodb_client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{cluster_settings.CLUSTER_SETTINGS_TABLE_NAME}",
        AttributeDefinitions=[
            {
                "AttributeName": cluster_settings.CLUSTER_SETTINGS_HASH_KEY,
                "AttributeType": "S",
            },
        ],
        KeySchema=[
            {
                "AttributeName": cluster_settings.CLUSTER_SETTINGS_HASH_KEY,
                "KeyType": "HASH",
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Create session permissions table
    dynamodb_client.create_table(
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

    # Create schedules table
    dynamodb_client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{schedules.SCHEDULE_DB_TABLE_NAME}",
        AttributeDefinitions=[
            {
                "AttributeName": schedules.SCHEDULE_DB_HASH_KEY,
                "AttributeType": "S",
            },
            {
                "AttributeName": schedules.SCHEDULE_DB_RANGE_KEY,
                "AttributeType": "S",
            },
        ],
        KeySchema=[
            {
                "AttributeName": schedules.SCHEDULE_DB_HASH_KEY,
                "KeyType": "HASH",
            },
            {
                "AttributeName": schedules.SCHEDULE_DB_RANGE_KEY,
                "KeyType": "RANGE",
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    # Create ad sync lock table
    dynamodb_client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{AD_SYNC_LOCK_TABLE}",
        KeySchema=[{"AttributeName": "lock_key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "lock_key", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Create permission profiles table
    dynamodb_client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{permission_profiles.PERMISSION_PROFILE_TABLE_NAME}",
        KeySchema=[
            {
                "AttributeName": permission_profiles.PERMISSION_PROFILE_DB_HASH_KEY,
                "KeyType": "HASH",
            },
        ],
        AttributeDefinitions=[
            {
                "AttributeName": permission_profiles.PERMISSION_PROFILE_DB_HASH_KEY,
                "AttributeType": "S",
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Create modules table
    dynamodb_client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.modules",
        KeySchema=[
            {"AttributeName": modules.MODULES_TABLE_HASH_KEY, "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": modules.MODULES_TABLE_HASH_KEY, "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Create software stacks table
    dynamodb_client.create_table(
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
    # Create email template table
    dynamodb_client.create_table(
        TableName=f"{ENVIRONMENT_NAME}.{email_templates.EMAIL_TEMPLATE_TABLE_NAME}",
        KeySchema=[
            {
                "AttributeName": email_templates.EMAIL_TEMPLATE_DB_NAME_KEY,
                "KeyType": "HASH",
            },
        ],
        AttributeDefinitions=[
            {
                "AttributeName": email_templates.EMAIL_TEMPLATE_DB_NAME_KEY,
                "AttributeType": "S",
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    yield context

    # Clean up all the tables related to the AD Sync process after running tests
    dynamodb_client.delete_table(TableName=f"{ENVIRONMENT_NAME}.projects")
    dynamodb_client.delete_table(TableName=f"{ENVIRONMENT_NAME}.authz.role-assignments")
    dynamodb_client.delete_table(TableName=f"{ENVIRONMENT_NAME}.accounts.group-members")
    dynamodb_client.delete_table(TableName=f"{ENVIRONMENT_NAME}.accounts.groups")
    dynamodb_client.delete_table(TableName=f"{ENVIRONMENT_NAME}.accounts.users")
    dynamodb_client.delete_table(
        TableName=f"{ENVIRONMENT_NAME}.{sessions.SESSIONS_TABLE_NAME}"
    )
    dynamodb_client.delete_table(
        TableName=f"{ENVIRONMENT_NAME}.{servers.SERVER_TABLE_NAME}"
    )
    dynamodb_client.delete_table(
        TableName=f"{ENVIRONMENT_NAME}.{session_permissions.SESSION_PERMISSION_TABLE_NAME}"
    )
    dynamodb_client.delete_table(
        TableName=f"{ENVIRONMENT_NAME}.{schedules.SCHEDULE_DB_TABLE_NAME}"
    )
    dynamodb_client.delete_table(
        TableName=f"{ENVIRONMENT_NAME}.{cluster_settings.CLUSTER_SETTINGS_TABLE_NAME}"
    )
    dynamodb_client.delete_table(TableName=f"{ENVIRONMENT_NAME}.{AD_SYNC_LOCK_TABLE}")
    dynamodb_client.delete_table(
        TableName=f"{ENVIRONMENT_NAME}.{permission_profiles.PERMISSION_PROFILE_TABLE_NAME}"
    )
    dynamodb_client.delete_table(
        TableName=f"{ENVIRONMENT_NAME}.{software_stacks.SOFTWARE_STACK_TABLE_NAME}"
    )
    dynamodb_client.delete_table(TableName=f"{ENVIRONMENT_NAME}.modules")
    dynamodb_client.delete_table(
        TableName=f"{ENVIRONMENT_NAME}.{email_templates.EMAIL_TEMPLATE_TABLE_NAME}"
    )
