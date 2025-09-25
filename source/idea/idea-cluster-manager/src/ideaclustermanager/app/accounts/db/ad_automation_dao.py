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
from ideadatamodel import exceptions
from ideasdk.context import SocaContext

from typing import Dict


class ADAutomationDAO:

    def __init__(self, context: SocaContext):
        self.context = context
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.ad-automation'

    def initialize(self):
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    def create_ad_automation_entry(self, entry: Dict) -> Dict:

        instance_id = Utils.get_value_as_string('instance_id', entry)
        if Utils.is_empty(instance_id):
            raise exceptions.invalid_params('instance_id is required')

        status = Utils.get_value_as_string('status', entry)
        if Utils.is_empty(status):
            raise exceptions.invalid_params('status is required.')

        if status not in ('success', 'fail'):
            raise exceptions.invalid_params('status must be one of [success, fail]')

        created_entry = {
            **entry,
            'created_on': Utils.current_time_ms(),
            'updated_on': Utils.current_time_ms()
        }
        self.table.put_item(
            Item=created_entry
        )
        return created_entry
