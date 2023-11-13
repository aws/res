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
    'CreateProjectRequest',
    'CreateProjectResult',
    'GetProjectRequest',
    'GetProjectResult',
    'UpdateProjectRequest',
    'UpdateProjectResult',
    'DeleteProjectRequest',
    'DeleteProjectResult',
    'ListProjectsRequest',
    'ListProjectsResult',
    'EnableProjectRequest',
    'EnableProjectResult',
    'DisableProjectRequest',
    'DisableProjectResult',
    'GetUserProjectsRequest',
    'GetUserProjectsResult',
    'ListFileSystemsForProjectRequest',
    'ListFileSystemsForProjectResult',
    'OPEN_API_SPEC_ENTRIES_PROJECTS'
)

from ideadatamodel import SocaPayload, SocaListingPayload, IdeaOpenAPISpecEntry
from ideadatamodel.projects.projects_model import Project
from typing import Optional, List

from ideadatamodel.shared_filesystem import FileSystem


# Projects.CreateProject
class CreateProjectRequest(SocaPayload):
    project: Optional[Project]
    filesystem_names: Optional[list[str]]


class CreateProjectResult(SocaPayload):
    project: Optional[Project]


# Projects.CreateProject
class GetProjectRequest(SocaPayload):
    project_name: Optional[str]
    project_id: Optional[str]


class GetProjectResult(SocaPayload):
    project: Optional[Project]


# Projects.UpdateProject
class UpdateProjectRequest(SocaPayload):
    project: Optional[Project]


class UpdateProjectResult(SocaPayload):
    project: Optional[Project]


# Projects.DeleteProject
class DeleteProjectRequest(SocaPayload):
    project_name: Optional[str]
    project_id: Optional[str]


class DeleteProjectResult(SocaPayload):
    pass


# Projects.ListProjects, Projects.ListProjects
class ListProjectsRequest(SocaListingPayload):
    pass


class ListProjectsResult(SocaListingPayload):
    listing: Optional[List[Project]]


# Projects.EnableProject
class EnableProjectRequest(SocaPayload):
    project_name: Optional[str]
    project_id: Optional[str]


class EnableProjectResult(SocaPayload):
    pass


# Projects.DisableProject
class DisableProjectRequest(SocaPayload):
    project_name: Optional[str]
    project_id: Optional[str]


class DisableProjectResult(SocaPayload):
    pass


# Projects.GetUserProjects
class GetUserProjectsRequest(SocaPayload):
    username: Optional[str]


class GetUserProjectsResult(SocaPayload):
    projects: Optional[List[Project]]


# Projects.ListFileSystemsForProject
class ListFileSystemsForProjectRequest(SocaPayload):
    project_id: Optional[str]
    project_name: Optional[str]


class ListFileSystemsForProjectResult(SocaListingPayload):
    listing: Optional[List[FileSystem]]

OPEN_API_SPEC_ENTRIES_PROJECTS = [
    IdeaOpenAPISpecEntry(
        namespace='Projects.CreateProject',
        request=CreateProjectRequest,
        result=CreateProjectResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Projects.GetProject',
        request=GetProjectRequest,
        result=GetProjectResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Projects.UpdateProject',
        request=UpdateProjectRequest,
        result=UpdateProjectResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Projects.ListProjects',
        request=ListProjectsRequest,
        result=ListProjectsResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Projects.GetUserProjects',
        request=GetUserProjectsRequest,
        result=GetUserProjectsResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Projects.EnableProject',
        request=EnableProjectRequest,
        result=EnableProjectResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Projects.DisableProject',
        request=DisableProjectRequest,
        result=DisableProjectResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='Projects.ListFileSystemsForProject',
        request=ListFileSystemsForProjectRequest,
        result=ListFileSystemsForProjectResult,
        is_listing=True,
        is_public=False
    ),
]
