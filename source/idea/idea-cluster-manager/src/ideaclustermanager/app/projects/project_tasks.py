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

__all__ = (
    'ProjectEnabledTask',
    'ProjectDisabledTask',
    'ProjectGroupsUpdatedTask'
)

from ideasdk.utils import Utils

import ideaclustermanager
from ideaclustermanager.app.tasks.base_task import BaseTask

from typing import Dict


class ProjectEnabledTask(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'projects.project-enabled'

    def invoke(self, payload: Dict):
        project_id = payload['project_id']
        self.context.projects.user_projects_dao.project_enabled(
            project_id=project_id
        )


class ProjectDisabledTask(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'projects.project-disabled'

    def invoke(self, payload: Dict):
        project_id = payload['project_id']
        self.context.projects.user_projects_dao.project_disabled(
            project_id=project_id
        )


class ProjectGroupsUpdatedTask(BaseTask):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'projects.project-groups-updated'

    def invoke(self, payload: Dict):
        project_id = payload['project_id']
        project = self.context.projects.projects_dao.get_project_by_id(project_id)
        if project['enabled']:
            groups_added = payload.get('groups_added') or []
            groups_removed = payload.get('groups_removed') or []
            users_added = payload.get('users_added') or []
            users_removed = payload.get('users_removed') or []

            for username in users_removed:
                self.context.projects.user_projects_dao.delete_user_project(
                    project_id=project_id,
                    username=username,
                    by_ldaps=["SELF"]
                ) 

            for ldap_group_name in groups_removed:
                self.context.projects.user_projects_dao.ldap_group_removed(
                    project_id=project_id,
                    group_name=ldap_group_name
                )
                # perform full refresh to ensure if users existed in multiple groups, and one of the group
                # was deleted, those users get added back again
                self.context.projects.user_projects_dao.project_enabled(
                    project_id=project_id
                )

            for username in users_added:
                self.context.projects.user_projects_dao.create_user_project(
                    project_id=project_id,
                    username=username,
                    by_ldaps=["SELF"]
                ) 

            for ldap_group_name in groups_added:
                self.context.projects.user_projects_dao.ldap_group_added(
                    project_id=project_id,
                    group_name=ldap_group_name
                )
