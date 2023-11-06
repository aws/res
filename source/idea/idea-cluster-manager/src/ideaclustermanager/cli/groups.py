#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from ideadatamodel import (
    exceptions,
    errorcodes,
    constants,
    GetGroupRequest,
    GetGroupResult,
    ListGroupsRequest,
    ListGroupsResult,
    ListUsersInGroupRequest,
    ListUsersInGroupResult,
    EnableGroupRequest,
    EnableGroupResult,
    DisableGroupRequest,
    DisableGroupResult,
    CreateGroupRequest,
    CreateGroupResult,
    DeleteGroupRequest,
    DeleteGroupResult,
    AddUserToGroupRequest,
    AddUserToGroupResult,
    RemoveUserFromGroupRequest,
    RemoveUserFromGroupResult
)

from ideaclustermanager.cli import build_cli_context
from ideasdk.utils import Utils
from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from ideaclustermanager.cli.cli_utils import ClusterManagerUtils

from rich.table import Table
import click
import csv


@click.group()
def groups():
    """
    group management options
    """


@groups.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--groupname', required=True, help='Group Name')
def get_group(groupname: str):
    """
    get group
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    try:
        result = context.unix_socket_client.invoke_alt(
            namespace='Accounts.GetGroup',
            payload=GetGroupRequest(
                group_name=groupname
            ),
            result_as=GetGroupResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)
        return
    context.print(Utils.to_yaml(result.group))


@groups.command(context_settings=constants.CLICK_SETTINGS)
def list_groups():
    """
    list existing groups
    """

    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    result = context.unix_socket_client.invoke_alt(
        namespace='Accounts.ListGroups',
        payload=ListGroupsRequest(),
        result_as=ListGroupsResult
    )
    group_table = Table()
    group_table.add_column("Group Name", justify="left", no_wrap=False)
    group_table.add_column("Group Type", justify="left", no_wrap=False)
    group_table.add_column("Directory Group Name", justify="left", no_wrap=False)
    group_table.add_column("GID", justify="left", no_wrap=False)
    group_table.add_column("Created On", justify="left", no_wrap=False)
    group_table.add_column("Is Enabled?", justify="left", no_wrap=False)
    for listing in result.listing:
        group_table.add_row(listing.name,
                            Utils.get_as_string(listing.group_type),
                            Utils.get_as_string(listing.ds_name),
                            Utils.get_as_string(listing.gid),
                            listing.created_on.strftime("%m/%d/%Y, %H:%M:%S"),
                            Utils.get_as_string(listing.enabled),
                            )
    context.print(group_table)


@groups.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--groupname', required=True, help='Group Name to fetch users')
def list_users(groupname: str):
    """
    list users in a group
    """

    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    result = context.unix_socket_client.invoke_alt(
        namespace='Accounts.ListUsersInGroup',
        payload=ListUsersInGroupRequest(
            group_names=[groupname]
        ),
        result_as=ListUsersInGroupResult
    )
    group_table = Table()
    group_table.add_column("User Name", justify="left", no_wrap=False)
    group_table.add_column("User Email", justify="left", no_wrap=False)
    group_table.add_column("User UID", justify="left", no_wrap=False)
    group_table.add_column("User GID", justify="left", no_wrap=False)
    group_table.add_column("Created On", justify="left", no_wrap=False)
    group_table.add_column("Is Enabled?", justify="left", no_wrap=False)
    for listing in result.listing:
        group_table.add_row(listing.username,
                            Utils.get_as_string(listing.email),
                            Utils.get_as_string(listing.uid),
                            Utils.get_as_string(listing.gid),
                            listing.created_on.strftime("%m/%d/%Y, %H:%M:%S"),
                            Utils.get_as_string(listing.enabled),
                            )
    context.print(group_table)


@groups.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--groupname', required=True, help='Group Name')
def enable_group(groupname: str):
    """
    enable a group
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    try:
        context.unix_socket_client.invoke_alt(
            namespace='Accounts.EnableGroup',
            payload=EnableGroupRequest(
                group_name=groupname
            ),
            result_as=EnableGroupResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)


@groups.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--groupname', required=True, help='Group Name')
def disable_group(groupname: str):
    """
    disable a group
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    try:
        context.unix_socket_client.invoke_alt(
            namespace='Accounts.DisableGroup',
            payload=DisableGroupRequest(
                group_name=groupname
            ),
            result_as=DisableGroupResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)


@groups.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--groupname', required=True, help='Group Name')
@click.option('--title', required=True, help='Group Title')
@click.option('--description', required=True, help='Group Description')
@click.option('--ds-name', required=True, help='Directory Service Name')
@click.option('--group-type', required=True, help='Group Type')
@click.option('--gid', required=True, help='GID')
def create_group(**kwargs):
    """
    create a new group
    """
    request = {
        'group': {
            'name': Utils.get_value_as_string('groupname', kwargs),
            'title': Utils.get_value_as_string('title', kwargs),
            'description': Utils.get_value_as_string('description', kwargs),
            'ds_name': Utils.get_value_as_string('ds_name', kwargs),
            'gid': Utils.get_value_as_int('gid', kwargs),
            'group_type': Utils.get_value_as_string('group_type', kwargs),
            'enabled': True,
        }
    }

    context = build_cli_context()
    result = context.unix_socket_client.invoke_alt(
        namespace='Accounts.CreateGroup',
        payload=CreateGroupRequest(**request),
        result_as=CreateGroupResult
    )
    context.print_json(Utils.to_json(result.group))

@groups.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--groupname', required=True, help='Groupname to DELETE')
def delete_group(groupname: str):
    """
    delete a group
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    try:
        context.unix_socket_client.invoke_alt(
            namespace='Accounts.DeleteGroup',
            payload=DeleteGroupRequest(
                group_name=groupname
            ),
            result_as=DeleteGroupResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)

@groups.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--username', required=True, multiple=True, help='Username for operation. Can be specified multiple times (-u user1 -u user2)')
@click.option('--groupname', required=True, help='Groupname to add username(s)')
def add_user_to_group(username: list[str], groupname: str):
    """
    Add username(s) to a group.
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    result = None
    try:
        result = context.unix_socket_client.invoke_alt(
            namespace='Accounts.AddUserToGroup',
            payload=AddUserToGroupRequest(
                usernames=username,
                group_name=groupname
            ),
            result_as=AddUserToGroupResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)

    # Show the groupname in summary?
    print(result)

@groups.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--username', required=True, multiple=True, help='Username for operation. Can be specified multiple times (-u user1 -u user2)')
@click.option('--groupname', required=True, help='Groupname to remove username(s)')
def remove_user_from_group(username: list[str], groupname: str):
    """
    Remove username(s) from a group.
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    result = None
    try:
        result = context.unix_socket_client.invoke_alt(
            namespace='Accounts.RemoveUserFromGroup',
            payload=RemoveUserFromGroupRequest(
                usernames=username,
                group_name=groupname
            ),
            result_as=RemoveUserFromGroupResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)

    # Show the groupname in summary
    print(result)
