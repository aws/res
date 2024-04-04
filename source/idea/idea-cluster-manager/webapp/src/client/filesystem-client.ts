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

import { AddFileSystemToProjectRequest, AddFileSystemToProjectResult, CreateEFSFileSystemRequest, CreateEFSFileSystemResult, CreateONTAPFileSystemRequest, CreateONTAPFileSystemResult, ListFileSystemsRequest, ListFileSystemsResult, RemoveFileSystemFromProjectRequest, RemoveFileSystemFromProjectResult,     ListFileSystemsInVPCRequest,
    ListFileSystemsInVPCResult,
    OnboardEFSFileSystemRequest, OnboardFileSystemResult, OnboardONTAPFileSystemRequest, OnboardLUSTREFileSystemRequest} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface FileSystemClientProps extends IdeaBaseClientProps {}

class FileSystemClient extends IdeaBaseClient<FileSystemClientProps> {
    listFileSystems(req: ListFileSystemsRequest): Promise<ListFileSystemsResult> {
        return this.apiInvoker.invoke_alt<ListFileSystemsRequest, ListFileSystemsResult>("FileSystem.ListFileSystems", req);
    }

    listFileSystemsInVPC(req: ListFileSystemsInVPCRequest): Promise<ListFileSystemsInVPCResult> {
        return this.apiInvoker.invoke_alt<ListFileSystemsInVPCRequest, ListFileSystemsInVPCResult>("FileSystem.ListFSinVPC", req);
    }

    addFileSystemToProject(req: AddFileSystemToProjectRequest) {
        return this.apiInvoker.invoke_alt<AddFileSystemToProjectRequest, AddFileSystemToProjectResult>("FileSystem.AddFileSystemToProject", req);
    }

    removeFileSystemFromProject(req: RemoveFileSystemFromProjectRequest) {
        return this.apiInvoker.invoke_alt<RemoveFileSystemFromProjectRequest, RemoveFileSystemFromProjectResult>("FileSystem.RemoveFileSystemFromProject", req);
    }

    createEFSFileSystem(req: CreateEFSFileSystemRequest) {
        return this.apiInvoker.invoke_alt<CreateEFSFileSystemRequest, CreateEFSFileSystemResult>("FileSystem.CreateEFS", req);
    }

    createONTAPFileSystem(req: CreateONTAPFileSystemRequest) {
        return this.apiInvoker.invoke_alt<CreateONTAPFileSystemRequest, CreateONTAPFileSystemResult>("FileSystem.CreateONTAP", req);
    }

    onboardEFSFileSystem(req: OnboardEFSFileSystemRequest) {
        return this.apiInvoker.invoke_alt<OnboardEFSFileSystemRequest, OnboardFileSystemResult>("FileSystem.OnboardEFSFileSystem", req);
    }

    onboardFSXLUSTREFileSystem(req: OnboardEFSFileSystemRequest) {
        return this.apiInvoker.invoke_alt<OnboardEFSFileSystemRequest, OnboardFileSystemResult>("FileSystem.OnboardLUSTREFileSystem", req);
    }

    onboardFSXONTAPFileSystem(req: OnboardLUSTREFileSystemRequest) {
        return this.apiInvoker.invoke_alt<OnboardLUSTREFileSystemRequest, OnboardFileSystemResult>("FileSystem.OnboardONTAPFileSystem", req);
    }
}

export default FileSystemClient;
