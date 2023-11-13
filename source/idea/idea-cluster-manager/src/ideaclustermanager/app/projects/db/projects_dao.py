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
from ideadatamodel import (exceptions, Project, AwsProjectBudget, ListProjectsRequest, ListProjectsResult,
                           SocaPaginator, SocaKeyValue)
from ideasdk.context import SocaContext

from typing import Dict, Optional
from boto3.dynamodb.conditions import Attr, Key
import arrow

GSI_PROJECT_NAME = 'project-name-index'


class ProjectsDAO:

    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('projects-dao')
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.projects'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'project_id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'name',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'project_id',
                        'KeyType': 'HASH'
                    }
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': GSI_PROJECT_NAME,
                        'KeySchema': [
                            {
                                'AttributeName': 'name',
                                'KeyType': 'HASH'
                            }
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
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    @staticmethod
    def convert_from_db(project: Dict) -> Project:
        project_id = Utils.get_value_as_string('project_id', project)
        name = Utils.get_value_as_string('name', project)
        title = Utils.get_value_as_string('title', project)
        description = Utils.get_value_as_string('description', project)
        ldap_groups = Utils.get_value_as_list('ldap_groups', project, [])
        enabled = Utils.get_value_as_bool('enabled', project, False)
        enable_budgets = Utils.get_value_as_bool('enable_budgets', project, False)
        budget_name = Utils.get_value_as_string('budget_name', project)
        budget = None
        if Utils.is_not_empty(budget_name):
            budget = AwsProjectBudget(
                budget_name=budget_name
            )
        db_tags = Utils.get_value_as_dict('tags', project)
        tags = None
        if db_tags is not None:
            tags = []
            for key, value in db_tags.items():
                tags.append(SocaKeyValue(key=key, value=value))

        created_on = Utils.get_value_as_int('created_on', project)
        updated_on = Utils.get_value_as_int('updated_on', project)

        return Project(
            project_id=project_id,
            title=title,
            name=name,
            description=description,
            ldap_groups=ldap_groups,
            tags=tags,
            enabled=enabled,
            enable_budgets=enable_budgets,
            budget=budget,
            created_on=arrow.get(created_on).datetime,
            updated_on=arrow.get(updated_on).datetime
        )

    @staticmethod
    def convert_to_db(project: Project) -> Dict:
        """
        convert project to db object.
        None values will not replace existing values
        :param project:
        :return: Dict
        """
        db_project = {
            'project_id': project.project_id
        }

        if project.name is not None:
            db_project['name'] = project.name

        if project.title is not None:
            db_project['title'] = project.title

        if project.description is not None:
            db_project['description'] = project.description

        if project.ldap_groups is not None:
            db_project['ldap_groups'] = project.ldap_groups

        if project.tags is not None:
            tags = {}
            for tag in project.tags:
                tags[tag.key] = tag.value
            db_project['tags'] = tags

        if project.enable_budgets is not None:
            db_project['enable_budgets'] = project.enable_budgets

        if project.budget is not None and project.budget.budget_name is not None:
            db_project['budget_name'] = project.budget.budget_name

        return db_project

    def create_project(self, project: Dict) -> Dict:
        created_project = {
            **project,
            'project_id': Utils.uuid(),
            'created_on': Utils.current_time_ms(),
            'updated_on': Utils.current_time_ms()
        }
        self.table.put_item(
            Item=created_project
        )

        return created_project

    def get_project_by_id(self, project_id: str) -> Optional[Dict]:

        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')

        result = self.table.get_item(
            Key={
                'project_id': project_id
            }
        )
        return Utils.get_value_as_dict('Item', result)

    def get_project_by_name(self, name: str) -> Optional[Dict]:

        if Utils.is_empty(name):
            raise exceptions.invalid_params('name is required')

        result = self.table.query(
            IndexName=GSI_PROJECT_NAME,
            KeyConditionExpression=Key('name').eq(name)
        )
        items = Utils.get_value_as_list('Items', result, [])
        if len(items) == 0:
            return None

        return items[0]

    def update_project(self, project: Dict):

        project_id = Utils.get_value_as_string('project_id', project)
        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')

        project['updated_on'] = Utils.current_time_ms()

        update_expression_tokens = []
        expression_attr_names = {}
        expression_attr_values = {}

        for key, value in project.items():
            if key in ('project_id', 'created_on'):
                continue
            update_expression_tokens.append(f'#{key} = :{key}')
            expression_attr_names[f'#{key}'] = key
            expression_attr_values[f':{key}'] = value

        result = self.table.update_item(
            Key={
                'project_id': project_id
            },
            ConditionExpression=Attr('project_id').eq(project_id),
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW'
        )

        updated_project = result['Attributes']
        updated_project['project_id'] = project_id

        return updated_project

    def delete_project(self, project_id: str):

        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')

        self.table.delete_item(
            Key={
                'project_id': project_id
            }
        )

    def list_projects(self, request: ListProjectsRequest) -> ListProjectsResult:
        scan_request = {}

        cursor = request.cursor
        last_evaluated_key = None
        if Utils.is_not_empty(cursor):
            last_evaluated_key = Utils.from_json(Utils.base64_decode(cursor))
        if last_evaluated_key is not None:
            scan_request['LastEvaluatedKey'] = last_evaluated_key

        scan_filter = None
        if Utils.is_not_empty(request.filters):
            scan_filter = {}
            for filter_ in request.filters:
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

        scan_result = self.table.scan(**scan_request)

        db_projects = Utils.get_value_as_list('Items', scan_result, [])
        projects = []
        for db_project in db_projects:
            project = self.convert_from_db(db_project)
            projects.append(project)

        response_cursor = None
        last_evaluated_key = Utils.get_any_value('LastEvaluatedKey', scan_result)
        if last_evaluated_key is not None:
            response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_key))

        return ListProjectsResult(
            listing=projects,
            paginator=SocaPaginator(
                cursor=response_cursor
            )
        )
