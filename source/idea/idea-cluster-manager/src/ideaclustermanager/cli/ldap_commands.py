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
    constants,
    SocaFilter,
    exceptions
)

from ideaclustermanager.app.accounts.ldapclient.ldap_client_factory import build_ldap_client
from ideaclustermanager.cli import build_cli_context

from ideasdk.utils import Utils
from ideasdk.context import SocaCliContext

from typing import Dict
import click


@click.group('ldap')
def ldap_commands():
    """
    ldap utilities
    """


@ldap_commands.command('search-users', context_settings=constants.CLICK_SETTINGS)
@click.option('-q', '--query', help="search query (substring of username)")
def search_users(query: str):
    """
    search for users in directory service using ldap
    """

    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)
    ldap_client = build_ldap_client(context)

    users, _ = ldap_client.search_users(username_filter=SocaFilter(
        like=query
    ))
    context.print_json(users)


@ldap_commands.command('search-groups', context_settings=constants.CLICK_SETTINGS)
@click.option('-q', '--query', help="search query (substring of group name)")
def search_groups(query: str):
    """
    search for groups in directory service using ldap
    """

    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)
    ldap_client = build_ldap_client(context)

    groups, _ = ldap_client.search_groups(group_name_filter=SocaFilter(
        like=query
    ))
    context.print_json(groups)


@ldap_commands.command('delete-user', context_settings=constants.CLICK_SETTINGS)
@click.option('-u', '--username', required=True, multiple=True, help="username of the user to be deleted. accepts multiple inputs eg. -u user1 -u user2")
def delete_user(username):
    """
    delete user from directory service
    """

    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)
    ldap_client = build_ldap_client(context)

    for user in username:
        ldap_client.delete_user(username=user)


@ldap_commands.command('delete-group', context_settings=constants.CLICK_SETTINGS)
@click.option('-g', '--group', required=True, multiple=True, help="name of the group to be deleted. accepts multiple inputs eg. -g group1 -g group2")
def delete_group(group):
    """
    delete group from directory service
    """

    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)
    ldap_client = build_ldap_client(context)

    for group_name in group:
        ldap_client.delete_group(group_name=group_name)


@ldap_commands.command('show-credentials', context_settings=constants.CLICK_SETTINGS)
@click.option('--username', is_flag=True, help="Print username")
@click.option('--password', is_flag=True, help="Print password")
def show_credentials(username: bool, password: bool):
    """
    print service account credentials
    """

    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)

    if username:
        print(context.config().get_secret('directoryservice.root_username_secret_arn'), end='')
    if password:
        print(context.config().get_secret('directoryservice.root_password_secret_arn'), end='')


def _send_task(context: SocaCliContext, task_name: str, payload: Dict, message_group_id: str, message_dedupe_id: str = None):
    task_queue_url = context.config().get_string('cluster-manager.task_queue_url', required=True)
    task_message = {
        'name': task_name,
        'payload': payload
    }

    if Utils.is_empty(message_dedupe_id):
        message_dedupe_id = Utils.uuid()

    context.info(f'send task: {task_name}, message group id: {message_group_id}, DedupeId: {message_dedupe_id}')
    context.aws().sqs().send_message(
        QueueUrl=task_queue_url,
        MessageBody=Utils.to_json(task_message),
        MessageDeduplicationId=Utils.uuid(),
        MessageGroupId=message_group_id
    )


@ldap_commands.command('sync-from-ad', context_settings=constants.CLICK_SETTINGS)
def sync_from_ad():
    """
    sync users and groups from ad
    """
    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)
    context.print('syncing from AD...')
    _send_task(
        context=context,
        task_name='adsync.sync-from-ad',
        payload={},
        message_group_id='adsync.sync-from-ad'
    )
    context.print('sync task submitted')


@ldap_commands.command('sync-user', context_settings=constants.CLICK_SETTINGS)
@click.option('-u', '--username', required=True, multiple=True, help="username of the user to be synced. accepts multiple inputs eg. -u user1 -u user2")
def sync_user(username):
    """
    sync user account from db to directory service
    """
    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)
    for user in username:
        _send_task(
            context=context,
            task_name='accounts.sync-user',
            payload={
                'username': user
            },
            message_group_id=user
        )


@ldap_commands.command('sync-group', context_settings=constants.CLICK_SETTINGS)
@click.option('-g', '--group', required=True, multiple=True, help="name of the group to be synced. accepts multiple inputs eg. -g group1 -g group2")
def sync_group(group):
    """
    sync group from db to directory service
    """
    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)
    for group_name in group:
        _send_task(
            context=context,
            task_name='accounts.sync-group',
            payload={
                'group_name': group_name
            },
            message_group_id=group_name
        )


@ldap_commands.command('create-service-account', context_settings=constants.CLICK_SETTINGS)
@click.option('-u', '--username', required=True, help='username of the service account')
@click.option('-p', '--password', required=True, help='password of the service account')
def create_service_account(username: str, password: str):
    """
    create a service account with administrator access

    only supported for active directory
    """
    context = build_cli_context(cluster_config=True, enable_aws_client_provider=True, enable_aws_util=True)
    ds_provider = context.config().get_string('directoryservice.provider', required=True)
    if ds_provider == constants.DIRECTORYSERVICE_OPENLDAP:
        context.error('service account creation is not supported for OpenLDAP')
        raise SystemExit(1)

    ldap_client = build_ldap_client(context)
    with context.spinner(f'creating service account for username: {username} ...'):
        account = ldap_client.create_service_account(username=username, password=password)
    context.success('service account created successfully: ')
    context.print_json(account)
