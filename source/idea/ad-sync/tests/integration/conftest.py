#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
import time

import adsync.main as main
import boto3
import ldap  # noqa
import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideatestutils.dynamodb.dynamodb_local import DynamoDBLocal
from res.clients.ldap_client.active_directory_client import ActiveDirectoryClient
from res.resources import accounts, cluster_settings
from res.utils import table_utils

logger = logging.getLogger(__name__)

# initialize monkey patch globally, so that it can be used inside session scoped context fixtures
# this allows session scoped monkey patches to be applicable across all unit tests
# monkeypatch.undo() is called at the end of context fixture
monkeypatch = MonkeyPatch()
monkeypatch.setattr(
    ActiveDirectoryClient,
    "fetch_service_account_credentials",
    lambda x: ("ServiceAccount", "RESPassword1."),
)
monkeypatch.setattr(
    ActiveDirectoryClient,
    "ldap_service_account_bind",
    "cn=ServiceAccount,dc=corp,dc=res,dc=com",
)
monkeypatch.setattr(accounts, "_get_uid_and_gid_for_username", lambda x: (1000, 1000))
monkeypatch.setattr(accounts, "_get_gid_for_group", lambda x: 1000)
monkeypatch.setattr(main, "_start_sssd", lambda x: None)


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
    os.environ["environment_name"] = "res-test"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    # Override the endpoint for boto3.resource("dynamodb") to use DynamoDB local
    dynamodb = boto3.resource("dynamodb", endpoint_url="http://localhost:9000")

    def _resource(service_name: str):
        if service_name == "dynamodb":
            return dynamodb

    monkeypatch.setattr(boto3, "resource", _resource)

    # Create the required tables in DynamoDB local
    dynamodb_client = boto3.client("dynamodb", endpoint_url="http://localhost:9000")
    dynamodb_client.create_table(
        TableName=f"{os.environ['environment_name']}.accounts.users",
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
        TableName=f"{os.environ['environment_name']}.accounts.groups",
        AttributeDefinitions=[{"AttributeName": "group_name", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "group_name", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )

    dynamodb_client.create_table(
        TableName=f"{os.environ['environment_name']}.accounts.group-members",
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
        TableName=f"{os.environ['environment_name']}.{cluster_settings.CLUSTER_SETTINGS_TABLE_NAME}",
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
    add_directory_service_settings()

    dynamodb_client.create_table(
        TableName=f"{os.environ['environment_name']}.authz.role-assignments",
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

    yield context

    # Clean up the required tables related to the AD Sync process after running tests
    dynamodb_client.delete_table(
        TableName=f"{os.environ['environment_name']}.accounts.group-members"
    )
    dynamodb_client.delete_table(
        TableName=f"{os.environ['environment_name']}.accounts.groups"
    )
    dynamodb_client.delete_table(
        TableName=f"{os.environ['environment_name']}.accounts.users"
    )
    dynamodb_client.delete_table(
        TableName=f"{os.environ['environment_name']}.{cluster_settings.CLUSTER_SETTINGS_TABLE_NAME}"
    )
    dynamodb_client.delete_table(
        TableName=f"{os.environ['environment_name']}.authz.role-assignments"
    )


def add_directory_service_settings():
    "Add all the AD configuration to the cluster settings table"
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.ldap_connection_uri",
            "value": "ldap://corp.res.com",
        },
    )
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.name",
            "value": "corp.res.com",
        },
    )
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.users_filter",
            "value": "(sAMAccountName=*)",
        },
    )
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.groups.ou",
            "value": "OU=Users,OU=RES,OU=CORP,DC=corp,DC=res,DC=com",
        },
    )
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.groups_filter",
            "value": "(sAMAccountName=*)",
        },
    )
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.users.ou",
            "value": "OU=Users,OU=RES,OU=CORP,DC=corp,DC=res,DC=com",
        },
    )
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.sudoers.group_name",
            "value": "RESAdministrators",
        },
    )
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.ldap_base",
            "value": "dc=corp,dc=res,dc=com",
        },
    )
    table_utils.create_item(
        cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
        item={
            "key": "directoryservice.sssd.ldap_id_mapping",
            "value": "true",
        },
    )


class LdapHelper:
    def __init__(self):
        self.ldap_client = ActiveDirectoryClient(logger)

    def ldap_search(self, base, filters):
        "Perform an ldap search at the base with given filters."
        result = self.ldap_client.simple_paginated_search(base=base, filterstr=filters)
        result = result.get("result", [])
        if len(result) == 0:
            return None

        return (
            result[0][0],
            {k: v[0].decode("utf-8") for k, v in result[0][1].items()},
        )

    def add_ldap_user(self, username, ou=None):
        "Add a new user with given username to the LDAP server under the provided or default OU"
        ou = ou or self.ldap_client.options.users_ou
        dn = f"cn={username},ou=users,ou=res,ou=corp,dc=corp,dc=res,dc=com"
        user_ldif = [
            ("objectClass", [b"user"]),
            ("cn", [username.encode("utf-8")]),
            ("sAMAccountName", [username.encode("utf-8")]),
            ("userPrincipalName", [f"{username}@corp.res.com".encode("utf-8")]),
            ("uidNumber", [b"1011"]),
            ("gidNumber", [b"1006"]),
            ("unixHomeDirectory", [f"/home/{username}".encode("utf-8")]),
            ("loginShell", [b"/bin/bash"]),
        ]
        return self.ldap_client.add_s(dn, user_ldif)

    def delete_ldap_user(self, username, ou=None):
        "Find the user by username and deletes it from the LDAP server"
        dn, _ = self.find_ldap_user(username, ou)
        self.ldap_client.delete_s(dn)

    def find_ldap_user(self, username, base=None):
        "Finds a user in LDAP by the username."
        base = base or self.ldap_client.options.ldap_base
        filters = f"(&(objectClass=user)(cn={username}))"
        return self.ldap_search(base, filters)

    def add_ldap_group(self, groupname, ou=None):
        "Adds an ldap group with the given groupname to the optional OU or default group OU"
        ou = ou or self.ldap_client.options.groups_ou
        dn = f"cn={groupname},ou=users,ou=res,ou=corp,dc=corp,dc=res,dc=com"
        group_ldif = [
            ("objectClass", [b"group"]),
            ("cn", [groupname.encode("utf-8")]),
            ("description", [f"res test group: {groupname}".encode("utf-8")]),
            ("sAMAccountName", [groupname.encode("utf-8")]),
            ("gidNumber", [b"1006"]),
        ]
        return self.ldap_client.add_s(dn, group_ldif)

    def find_ldap_group(self, groupname, base=None):
        "Finds a user in LDAP by the username."
        base = base or self.ldap_client.options.groups_ou
        filters = f"(&(objectClass=group)(cn={groupname}))"
        return self.ldap_search(base, filters)

    def delete_ldap_group(self, groupname, ou=None):
        "Takes a groupname and optional OU and deletes the group."
        dn, _ = self.find_ldap_group(groupname, ou)
        self.ldap_client.delete_s(dn)

    def create_ou(self, ou_dn: str):
        "Takes the distinguished name for an OU and creates it."
        cn = ou_dn.split(",")[0].split("=")[1]
        ou_ldif = [
            ("objectClass", [b"organizationalUnit"]),
            ("cn", [cn.encode("utf-8")]),
            ("description", [f"OU {cn}".encode("utf-8")]),
        ]
        return self.ldap_client.add_s(ou_dn, ou_ldif)

    def delete_ou(self, ou_dn: str):
        "Takes the distinguished name for an OU and deletes it."
        self.ldap_client.delete_s(ou_dn)

    def add_user_to_group(self, groupname, username, group_ou=None, user_ou=None):
        "Adds a user to an LDAP group."
        group_dn, _ = self.find_ldap_group(groupname, group_ou)
        user_dn, _ = self.find_ldap_user(username, user_ou)
        group_ldif = [(ldap.MOD_ADD, "member", [user_dn.encode("utf-8")])]
        self.ldap_client.modify_s(group_dn, group_ldif)

    def remove_user_from_group(self, groupname, username, group_ou=None, user_ou=None):
        "Removes a user to an LDAP group."
        group_dn, _ = self.find_ldap_group(groupname, group_ou)
        user_dn, _ = self.find_ldap_user(username, user_ou)
        group_ldif = [(ldap.MOD_DELETE, "member", [user_dn.encode("utf-8")])]
        self.ldap_client.modify_s(group_dn, group_ldif)


@pytest.fixture
def ldap_helper():
    return LdapHelper()


def pytest_addoption(parser):
    parser.addoption("--module", action="store")
    parser.addoption("--environment-name", action="store")
    parser.addoption("--aws-region", action="store")
