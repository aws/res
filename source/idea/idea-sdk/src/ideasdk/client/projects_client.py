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

from ideasdk.client.soca_client import SocaClient, SocaClientOptions
from ideasdk.auth import TokenService
from ideasdk.utils import Utils
from ideadatamodel import exceptions
from ideadatamodel.projects import (
    GetProjectRequest,
    Project,
    GetProjectResult,
    GetUserProjectsRequest,
    GetUserProjectsResult
)

from typing import Optional, List
from cacheout import LRUCache


class ProjectsClient:

    def __init__(self, context: SocaContextProtocol,
                 options: SocaClientOptions,
                 token_service: Optional[TokenService],
                 cache_ttl_seconds=30):
        """
        :param context: Application Context
        :param options: Client Options
        :param token_service: TokenService to get the access token. Token service is not required if options.unix_socket is provided.
        """
        self.context = context
        self.logger = context.logger('projects-client')
        self.client = SocaClient(context=context, options=options)
        self.cache = LRUCache(
            maxsize=1000,
            ttl=cache_ttl_seconds
        )

        if Utils.is_empty(options.unix_socket) and token_service is None:
            raise exceptions.invalid_params('token_service is required for http client')
        self.token_service = token_service

    def get_access_token(self) -> Optional[str]:
        if self.token_service is None:
            return None
        return self.token_service.get_access_token()

    def get_project_by_id(self, project_id: str) -> Project:
        if Utils.is_empty(project_id):
            raise exceptions.invalid_params('project_id is required')
        result = self.get_project(GetProjectRequest(project_id=project_id))
        return result.project

    def get_project_by_name(self, project_name: str) -> Project:
        if Utils.is_empty(project_name):
            raise exceptions.invalid_params('project_name is required')
        result = self.get_project(GetProjectRequest(project_name=project_name))
        return result.project

    def get_default_project(self) -> GetProjectResult:
        return self.get_project(GetProjectRequest(
            project_name='default'
        ))

    def get_project(self, request: GetProjectRequest) -> GetProjectResult:

        if Utils.are_empty(request.project_id, request.project_name):
            raise exceptions.invalid_params('either project_id or project_name is required')

        if Utils.is_not_empty(request.project_id):
            cache_key = f'Projects.GetProject.project_id.{request.project_id}'
        else:
            cache_key = f'Projects.GetProject.project_name.{request.project_name}'

        result = self.cache.get(key=cache_key)
        if result is not None:
            return result

        result = self.client.invoke_alt(
            namespace='Projects.GetProject',
            payload=request,
            result_as=GetProjectResult,
            access_token=self.get_access_token()
        )

        self.cache.set(cache_key, result)
        return result

    def get_user_projects(self, username: str) -> List[Project]:

        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        cache_key = f'Projects.GetUserProjects.{username}'

        result = self.cache.get(key=cache_key)
        if result is not None:
            return result

        result = self.client.invoke_alt(
            namespace='Projects.GetUserProjects',
            payload=GetUserProjectsRequest(username=username),
            result_as=GetUserProjectsResult,
            access_token=self.get_access_token()
        )

        self.cache.set(cache_key, result.projects)
        return result.projects

    def destroy(self):
        self.client.close()
