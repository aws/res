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


from ideadatamodel import exceptions, errorcodes, constants
from ideadatamodel.projects import (
    CreateProjectRequest,
    CreateProjectResult,
    GetProjectRequest,
    GetProjectResult,
    UpdateProjectRequest,
    UpdateProjectResult,
    ListProjectsRequest,
    ListProjectsResult,
    EnableProjectRequest,
    EnableProjectResult,
    DisableProjectRequest,
    DisableProjectResult,
    GetUserProjectsRequest,
    GetUserProjectsResult,
    Project
)
from ideasdk.utils import Utils, GroupNameHelper
from ideasdk.context import SocaContext

from ideaclustermanager.app.projects.db.projects_dao import ProjectsDAO
from ideaclustermanager.app.projects.db.user_projects_dao import UserProjectsDAO
from ideaclustermanager.app.accounts.accounts_service import AccountsService
from ideaclustermanager.app.tasks.task_manager import TaskManager

from typing import List


class ProjectsService:

    def __init__(self, context: SocaContext, accounts_service: AccountsService, task_manager: TaskManager):
        self.context = context
        self.accounts_service = accounts_service
        self.task_manager = task_manager
        self.logger = context.logger('projects')

        self.projects_dao = ProjectsDAO(context)
        self.projects_dao.initialize()

        self.user_projects_dao = UserProjectsDAO(
            context=context,
            projects_dao=self.projects_dao,
            accounts_service=self.accounts_service
        )
        self.user_projects_dao.initialize()

    def create_project(self, request: CreateProjectRequest) -> CreateProjectResult:
        """
        Create a new Project
        validate required fields, add the project to DynamoDB and Cache.
        :param request:
        :return: the created project (with project_id)
        """

        ds_provider = self.context.config().get_string('directoryservice.provider', required=True)

        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')

        project = request.project
        if Utils.is_empty(project):
            raise exceptions.invalid_params('project is required')

        if Utils.is_empty(project.name):
            raise exceptions.invalid_params('project.name is required')

        existing = self.projects_dao.get_project_by_name(project.name)
        if existing is not None:
            raise exceptions.invalid_params(f'project with name: {project.name} already exists')

        if Utils.is_empty(project.ldap_groups):
            raise exceptions.invalid_params('ldap_groups[] is required')
        for ldap_group_name in project.ldap_groups:
            # check if group exists
            # Active Directory mode checks the back-end LDAP
            if ds_provider in {constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}:
                self.logger.debug(f'Performing DS lookup for group: {ldap_group_name}')
                self.accounts_service.ldap_client.get_group(ldap_group_name)
            else:
                self.accounts_service.get_group(ldap_group_name)

        enable_budgets = Utils.get_as_bool(project.enable_budgets, False)
        if enable_budgets:
            if project.budget is None or Utils.is_empty(project.budget.budget_name):
                raise exceptions.invalid_params('budget.budget_name is required when budgets are enabled')
            budget_name = project.budget.budget_name
            self.context.aws_util().budgets_get_budget(budget_name)

        # ensure project is always disabled during creation
        project.enabled = False

        db_project = self.projects_dao.convert_to_db(project)
        db_created_project = self.projects_dao.create_project(db_project)

        created_project = self.projects_dao.convert_from_db(db_created_project)

        # and then call enable_project() to propagate the status
        self.enable_project(EnableProjectRequest(
                project_id=created_project.project_id
            ))

        enabled_project = self.get_project(
            GetProjectRequest(project_id=created_project.project_id))

        return CreateProjectResult(
            project=enabled_project.project
        )

    def get_project(self, request: GetProjectRequest) -> GetProjectResult:
        """
        Retrieve the Project from the cache
        :param request.project_name name of the project you are getting
        :param request.project_id UUID of the project being searched
        :return: Project from cache
        """
        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')
        if Utils.are_empty(request.project_id, request.project_name):
            raise exceptions.invalid_params('Either project_id or project_name is required')

        self.logger.debug(f'get_project(): running with request: {request}')

        project = None
        if Utils.is_not_empty(request.project_id):
            project = self.projects_dao.get_project_by_id(request.project_id)
        elif Utils.is_not_empty(request.project_name):
            project = self.projects_dao.get_project_by_name(request.project_name)

        if project is None:
            if Utils.is_not_empty(request.project_id):
                raise exceptions.soca_exception(
                    error_code=errorcodes.PROJECT_NOT_FOUND,
                    message=f'project not found for project id: {request.project_id}'
                )
            if Utils.is_not_empty(request.project_name):
                raise exceptions.soca_exception(
                    error_code=errorcodes.PROJECT_NOT_FOUND,
                    message=f'project not found for project name: {request.project_name}'
                )

        return GetProjectResult(
            project=self.projects_dao.convert_from_db(project)
        )

    def update_project(self, request: UpdateProjectRequest) -> UpdateProjectResult:
        """
        Update a Project
        :param request:
        :return:
        """
        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')

        project = request.project
        if Utils.is_empty(project):
            raise exceptions.invalid_params('project is required')
        if Utils.is_empty(project.project_id):
            raise exceptions.invalid_params('project.project_id is required')

        existing = self.projects_dao.get_project_by_id(project_id=project.project_id)

        if existing is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.PROJECT_NOT_FOUND,
                message=f'project not found for id: {project.project_id}'
            )

        if Utils.is_not_empty(project.name) and existing['name'] != project.name:
            same_name_project = self.projects_dao.get_project_by_name(project.name)
            if same_name_project is not None and same_name_project['project_id'] != project.project_id:
                raise exceptions.invalid_params(f'project with name: {project.name} already exists')

        enable_budgets = Utils.get_as_bool(project.enable_budgets, False)
        if enable_budgets:
            if project.budget is None or Utils.is_empty(project.budget.budget_name):
                raise exceptions.invalid_params('budget.budget_name is required when budgets are enabled')
            budget_name = project.budget.budget_name
            self.context.aws_util().budgets_get_budget(budget_name)

        groups_added = None
        groups_removed = None
        if Utils.is_not_empty(project.ldap_groups):
            existing_ldap_groups = set(Utils.get_value_as_list('ldap_groups', existing, []))
            updated_ldap_groups = set(project.ldap_groups)

            groups_added = updated_ldap_groups - existing_ldap_groups
            groups_removed = existing_ldap_groups - updated_ldap_groups

            if len(groups_added) > 0:
                for ldap_group_name in groups_added:
                    # check if group exists
                    self.accounts_service.get_group(ldap_group_name)

        # none values will be skipped by db update. ensure enabled/disabled cannot be called via update project.
        project.enabled = None

        db_updated = self.projects_dao.update_project(self.projects_dao.convert_to_db(project))
        updated_project = self.projects_dao.convert_from_db(db_updated)

        if updated_project.enabled:
            if groups_added is not None or groups_removed is not None:
                self.task_manager.send(
                    task_name='projects.project-groups-updated',
                    payload={
                        'project_id': updated_project.project_id,
                        'groups_added': list(groups_added),
                        'groups_removed': list(groups_removed)
                    },
                    message_group_id=updated_project.project_id
                )

        return UpdateProjectResult(
            project=updated_project
        )

    def enable_project(self, request: EnableProjectRequest) -> EnableProjectResult:

        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')
        if Utils.are_empty(request.project_id, request.project_name):
            raise exceptions.invalid_params('Either project_id or project_name is required')

        project = None
        if Utils.is_not_empty(request.project_id):
            project = self.projects_dao.get_project_by_id(request.project_id)
        elif Utils.is_not_empty(request.project_name):
            project = self.projects_dao.get_project_by_name(request.project_name)

        if project is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.PROJECT_NOT_FOUND,
                message='project not found'
            )

        self.projects_dao.update_project({
            'project_id': project['project_id'],
            'enabled': True
        })

        self.task_manager.send(
            task_name='projects.project-enabled',
            payload={
                'project_id': project['project_id']
            },
            message_group_id=project['project_id'],
            message_dedupe_id=Utils.short_uuid()
        )

        return EnableProjectResult()

    def disable_project(self, request: DisableProjectRequest) -> DisableProjectResult:

        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')
        if Utils.are_empty(request.project_id, request.project_name):
            raise exceptions.invalid_params('Either project_id or project_name is required')

        project = None
        if Utils.is_not_empty(request.project_id):
            project = self.projects_dao.get_project_by_id(request.project_id)
        elif Utils.is_not_empty(request.project_name):
            project = self.projects_dao.get_project_by_name(request.project_name)

        if project is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.PROJECT_NOT_FOUND,
                message='project not found'
            )
        self.projects_dao.update_project({
            'project_id': project['project_id'],
            'enabled': False
        })

        self.task_manager.send(
            task_name='projects.project-disabled',
            payload={
                'project_id': project['project_id']
            },
            message_group_id=project['project_id'],
            message_dedupe_id=Utils.short_uuid()
        )

        return DisableProjectResult()

    def list_projects(self, request: ListProjectsRequest) -> ListProjectsResult:
        return self.projects_dao.list_projects(request)

    def remove_projects_from_group(self, project_ids: List[str], group_name: str, force: bool):
        """
        remove multiple projects from a group
        useful for bulk operations from ad sync script
        :param project_ids: List of project_ids to be removed from group
        :param group_name:
        :param force: force delete even if group is disabled. if project is not found, skip project.
        :return:
        """
        if project_ids is None or len(project_ids) == 0:
            raise exceptions.invalid_params('project_ids is required')

        if group_name is None or len(group_name.strip()) == 0:
            raise exceptions.invalid_params('group_name is required')

        group = self.accounts_service.group_dao.get_group(group_name)
        if group is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_NOT_FOUND,
                message=f'group: {group_name} not found.'
            )
        if not group['enabled'] and not force:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_IS_DISABLED,
                message='cannot remove projects from a disabled group'
            )

        projects = []
        for project_id in project_ids:
            project = self.projects_dao.get_project_by_id(project_id)
            if project is None and not force:
                raise exceptions.soca_exception(
                    error_code=errorcodes.PROJECT_NOT_FOUND, message=f'project not found: {project_id}')
            if not project['enabled'] and not force:
                raise exceptions.soca_exception(
                    error_code=errorcodes.PROJECT_NOT_FOUND, message=f'project is disabled: {project_id}')
            projects.append(project)

        # for each project where the group is a part of the 'ldap_groups', remove the group
        for project in filter(lambda p: group_name in p.get('ldap_groups', []), projects):
            self.projects_dao.update_project(
                {
                    'project_id': project['project_id'],
                    'ldap_groups': [g for g in project.get('ldap_groups', []) if g != group_name],
                }
            )

            self.user_projects_dao.ldap_group_removed(
                project_id=project['project_id'], group_name=group_name)

    def get_user_projects(self, request: GetUserProjectsRequest) -> GetUserProjectsResult:
        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')
        if Utils.is_empty(request.username):
            raise exceptions.invalid_params('username is required')

        self.logger.debug(f'get_user_projects() - request: {request}')

        # Probe directory service
        ds_provider = self.context.config().get_string('directoryservice.provider', required=True)
        self.logger.debug(f'ProjectsService.get_user_projects() - DS Provider is {ds_provider} ...')
        if ds_provider in {constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}:
            self.logger.debug(f'get_user_projects() - Running in AD mode - performing AD query for {request.username} group memberships...')
            user_result = self.accounts_service.ldap_client.get_user(username=request.username)
            self.logger.debug(f'get_user_projects() - User Result: {user_result}')

        user_projects = self.user_projects_dao.get_projects_by_username(request.username)
        is_user_enabled = Utils.is_true(self.context.accounts.get_user(request.username).enabled)

        result = []
        if is_user_enabled:
            # todo - batch get
            for project_id in user_projects:
                db_project = self.projects_dao.get_project_by_id(project_id)
                if db_project is None:
                    continue
                if not db_project['enabled']:
                    continue
                result.append(self.projects_dao.convert_from_db(db_project))
            result.sort(key=lambda p: p.name)

        return GetUserProjectsResult(
            projects=result
        )