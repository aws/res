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
from ideadatamodel import exceptions, Role, SocaPaginator, ProjectPermissions, VDIPermissions, SocaFilter, SocaListingPayload
from ideasdk.context import SocaContext

from typing import List, Optional, Dict
from boto3.dynamodb.conditions import Attr

class RolesDAO:

    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('roles-dao')

        self.roles_table = None

    def get_roles_table_name(self) -> str:
        return f'{self.context.cluster_name()}.authz.roles'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_roles_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'role_id',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'role_id',
                        'KeyType': 'HASH'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.roles_table = self.context.aws().dynamodb_table().Table(self.get_roles_table_name())
    
    @staticmethod
    def convert_from_db(role: Dict) -> Role:
        """
        convert db object to role.
        :param role:
        :return: Role
        """

        keys = [
            'role_id',
            'name',
            'description',
        ]
        converted_role = Role(**{k: role.get(k, "") for k in keys})

        db_project_permissions = Utils.get_value_as_dict('projects', role)
        if db_project_permissions is not None:
            converted_role.projects = ProjectPermissions()
            converted_role.projects.update_personnel = Utils.get_value_as_bool('update_personnel', db_project_permissions)
            converted_role.projects.update_status = Utils.get_value_as_bool('update_status', db_project_permissions)
        
        db_vdi_permissions = Utils.get_value_as_dict('vdis', role)
        if db_vdi_permissions is not None:
            converted_role.vdis = VDIPermissions()
            converted_role.vdis.create_sessions = Utils.get_value_as_bool('create_sessions', db_vdi_permissions)
            converted_role.vdis.create_terminate_others_sessions = Utils.get_value_as_bool('create_terminate_others_sessions', db_vdi_permissions)

        converted_role.created_on = Utils.get_value_as_int('created_on', role, 0)
        converted_role.updated_on = Utils.get_value_as_int('updated_on', role, 0)

        return converted_role

    @staticmethod
    def convert_to_db(role: Role) -> Dict:
        """
        convert role to db object.
        None values will not replace existing values
        :param role:
        :return: Dict
        """

        keys = [
            'role_id',
            'name',
            'description',
        ]
        db_role = {k: getattr(role, k) for k in keys}

        if role.projects is not None:
            db_role['projects'] = {}
            if role.projects.update_personnel is not None: db_role['projects']['update_personnel'] = role.projects.update_personnel
            if role.projects.update_status is not None: db_role['projects']['update_status'] = role.projects.update_status
        
        if role.vdis is not None:
            db_role['vdis'] = {}
            if role.vdis.create_sessions is not None: db_role['vdis']['create_sessions'] = role.vdis.create_sessions
            if role.vdis.create_terminate_others_sessions is not None: db_role['vdis']['create_terminate_others_sessions'] = role.vdis.create_terminate_others_sessions
        
        return db_role
    
    def get_role(self, role_id: str) -> Optional[Dict]:

        if Utils.is_empty(role_id):
            raise exceptions.invalid_params('role_id is required')
        
        self.logger.info(f'get role {role_id}')

        result = self.roles_table.get_item(
            Key={
                'role_id': role_id
            }
        )
        return Utils.get_value_as_dict('Item', result)

    def list_roles(self, include_permissions: bool, cursor: str, filters: List[SocaFilter] ) -> SocaListingPayload:
        self.logger.info(f'list roles')

        scan_request = {}

        last_evaluated_key = None
        if Utils.is_not_empty(cursor):
            last_evaluated_key = Utils.from_json(Utils.base64_decode(cursor))
        if last_evaluated_key is not None:
            scan_request['LastEvaluatedKey'] = last_evaluated_key
        
        scan_filter = None
        if Utils.is_not_empty(filters):
            scan_filter = {}
            for filter_ in filters:
                if filter_.eq is not None:
                    scan_filter[filter_.key] = {
                        'AttributeValueList': [filter_.eq],
                        'ComparisonOperator': 'EQ'
                    }
                if filter_.like is not None:
                    scan_filter[filter_.key] = {
                        'AttributeValueList': [filter_.like],
                        'ComparisonOperator': 'CONTAINS'
                    }
        if scan_filter is not None:
            scan_request['ScanFilter'] = scan_filter

        scan_result = self.roles_table.scan(**scan_request)

        db_roles = Utils.get_value_as_list('Items', scan_result, [])
        roles = []
        for db_role in db_roles:
            role = self.convert_from_db(db_role)
            if not include_permissions:
                # Don't send permissions for any resource collections
                delattr(role, 'projects')
            roles.append(role)
        
        response_cursor = None
        last_evaluated_key = Utils.get_any_value('LastEvaluatedKey', scan_result)
        if last_evaluated_key is not None:
            response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_key))

        return SocaListingPayload(
            listing=roles,
            paginator=SocaPaginator(
                cursor=response_cursor
            )
        )
    
    def create_role(self, role: Dict) -> Dict:
        self.logger.info(f'create role')

        created_role = {
            **role,
            'created_on': Utils.current_time_ms(),
            'updated_on': Utils.current_time_ms()
        }

        self.roles_table.put_item(
            Item=created_role
        )

        return created_role
    
    def delete_role(self, role_id: str):
        self.logger.info(f'delete role {role_id}')

        self.roles_table.delete_item(
            Key={
                'role_id': role_id
            }
        )
    
    def update_role(self, role: Dict) -> Dict:
        role_id = Utils.get_value_as_string('role_id', role)
        self.logger.info(f'update role {role_id}')

        if Utils.is_empty(role_id):
            raise exceptions.invalid_params('role_id is required')

        role['updated_on'] = Utils.current_time_ms()

        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in role.items():
            if key in ('role_id', 'created_on'):
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self.roles_table.update_item(
            Key={
                'role_id': role_id
            },
            ConditionExpression=Attr('role_id').eq(role_id),
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW'
        )

        updated_role = result['Attributes']
        updated_role['role_id'] = role_id

        return updated_role
