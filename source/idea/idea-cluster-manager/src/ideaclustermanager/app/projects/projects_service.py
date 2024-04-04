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
    DeleteProjectRequest,
    DeleteProjectResult,
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
    ListSecurityGroupsResult,
    ListPoliciesResult
)
from ideasdk.aws import AwsResources
from ideasdk.utils import Utils
from ideasdk.launch_configurations import LaunchScriptsHelper, LaunchRoleHelper
from ideasdk.context import SocaContext, ArnBuilder
from ideasdk.client.vdc_client import AbstractVirtualDesktopControllerClient

from ideaclustermanager.app.projects.db.projects_dao import ProjectsDAO
from ideaclustermanager.app.projects.db.user_projects_dao import UserProjectsDAO
from ideaclustermanager.app.accounts.accounts_service import AccountsService
from ideaclustermanager.app.tasks.task_manager import TaskManager

from typing import List, Set


class ProjectsService:

    def __init__(self, context: SocaContext, accounts_service: AccountsService, task_manager: TaskManager, vdc_client: AbstractVirtualDesktopControllerClient):
        self.context = context
        self.accounts_service = accounts_service
        self.task_manager = task_manager
        self.vdc_client = vdc_client
        self.logger = context.logger('projects')
        self.arn_builder = ArnBuilder(self.context.config())

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

        # Validate scripts
        scripts = project.scripts
        if scripts is not None:
            if not LaunchScriptsHelper.validate_scripts(scripts):
                raise exceptions.invalid_params('Script location is incorrect. Script must be https://, s3://, or file://')

        # Validate security groups and ensure security group is within VPC
        if project.security_groups:
            vpc_id = self.context.config().get_string('cluster.network.vpc_id')
            for security_group_id in project.security_groups:
                if not self.context.aws_util().is_security_group_available(security_group_id=security_group_id,vpc_id=vpc_id):
                    self.logger.error(f'{security_group_id} is not a valid security group that can be attached')
                    raise exceptions.invalid_params('Security group is not valid')

        # Create VDI role only when policies are provided
        policy_arns = Utils.get_as_string_list(project.policy_arns, [])
        if policy_arns:
            for policy_arn in policy_arns:
                if not self.context.aws_util().is_policy_valid(policy_arn):
                    self.logger.error(f'{policy_arn} is not a valid policy arn that can be attached')
                    raise exceptions.invalid_params('Policy is not valid')
            self._create_vdi_role_and_instance_profile(project.name, set(policy_arns))

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

    def delete_project(self, request: DeleteProjectRequest) -> DeleteProjectResult:
        """
        Delete a Project
        validate required fields, remove the project from DynamoDB and Cache.
        :param request: DeleteProjectRequest
        :param access_token: access token used for this request
        :param api_authorization: authorization for this request
        :return: DeleteProjectResult
        """
        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')

        project_id = request.project_id
        project_name = request.project_name
        if Utils.is_empty(project_id) and Utils.is_empty(project_name):
            raise exceptions.invalid_params('either project id or project name is required')

        project = self.projects_dao.get_project_by_id(project_id) if project_id else self.projects_dao.get_project_by_name(project_name)
        if project is not None:
            project_id = self.projects_dao.convert_from_db(project).project_id
            sessions_by_project_id = self.vdc_client.list_sessions_by_project_id(project_id)
            if sessions_by_project_id:
                session_ids_by_project_id = [session.dcv_session_id for session in sessions_by_project_id]
                raise exceptions.general_exception(f'project is still used by virtual desktop sessions. '
                                                   f'Project ID: {project_id}, Session IDs: {session_ids_by_project_id}')

            software_stacks_by_project_id = self.vdc_client.list_software_stacks_by_project_id(project_id)
            if software_stacks_by_project_id:
                stack_ids_by_project_id = [software_stack.stack_id for software_stack in software_stacks_by_project_id]
                raise exceptions.general_exception(f'project is still used by software stacks. '
                                                   f'Project ID: {project_id}, Stack IDs: {stack_ids_by_project_id}')

            self.user_projects_dao.delete_project(project_id)
            self.projects_dao.delete_project(project_id)

        return DeleteProjectResult()

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
        users_added = None
        users_removed = None
        if project.users:
            existing_users = set(existing.get('users', []))
            updated_users = set(project.users)

            users_added = updated_users - existing_users
            users_removed = existing_users - updated_users
            if len(users_added) > 0:
                for username in users_added:
                    # check if user exists
                    self.accounts_service.get_user(username)
        # none values will be skipped by db update. ensure enabled/disabled cannot be called via update project.
        project.enabled = None

        # Validate scripts
        scripts = project.scripts
        if scripts is not None:
            if not LaunchScriptsHelper.validate_scripts(scripts):
                raise exceptions.invalid_params('Script location is incorrect. Script must be https://, s3://, or file://')

        # Validate security groups and ensure security group is within VPC
        if project.security_groups:
            vpc_id = self.context.config().get_string('cluster.network.vpc_id')
            for security_group_id in project.security_groups:
                if not self.context.aws_util().is_security_group_available(security_group_id=security_group_id,vpc_id=vpc_id):
                    self.logger.error(f'{security_group_id} is not a valid security group that can be attached')
                    raise exceptions.invalid_params('Security group is not valid')

        # Update VDI role if new policies differ from existing policies
        policy_arns = Utils.get_as_string_list(project.policy_arns, [])
        existing_policies = Utils.get_value_as_list('policy_arns', existing, [])
        policies_to_detach = set(existing_policies) - set(policy_arns)
        policies_to_attach = set(policy_arns) - set(existing_policies)
        if policies_to_detach or policies_to_attach:
            for policy_arn in policy_arns:
                if not self.context.aws_util().is_policy_valid(policy_arn=policy_arn):
                    self.logger.error(f'{policy_arn} is not a valid policy arn that can be attached')
                    raise exceptions.invalid_params('Policy is not valid')
            self._update_vdi_role(project_name=project.name, policies_to_detach=policies_to_detach, policies_to_attach=policies_to_attach)

        db_updated = self.projects_dao.update_project(self.projects_dao.convert_to_db(project))
        updated_project = self.projects_dao.convert_from_db(db_updated)
        if updated_project.enabled:
            if groups_added or groups_removed or users_added or users_removed:
                self.task_manager.send(
                    task_name='projects.project-groups-updated',
                    payload={
                        'project_id': updated_project.project_id,
                        'groups_added': list(groups_added or []),
                        'groups_removed': list(groups_removed or []),
                        'users_added': list(users_added or []),
                        'users_removed': list(users_removed or [])
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

    def list_security_groups(self) -> ListSecurityGroupsResult:
        vpc_id = self.context.config().get_string('cluster.network.vpc_id')
        security_groups = self.context.aws_util().list_available_security_groups(vpc_id=vpc_id)
        return ListSecurityGroupsResult(security_groups=security_groups)

    def list_policies(self) -> ListPoliciesResult:
        policies = self.context.aws_util().list_available_host_policies()
        return ListPoliciesResult(policies=policies)

    def _create_vdi_role_and_instance_profile(self, project_name: str , policy_arns: Set[str], ) -> bool:
        self.logger.debug(f'Creating new VDI role for project {project_name}')
        vdi_role_name = LaunchRoleHelper.get_vdi_role_name(cluster_name=self.context.cluster_name(), project_name=project_name)
        instance_profile_name = vdi_role_name
        is_vdi_role_created = False
        is_vdi_instance_profile_created = False
        policies_added = []
        try:
            is_vdi_role_created = self.context.aws_util().create_vdi_host_role(vdi_role_name)
            is_vdi_instance_profile_created = self.context.aws_util().create_vdi_instance_profile(instance_profile_name)
            self.logger.debug(f'Attach custom policies to VDI role {vdi_role_name}')
            for policy_arn in policy_arns:
                self.context.aws_util().attach_role_policy(
                    role_name=vdi_role_name,
                    policy_arn=policy_arn
                )
                policies_added.append(policy_arn)
            self.logger.debug(f'Attach RES required policies to VDI role {vdi_role_name}')
            vdi_required_policy_arns = self.arn_builder.dcv_host_required_policy_arns
            for vdi_required_policy_arn in vdi_required_policy_arns:
                self.context.aws_util().attach_role_policy(
                    role_name=vdi_role_name,
                    policy_arn=vdi_required_policy_arn
                )
                policies_added.append(vdi_required_policy_arn)
            self.context.aws_util().add_role_to_instance_profile(
                role_name=vdi_role_name, instance_profile_name=instance_profile_name)
        except Exception as e:
            # Roll back creation of VDI role and instance profile if any steps fail
            if policies_added:
                for policy_arn in policies_added:
                    self.context.aws_util().detach_role_policy(
                        role_name=vdi_role_name,
                        policy_arn=policy_arn
                    )
            if is_vdi_role_created:
                self.context.aws_util().delete_vdi_host_role(vdi_role_name)
            if is_vdi_instance_profile_created:
                self.context.aws_util().delete_vdi_instance_profile(instance_profile_name)
            self.logger.error(f'Create VDI role error {e}')
            raise exceptions.general_exception("Could not create role with given policies")
        return True

    def _update_vdi_role(self, project_name, policies_to_detach: Set[str], policies_to_attach: Set[str]) -> bool:
        vdi_role_name = LaunchRoleHelper.get_vdi_role_name(cluster_name=self.context.cluster_name(), project_name=project_name)
        if not self.context.aws_util().does_vdi_role_exist(role_name=vdi_role_name):
            # If role does not exist, there were never any existing policies attached
            return self._create_vdi_role_and_instance_profile(project_name, policies_to_attach)
        policies_added = []
        policies_removed = []
        try:
            for policy_arn in policies_to_detach:
                self.context.aws_util().detach_role_policy(role_name=vdi_role_name, policy_arn=policy_arn)
                policies_removed.append(policy_arn)
            for policy_arn in policies_to_attach:
                self.context.aws_util().attach_role_policy(role_name=vdi_role_name, policy_arn=policy_arn)
                policies_added.append(policy_arn)
        except Exception as e:
            if policies_added:
                for policy_arn in policies_added:
                    self.context.aws_util().detach_role_policy(
                        role_name=vdi_role_name,
                        policy_arn=policy_arn
                    )
            if policies_removed:
                for policy_arn in policies_removed:
                    self.context.aws_util().attach_role_policy(
                        role_name=vdi_role_name,
                        policy_arn=policy_arn
                    )
            self.logger.error(f'Update VDI role error {e}')
            raise exceptions.general_exception("Could not update role with given policies")

        return True

