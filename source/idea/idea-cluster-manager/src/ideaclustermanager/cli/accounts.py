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
    GetUserResult,
    GetUserRequest,
    ListUsersRequest,
    ListUsersResult,
    CreateUserRequest,
    CreateUserResult,
    EnableUserRequest,
    EnableUserResult,
    DisableUserRequest,
    DisableUserResult,
    User,
    ModifyUserRequest,
    ModifyUserResult,
    DeleteUserRequest,
    DeleteUserResult,
)
from ideaclustermanager.cli import build_cli_context
from ideasdk.utils import Utils
from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from ideaclustermanager.cli.cli_utils import ClusterManagerUtils

from rich.table import Table
import click
import csv


@click.group()
def accounts():
    """
    account management options
    """


@accounts.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--username', required=True, help='Username')
def get_user(username: str):
    """
    get user
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    try:
        result = context.unix_socket_client.invoke_alt(
            namespace='Accounts.GetUser',
            payload=GetUserRequest(
                username=username
            ),
            result_as=GetUserResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)
        return
    context.print(Utils.to_yaml(result.user))


@accounts.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--username', required=True, help='Username')
def enable_user(username: str):
    """
    enable user
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    try:
        context.unix_socket_client.invoke_alt(
            namespace='Accounts.EnableUser',
            payload=EnableUserRequest(
                username=username
            ),
            result_as=EnableUserResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)


@accounts.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--username', required=True, help='Username')
def disable_user(username: str):
    """
    disable user
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    try:
        context.unix_socket_client.invoke_alt(
            namespace='Accounts.DisableUser',
            payload=DisableUserRequest(
                username=username
            ),
            result_as=DisableUserResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)


@accounts.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--username', required=True, help='Username')
def delete_user(username: str):
    """
    delete user
    """
    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    try:
        context.unix_socket_client.invoke_alt(
            namespace='Accounts.DeleteUser',
            payload=DeleteUserRequest(
                username=username
            ),
            result_as=DeleteUserResult
        )
    except exceptions.SocaException as e:
        context.error(e.message)


@accounts.command(context_settings=constants.CLICK_SETTINGS)
def list_users():
    """
    list existing users
    """

    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()
    result = context.unix_socket_client.invoke_alt(
        namespace='Accounts.ListUsers',
        payload=ListUsersRequest(),
        result_as=ListUsersResult
    )
    user_table = Table()
    user_table.add_column("Username", justify="left", no_wrap=False)
    user_table.add_column("UID", justify="left", no_wrap=False)
    user_table.add_column("GID", justify="left", no_wrap=False)
    user_table.add_column("Email", justify="left", no_wrap=False)
    user_table.add_column("Is Admin?", justify="left", no_wrap=False)
    user_table.add_column("Status", justify="left", no_wrap=False)
    user_table.add_column("Group", justify="left", style="green", no_wrap=False)
    user_table.add_column("Created On", justify="left", style="red", no_wrap=False)
    for listing in result.listing:
        user_table.add_row(listing.username, Utils.get_as_string(listing.uid), Utils.get_as_string(listing.gid),
                           listing.email, Utils.get_as_string(listing.sudo), Utils.get_as_string(listing.status),
                           listing.group_name, listing.created_on.strftime("%m/%d/%Y, %H:%M:%S"))
    context.print(user_table)


@accounts.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--username', required=True, help='The Username')
@click.option('--email', required=True, help='Email Address')
@click.option('--password', help='Password (Required when setting email-verified)')
@click.option('--uid', help='UID')
@click.option('--gid', help='GID')
@click.option('--email-verified', is_flag=True, help='Indicate if the email address is verified. Invitation email will not be sent.')
@click.option('--sudo', is_flag=True, help='Indicate if user is an admin user with sudo access')
def create_user(**kwargs):
    """
    create new user account
    """
    request = {
        'user': {
            'username': Utils.get_value_as_string('username', kwargs),
            'email': Utils.get_value_as_string('email', kwargs),
            'sudo': Utils.get_value_as_bool('sudo', kwargs, False),
            'password': Utils.get_value_as_string('password', kwargs),
            'uid': Utils.get_value_as_int('uid', kwargs),
            'gid': Utils.get_value_as_int('gid', kwargs)
        },
        'email_verified': Utils.get_value_as_bool('email_verified', kwargs, False)
    }

    context = build_cli_context()
    result = context.unix_socket_client.invoke_alt(
        namespace='Accounts.CreateUser',
        payload=CreateUserRequest(**request),
        result_as=CreateUserResult
    )
    context.print_json(Utils.to_json(result.user))


@accounts.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--username', required=True, help='The Username')
@click.option('--email', help='Email Address')
@click.option('--uid', help='UID')
@click.option('--gid', help='GID')
@click.option('--sudo', help='Add or remove sudo access. Allowed values [yes/no/true/false/0/1]')
@click.option('--login-shell', help='Login shell for the user')
def modify_user(**kwargs):
    """
    update an existing user account

    \b
    supported fields:
    * uid
    * gid
    * email
    * sudo
    """
    request = {
        'user': {
            'username': Utils.get_value_as_string('username', kwargs),
            'email': Utils.get_value_as_string('email', kwargs),
            'sudo': Utils.get_value_as_bool('sudo', kwargs),
            'uid': Utils.get_value_as_int('uid', kwargs),
            'gid': Utils.get_value_as_int('gid', kwargs),
            'login_shell': Utils.get_value_as_string('login_shell', kwargs)
        }
    }

    context = build_cli_context()
    result = context.unix_socket_client.invoke_alt(
        namespace='Accounts.ModifyUser',
        payload=ModifyUserRequest(**request),
        result_as=ModifyUserResult
    )
    context.print_json(Utils.to_json(result.user))


@accounts.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--path-to-csv', help='path to the csv file')
@click.option('--force', is_flag=True, help='skips confirmation prompts')
@click.option('--generate-template', is_flag=True, help='generates a csv template compatible with this command')
@click.option('--template-path', help='location to generate template.csv file')
def batch_create_users(path_to_csv: str, force: bool, generate_template: bool, template_path: str):
    """
    creates users from csv file
    """

    context = ClusterManagerUtils.get_soca_cli_context_cluster_manager()

    if generate_template:
        # generate template
        if template_path and Utils.is_dir(template_path):
            csv_file = ClusterManagerUtils.generate_template(template_path)
            context.info(f'The generated template file is located at {csv_file}')
        else:
            context.error('Path missing or incorrect; please provide a path to where to generate the "users_file_template.csv"')
        return

    ClusterManagerUtils.check_if_csv_file(path_to_csv, context)

    user_table = ClusterManagerUtils.build_confirm_user_table()
    status_table = ClusterManagerUtils.build_create_user_status_table()

    new_users = []
    new_usernames = []
    csv_validations = []
    csv_contains_error = False
    csv_contains_duplicate = False
    with open(path_to_csv, 'r', encoding="utf-8") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        fieldnames = csv_reader.fieldnames

        # check for valid csv file
        ClusterManagerUtils.check_has_valid_csv_headers(fieldnames, context)

        for row in csv_reader:
            new_username = AuthUtils.sanitize_username(Utils.get_value_as_string('Username', row))
            valid_username_response = ''
            try:
                ClusterManagerUtils.check_valid_username(new_username)
            except exceptions.SocaException as e:
                if e.error_code == errorcodes.INVALID_PARAMS:
                    valid_username_response = e.message
                else:
                    raise e
            if not Utils.is_empty(valid_username_response):
                csv_contains_error = True
            new_email = Utils.get_value_as_string('Email', row).strip().lower()

            valid_email_response = ''
            try:
                ClusterManagerUtils.check_valid_email(new_email)
            except exceptions.SocaException as e:
                if e.error_code == errorcodes.INVALID_PARAMS:
                    valid_email_response = e.message
                else:
                    raise e
            if not Utils.is_empty(valid_email_response):
                csv_contains_error = True
            new_is_admin = Utils.get_value_as_bool('Is Admin?', row, default=False)

            new_usernames.append(new_username)
            csv_validations.append((new_username, new_email, Utils.get_as_string(new_is_admin, default='False'), valid_username_response, valid_email_response))

            user_table.add_row(new_username, new_email, Utils.get_as_string(new_is_admin))
            new_users.append(User(username=new_username, email=new_email, sudo=new_is_admin))

    duplicate_users_in_csv = ClusterManagerUtils.check_duplicate_users_in_csv(new_usernames)
    if len(duplicate_users_in_csv) > 0:
        table = Table()
        table.add_column('Username', justify='left', no_wrap=False)
        for user in duplicate_users_in_csv:
            table.add_row(user)
        context.print(table)
        context.error('These users are repeated in the csv file; please ensure all usernames are unique in the csv file and try again.')
        return

    duplicate_users = ClusterManagerUtils.check_duplicate_users(new_usernames, context)
    if len(duplicate_users) > 0:
        csv_contains_duplicate = True

    if csv_contains_error or csv_contains_duplicate:
        for item in csv_validations:
            is_duplicate = item[0] in duplicate_users

            if not Utils.is_empty(item[3]) and not Utils.is_empty(item[4]):
                status_table.add_row(item[0], item[1], item[2], "FAILED", f'{item[3]} AND {item[4]}', style='red')
            elif not Utils.is_empty(item[3]):
                status_table.add_row(item[0], item[1], item[2], "FAILED", f'{item[3]}', style='red')
            elif not Utils.is_empty(item[4]) and is_duplicate:
                status_table.add_row(item[0], item[1], item[2], "FAILED", f'user already exists; please remove them from the csv and try again AND {item[4]}', style='red')
            elif not Utils.is_empty(item[4]):
                status_table.add_row(item[0], item[1], item[2], "FAILED", f'{item[4]}', style='red')
            elif is_duplicate:
                status_table.add_row(item[0], item[1], item[2], "FAILED", 'user already exists; please remove them from the csv and try again', style='red')
            else:
                status_table.add_row(item[0], item[1], item[2], "ABORTED", 'csv file contains errors', style='bright_black')
        context.print(status_table)
        raise SystemExit(1)

    if not force:
        context.print(user_table)
        continue_deployment = context.prompt(f'Are you sure you want to add these users?')
        if not continue_deployment:
            for new_user in new_users:
                status_table.add_row(new_user.username, new_user.email, Utils.get_as_string(new_user.sudo, default='False'), 'ABORTED', 'Adding user Aborted!')
            context.print(status_table)
            raise SystemExit(1)

    create_users_response = ClusterManagerUtils.create_users(new_users, context)
    ClusterManagerUtils.print_create_user_status(create_users_response, context)
