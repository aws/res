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

from ideasdk.utils import Utils
from ideadatamodel import exceptions, errorcodes
from ideasdk.context import SocaContext

from ideaclustermanager.app.accounts.accounts_service import AccountsService
from ideaclustermanager.app.projects.db.projects_dao import ProjectsDAO

from typing import List
from boto3.dynamodb.conditions import Key


class UserProjectsDAO:

    def __init__(self, context: SocaContext, projects_dao: ProjectsDAO, accounts_service: AccountsService, logger=None):
        self.context = context
        self.projects_dao = projects_dao
        self.accounts_service = accounts_service
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('user-projects-dao')

        self.user_projects_table = None
        self.project_groups_table = None

    def get_user_projects_table_name(self) -> str:
        return f'{self.context.cluster_name()}.projects.user-projects'

    def get_project_groups_table_name(self) -> str:
        return f'{self.context.cluster_name()}.projects.project-groups'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_user_projects_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'username',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'project_id',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'username',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'project_id',
                        'KeyType': 'RANGE'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_project_groups_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'group_name',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'project_id',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'group_name',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'project_id',
                        'KeyType': 'RANGE'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.user_projects_table = self.context.aws().dynamodb_table().Table(self.get_user_projects_table_name())
        self.project_groups_table = self.context.aws().dynamodb_table().Table(self.get_project_groups_table_name())

    def create_user_project(self, project_id: str, username: str):
        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        self.logger.info(f'added user project: {project_id}, username: {username}')
        self.user_projects_table.put_item(
            Item={
                'project_id': project_id,
                'username': username
            }
        )

    def delete_user_project(self, project_id: str, username: str):
        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        project = self.projects_dao.get_project_by_id(project_id=project_id)
        if project is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.PROJECT_NOT_FOUND,
                message=f'project: {project_id} not found.'
            )

        project_groups = set(project['ldap_groups'] if 'ldap_groups' in project else [])

        user = self.accounts_service.user_dao.get_user(
            username=username)
        if user is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_USER_NOT_FOUND,
                message=f'user: {username} not found.'
            )

        user_groups = set(user['additional_groups'] if 'additional_groups' in user else [])

        common_groups = project_groups.intersection(user_groups)
        # delete user-project relation only user's additional_groups and project's ldap_groups has no common groups.
        if len(common_groups) == 0:
            self.logger.info(
                f'deleted user project: {project_id}, username: {username}')
            self.user_projects_table.delete_item(
                Key={
                    'project_id': project_id,
                    'username': username
                }
            )
        else:
            self.logger.info(
                f'Not deleting user project: {project_id}, username: {username} as user has permissions to access project through group/s: {common_groups}')

    def ldap_group_added(self, project_id: str, group_name: str):
        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('username is required')

        self.project_groups_table.put_item(
            Item={
                'group_name': group_name,
                'project_id': project_id
            }
        )

        usernames = self.accounts_service.group_members_dao.get_usernames_in_group(group_name)
        for username in usernames:
            self.create_user_project(
                project_id=project_id,
                username=username
            )

    def ldap_group_removed(self, project_id: str, group_name: str):
        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('username is required')

        self.project_groups_table.delete_item(
            Key={
                'group_name': group_name,
                'project_id': project_id
            }
        )

        usernames = self.accounts_service.group_members_dao.get_usernames_in_group(group_name)
        for username in usernames:
            self.delete_user_project(
                project_id=project_id,
                username=username
            )

    def get_projects_by_username(self, username: str) -> List[str]:
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        result = self.user_projects_table.query(
            KeyConditionExpression=Key('username').eq(username)
        )
        user_projects = Utils.get_value_as_list('Items', result, [])

        project_ids = []
        for user_project in user_projects:
            project_ids.append(user_project['project_id'])
        return project_ids

    def get_projects_by_group_name(self, group_name: str) -> List[str]:
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')
        self.logger.debug(f'get_projects_by_group_name() - Looking for {group_name} in UserProjectsDAO/DDB')
        result = self.project_groups_table.query(
            KeyConditionExpression=Key('group_name').eq(group_name)
        )
        self.logger.debug(f'get_projects_by_group_name() - Group: {group_name} Result: {result}')
        group_projects = Utils.get_value_as_list('Items', result, [])
        self.logger.debug(f'get_projects_by_group_name() - Group: {group_name} group_projects: {group_projects}')
        project_ids = []
        for group_project in group_projects:
            project_ids.append(group_project['project_id'])
        self.logger.debug(f'get_projects_by_group_name() - Group: {group_name} group_projects: {group_projects} - Returning IDs: {project_ids}')
        return project_ids

    def group_member_added(self, group_name: str, username: str):
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        self.logger.info(f'group_member_added() - Adding {username} to {group_name} in DDB. Fetch project_id for {group_name}')

        project_ids = self.get_projects_by_group_name(group_name)
        for project_id in project_ids:
            self.create_user_project(
                project_id=project_id,
                username=username
            )

    def group_member_removed(self, group_name: str, username: str):
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        project_ids = self.get_projects_by_group_name(group_name)
        for project_id in project_ids:
            self.delete_user_project(
                project_id=project_id,
                username=username
            )

    def project_disabled(self, project_id: str):
        if Utils.are_empty(project_id):
            raise exceptions.invalid_params('project_id is required')

        project = self.projects_dao.get_project_by_id(project_id)
        ldap_groups = project['ldap_groups']

        for ldap_group in ldap_groups:
            self.ldap_group_removed(project_id=project_id, group_name=ldap_group)

    def project_enabled(self, project_id: str):
        if Utils.are_empty(project_id):
            raise exceptions.invalid_params('project_id is required')

        project = self.projects_dao.get_project_by_id(project_id)
        ldap_groups = project['ldap_groups']

        for ldap_group in ldap_groups:
            self.ldap_group_added(project_id=project_id, group_name=ldap_group)

    def is_user_in_project(self, username: str, project_id: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')

        result = self.user_projects_table.get_item(
            Key={
                'username': username,
                'project_id': project_id
            }
        )
        return Utils.get_value_as_dict('Item', result) is not None

    def has_projects_in_group(self, group_name: str) -> bool:
        query_result = self.project_groups_table.query(
            Limit=1,
            KeyConditions={
                'group_name': {
                    'AttributeValueList': [group_name],
                    'ComparisonOperator': 'EQ'
                }
            }
        )
        memberships = query_result['Items'] if 'Items' in query_result else []
        return len(memberships) > 0
