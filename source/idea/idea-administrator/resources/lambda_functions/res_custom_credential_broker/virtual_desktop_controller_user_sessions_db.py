#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the 'License'). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import logging

USER_SESSION_OWNER_KEY = os.environ.get('USER_SESSION_OWNER_KEY')
USER_SESSION_SESSION_ID_KEY = os.environ.get('USER_SESSION_SESSION_ID_KEY')


class VirtualDesktopControllerUserSessionsDB:
    def __init__(self, cluster_name, module_id, logger: logging.Logger):
        self.cluster_name = cluster_name
        self.module_id = module_id
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(self.table_name)
        self.logger = logger

    @property
    def table_name(self):
        #  TODO: this should be a constant
        return f'{self.cluster_name}.{self.module_id}.controller.user-sessions'

    def get_user_session(self, owner_id, session_id):
        try:
            response = self.table.get_item(
                Key={
                    USER_SESSION_OWNER_KEY: owner_id,
                    USER_SESSION_SESSION_ID_KEY: session_id
                }
            )
            # Extract the item from the response
            item = response.get('Item')
            return item
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error getting item from DynamoDB: {e}")
            return None

    def get_project_id(self, owner_id, session_id):
        item = self.get_user_session(owner_id,  session_id)
        if item:
            project_item = item.get("project")
            if project_item:
                return project_item.get("name")
        return None
