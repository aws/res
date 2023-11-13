/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 * with the License. A copy of the License is located at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 * OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

import {
    CreateProjectRequest,
    CreateProjectResult,
    GetProjectRequest,
    GetProjectResult,
    DeleteProjectRequest,
    DeleteProjectResult,
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
    ListFileSystemsForProjectRequest,
    ListFileSystemsForProjectResult,
} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface ProjectsClientProps extends IdeaBaseClientProps {}

class ProjectsClient extends IdeaBaseClient<ProjectsClientProps> {
    createProject(req: CreateProjectRequest): Promise<CreateProjectResult> {
        return this.apiInvoker.invoke_alt<CreateProjectRequest, CreateProjectResult>("Projects.CreateProject", req);
    }

    getProject(req: GetProjectRequest): Promise<GetProjectResult> {
        return this.apiInvoker.invoke_alt<GetProjectRequest, GetProjectResult>("Projects.GetProject", req);
    }

    deleteProject(req: DeleteProjectRequest): Promise<DeleteProjectResult> {
        return this.apiInvoker.invoke_alt<DeleteProjectRequest, DeleteProjectResult>("Projects.DeleteProject", req);
    }

    updateProject(req: UpdateProjectRequest): Promise<UpdateProjectResult> {
        return this.apiInvoker.invoke_alt<UpdateProjectRequest, UpdateProjectResult>("Projects.UpdateProject", req);
    }

    listProjects(req: ListProjectsRequest): Promise<ListProjectsResult> {
        return this.apiInvoker.invoke_alt<ListProjectsRequest, ListProjectsResult>("Projects.ListProjects", req);
    }

    getUserProjects(req: GetUserProjectsRequest): Promise<GetUserProjectsResult> {
        return this.apiInvoker.invoke_alt<GetUserProjectsRequest, GetUserProjectsResult>("Projects.GetUserProjects", req);
    }

    enableProject(req: EnableProjectRequest): Promise<EnableProjectResult> {
        return this.apiInvoker.invoke_alt<EnableProjectRequest, EnableProjectResult>("Projects.EnableProject", req);
    }

    disableProject(req: DisableProjectRequest): Promise<DisableProjectResult> {
        return this.apiInvoker.invoke_alt<DisableProjectRequest, DisableProjectResult>("Projects.DisableProject", req);
    }

    listFileSystemsForProject(req: ListFileSystemsForProjectRequest): Promise<ListFileSystemsForProjectResult> {
        return this.apiInvoker.invoke_alt<ListFileSystemsForProjectRequest, ListFileSystemsForProjectResult>("Projects.ListFileSystemsForProject", req);
    }
}

export default ProjectsClient;
