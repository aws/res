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
from typing import List

import ideaclustermanager
from ideadatamodel.shared_filesystem import FileSystem

from ideasdk.api import ApiInvocationContext, BaseAPI
from ideadatamodel.projects import (
    CreateProjectRequest,
    DeleteProjectRequest,
    GetProjectRequest,
    UpdateProjectRequest,
    ListProjectsRequest,
    EnableProjectRequest,
    DisableProjectRequest,
    GetUserProjectsRequest,
    ListFileSystemsForProjectRequest,
    ListFileSystemsForProjectResult
)
from ideadatamodel import exceptions, constants
from ideasdk.utils import Utils, ApiUtils


class ProjectsAPI(BaseAPI):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.logger = context.logger('projects')
        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
            'Projects.CreateProject': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_project
            },
            'Projects.DeleteProject': {
                'scope': self.SCOPE_WRITE,
                'method': self.delete_project
            },
            'Projects.GetProject': {
                'scope': self.SCOPE_READ,
                'method': self.get_project
            },
            'Projects.UpdateProject': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_project
            },
            'Projects.ListProjects': {
                'scope': self.SCOPE_READ,
                'method': self.list_projects
            },
            'Projects.GetUserProjects': {
                'scope': self.SCOPE_READ,
                'method': self.admin_get_user_projects
            },
            'Projects.EnableProject': {
                'scope': self.SCOPE_WRITE,
                'method': self.enable_project
            },
            'Projects.DisableProject': {
                'scope': self.SCOPE_WRITE,
                'method': self.disable_project
            },
            'Projects.ListFileSystemsForProject': {
                'scope': self.SCOPE_READ,
                'method': self.list_filesystems_for_project
            },
            'Projects.ListSecurityGroups': {
                'scope': self.SCOPE_READ,
                'method': self.list_security_groups
            },
            'Projects.ListPolicies': {
                'scope': self.SCOPE_READ,
                'method': self.list_policies
            }
        }

    def create_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(CreateProjectRequest)
        ApiUtils.validate_input(request.project.name,
                                constants.PROJECT_ID_REGEX,
                                constants.PROJECT_ID_ERROR_MESSAGE)
        result = self.context.projects.create_project(request)
        if request.filesystem_names is not None:
            result.filesystem_names = self.context.shared_filesystem.update_filesystems_to_project_mappings(request.filesystem_names, request.project.name)
        context.success(result)

    def delete_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(DeleteProjectRequest)
        result = self.context.projects.delete_project(request)
        context.success(result)

    def get_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetProjectRequest)
        result = self.context.projects.get_project(request)
        project = result.project
        if project.is_budgets_enabled():
            budget = self.context.aws_util().budgets_get_budget(budget_name=project.budget.budget_name)
            project.budget = budget
        context.success(result)

    def update_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(UpdateProjectRequest)
        result = self.context.projects.update_project(request)
        if request.filesystem_names is not None:
            result.filesystem_names = self.context.shared_filesystem.update_filesystems_to_project_mappings(request.filesystem_names, request.project.name)
        context.success(result)

    def list_projects(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListProjectsRequest)
        result = self.context.projects.list_projects(request)
        for project in result.listing:
            if project.is_budgets_enabled():
                # this call could possibly make some performance degradations, if the configured budget is not available.
                # need to optimize this further.
                budget = self.context.aws_util().budgets_get_budget(budget_name=project.budget.budget_name)
                project.budget = budget
        context.success(result)

    def get_user_projects(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetUserProjectsRequest)
        request.username = context.get_username() if not Utils.is_empty(context.get_username()) else request.username
        request.exclude_disabled = Utils.get_as_bool(request.exclude_disabled, True)
        result = self.context.projects.get_user_projects(request)
        context.success(result)

    def admin_get_user_projects(self, context: ApiInvocationContext):
        if not context.is_administrator():
            self.get_user_projects(context)
            return
        request = context.get_request_payload_as(GetUserProjectsRequest)
        if Utils.is_empty(request.username):
            request.username = context.get_username()
        result = self.context.projects.get_user_projects(request)
        context.success(result)

    def enable_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(EnableProjectRequest)
        result = self.context.projects.enable_project(request)
        context.success(result)

    def disable_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(DisableProjectRequest)
        result = self.context.projects.disable_project(request)
        context.success(result)

    def list_filesystems_for_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListFileSystemsForProjectRequest)

        project_name = request.project_name
        if Utils.is_empty(project_name):
            raise exceptions.invalid_params('project_name is required')

        shared_storage_config_dict = self.context.config().get_config(constants.MODULE_SHARED_STORAGE).as_plain_ordered_dict()
        filesystems: List[FileSystem] = []
        for fs_name, config in shared_storage_config_dict.items():
            if Utils.is_not_empty(Utils.get_as_dict(config)) and 'projects' in list(config.keys()):
                fs = FileSystem(name=fs_name, storage=config)
                if Utils.is_not_empty(fs.get_projects()) and project_name in fs.get_projects():
                    filesystems.append(fs)

        context.success(ListFileSystemsForProjectResult(listing=filesystems))

    def list_security_groups(self, context: ApiInvocationContext):
        result = self.context.projects.list_security_groups()
        context.success(result)

    def list_policies(self, context: ApiInvocationContext):
        result = self.context.projects.list_policies()
        context.success(result)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = Utils.get_value_as_string('scope', acl_entry)
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])
        is_authenticated_user = context.is_authenticated_user()

        if is_authorized:
            acl_entry['method'](context)
            return

        if is_authenticated_user and namespace in ('Projects.GetUserProjects', 'Projects.GetProject'):
            acl_entry['method'](context)
            return
        
        # Conditional permissions for non-admins
        
        if namespace == 'Projects.EnableProject':
            request = context.get_request_payload_as(EnableProjectRequest)
            # Current user must have "update_status" permission for all projects in the request
            if not Utils.is_empty(request.project_id) and context.is_authorized(elevated_access=False, scopes=[acl_entry_scope], role_assignment_resource_key=f"{request.project_id}:project"):
                acl_entry['method'](context)
                return
        elif namespace == 'Projects.DisableProject':
            request = context.get_request_payload_as(DisableProjectRequest)
            # Current user must have "update_status" permission for all projects in the request
            if not Utils.is_empty(request.project_id) and context.is_authorized(elevated_access=False, scopes=[acl_entry_scope], role_assignment_resource_key=f"{request.project_id}:project"):
                acl_entry['method'](context)
                return

        raise exceptions.unauthorized_access()
