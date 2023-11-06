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

from ideasdk.protocols import SocaContextProtocol
from ideadatamodel import constants

IDEA_GROUP_NAME_PREFIX = 'idea'


class GroupNameHelper:
    """
    Helper class to standardize all group names across cluster and modules
    """

    def __init__(self, context: SocaContextProtocol):
        self.context = context

    @staticmethod
    def _build_group_name(group_type: str, name: str) -> str:
        return f'{name}-{group_type}-group'

    def get_cluster_administrators_group(self) -> str:
        group_name = self.context.config().get_string('identity-provider.cognito.administrators_group_name', required=True)
        if group_name.endswith(f'{constants.GROUP_TYPE_CLUSTER}-group'):
            return group_name
        return self._build_group_name(
            group_type=constants.GROUP_TYPE_CLUSTER,
            name=group_name
        )

    def get_cluster_managers_group(self) -> str:
        group_name = self.context.config().get_string('identity-provider.cognito.managers_group_name', required=True)
        if group_name.endswith(f'{constants.GROUP_TYPE_CLUSTER}-group'):
            return group_name
        return self._build_group_name(
            group_type=constants.GROUP_TYPE_CLUSTER,
            name=group_name
        )

    def get_module_administrators_group(self, module_id: str) -> str:
        return self._build_group_name(
            group_type=constants.GROUP_TYPE_MODULE,
            name=f'{module_id}-administrators'
        )

    def get_module_users_group(self, module_id: str) -> str:
        return self._build_group_name(
            group_type=constants.GROUP_TYPE_MODULE,
            name=f'{module_id}-users'
        )

    def get_user_group(self, username: str) -> str:
        return self._build_group_name(
            group_type=constants.GROUP_TYPE_USER,
            name=username
        )
