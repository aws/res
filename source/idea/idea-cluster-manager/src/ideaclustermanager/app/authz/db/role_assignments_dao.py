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
from ideadatamodel import exceptions, constants, RoleAssignment
from ideasdk.context import SocaContext

from typing import List, Optional, Dict
from boto3.dynamodb.conditions import Attr, Key

GSI_RESOURCE_KEY = 'resource-key-index'

class RoleAssignmentsDAO:

    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('role-assignments-dao')

        self.role_assignments_table = None

    def get_role_assignments_table_name(self) -> str:
        return f'{self.context.cluster_name()}.authz.role-assignments'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_role_assignments_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'actor_key',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'resource_key',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'actor_key',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'resource_key',
                        'KeyType': 'RANGE'
                    }
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': GSI_RESOURCE_KEY,
                        'KeySchema': [
                            {
                                'AttributeName': 'resource_key',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'actor_key',
                                'KeyType': 'RANGE'
                            },
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.role_assignments_table = self.context.aws().dynamodb_table().Table(self.get_role_assignments_table_name())

        # ToDo: Add GSI for role_id if it doesn't exist
    
    @staticmethod
    def convert_from_db(role_assignment: Dict) -> RoleAssignment:
        keys = [
            'actor_key',
            'resource_key',
            'actor_id',
            'actor_type',
            'resource_id',
            'resource_type',
            'role_id',
        ]
        return RoleAssignment(**{k: role_assignment.get(k, "") for k in keys})

    @staticmethod
    def convert_to_db(role_assignment: RoleAssignment) -> Dict:
        keys = [
            'actor_key',
            'resource_key',
            'actor_id',
            'actor_type',
            'resource_id',
            'resource_type',
            'role_id',
        ]
        return {k: getattr(role_assignment, k) for k in keys}

    def put_role_assignment(self, actor_key: str, resource_key: str, role_id: str):
        # Perform validations on the incoming actor/resource types
        if Utils.is_empty(actor_key):
            raise exceptions.invalid_params('actor_key is required')
        if Utils.is_empty(resource_key):
            raise exceptions.invalid_params('resource_key is required')
        if Utils.is_empty(role_id):
            raise exceptions.invalid_params('role_id is required')
        
        actor_key_split = actor_key.split(':')
        actor_type = actor_key_split[1] if len(actor_key_split) == 2 else ""
        if actor_type not in constants.VALID_ROLE_ASSIGNMENT_ACTOR_TYPES:
            raise exceptions.invalid_params('actor type is not recognized')
        
        resource_key_split = resource_key.split(':')
        resource_type = resource_key_split[1] if len(resource_key_split) == 2 else ""
        if resource_type not in constants.VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES:
            raise exceptions.invalid_params('resource type is not recognized')

        # Creates or updates the record in DDB
        self.role_assignments_table.put_item(
                Item={
                    'actor_key': actor_key,
                    'resource_key': resource_key,
                    'actor_id': actor_key_split[0],
                    'resource_id': resource_key_split[0],
                    'actor_type': actor_type,
                    'resource_type': resource_type,
                    'role_id': role_id,
                }
            )
        
        self.logger.info(f'assigned actor {actor_key} with role {role_id} to resource {resource_key}')


    def delete_role_assignment(self, actor_key: str, resource_key: str):
        # Perform validations on the incoming actor/resource types
        if Utils.is_empty(actor_key):
            raise exceptions.invalid_params('actor_key is required')
        if Utils.is_empty(resource_key):
            raise exceptions.invalid_params('resource_key is required')

        self.role_assignments_table.delete_item(
            Key={
                'actor_key': actor_key,
                'resource_key': resource_key
            }
        )
        self.logger.info(f'deleted role assignment of actor {actor_key} to resource {resource_key}')

    def get_role_assignment(self, actor_key: str, resource_key: str) -> Optional[RoleAssignment]:
        # Perform validations on the incoming actor/resource types
        if Utils.is_empty(actor_key):
            raise exceptions.invalid_params('actor_key is required')
        if Utils.is_empty(resource_key):
            raise exceptions.invalid_params('resource_key is required')

        result = self.role_assignments_table.get_item(
            Key={
                'actor_key': actor_key,
                'resource_key': resource_key
            }
        )

        return self.convert_from_db(Utils.get_value_as_dict('Item', result)) if Utils.get_value_as_dict('Item', result) else None
    
    def list_role_assignments(self, actor_key: str = "", resource_key: str = "", role_id: str = None) -> List[RoleAssignment]:
        self.logger.info(f'list role assignments for {resource_key if Utils.is_empty(actor_key) else actor_key}')
        
        role_assignments = []

        if not Utils.is_empty(actor_key) and not Utils.is_empty(resource_key):
            role_assignment = self.get_role_assignment(actor_key, resource_key)
            if role_assignment is not None: role_assignments.append(role_assignment)
        else:
            pagination_key = None
            result = None
            while True:
                if not Utils.is_empty(actor_key):
                    query_params = { 'KeyConditionExpression': Key('actor_key').eq(actor_key) }
                    if pagination_key: query_params.ExclusiveStartKey = pagination_key
                    result = self.role_assignments_table.query(**query_params)
                elif not Utils.is_empty(resource_key):
                    query_params = { 'KeyConditionExpression': Key('resource_key').eq(resource_key), 'IndexName': GSI_RESOURCE_KEY }
                    if pagination_key: query_params.ExclusiveStartKey = pagination_key
                    result = self.role_assignments_table.query(**query_params)
                elif not Utils.is_empty(role_id):
                    # This helps list all assignments for a role in the system
                    # ToDo: update table to use a new GSI for role_id
                    result = self.role_assignments_table.scan(FilterExpression=Attr("role_id").eq(role_id))
            
                query_output = Utils.get_value_as_list('Items', result, [])
                for item in query_output:
                    role_assignments.append(self.convert_from_db(item))
                pagination_key = Utils.get_any_value('LastEvaluatedKey', result)
                if pagination_key is None:
                    break
        
        return role_assignments
    
    def list_projects_for_role(self, role_id: str) -> List[str]:
        role_assignments = self.list_role_assignments(role_id=role_id)
        self.logger.info(f'list projects for role {role_id}')
        project_ids = [role_assignment.resource_id for role_assignment in role_assignments if role_assignment.resource_type == "project"]

        return project_ids
    
    def get_projects_for_user(self, username: str, groups: List[str]) -> List[str]:
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        role_assignments = self.list_role_assignments(actor_key=f'{username}:user')
        project_ids = [role_assignment.resource_id for role_assignment in role_assignments if role_assignment.resource_type=="project"]

        for group_name in groups:
            role_assignments = self.list_role_assignments(actor_key=f'{group_name}:group')
            project_ids.extend([role_assignment.resource_id for role_assignment in role_assignments if role_assignment.resource_type=="project"])

        # dedup the results and send it
        return list(set(project_ids))

    def get_all_users_for_project(self, project_id: str) -> List[str]:
        role_assignments = self.list_role_assignments(ListRoleAssignmentsRequest(resource_key=f'{project_id}:project')).items
        user_ids = [role_assignment.actor_id for role_assignment in role_assignments if role_assignment.actor_type=="user"]
        group_ids = [role_assignment.actor_id for role_assignment in role_assignments if role_assignment.actor_type=="group"]

        # Add all users grom group in user_ids
        for group_id in group_ids:
            user_ids.extend(self.get_users_by_group_name(group_id))

        return user_ids
    

    def get_projects_by_group_name(self, group_name: str) -> List[str]:
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        role_assignments = self.list_role_assignments(actor_key=f'{group_name}:group')
        project_ids = [role_assignment.resource_id for role_assignment in role_assignments if role_assignment.resource_type=="project"]

        return project_ids