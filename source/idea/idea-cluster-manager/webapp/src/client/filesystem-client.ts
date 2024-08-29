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

import { AddFileSystemToProjectRequest, AddFileSystemToProjectResult, CreateEFSFileSystemRequest, CreateEFSFileSystemResult, 
    CreateONTAPFileSystemRequest, CreateONTAPFileSystemResult, RemoveFileSystemFromProjectRequest, RemoveFileSystemFromProjectResult, 
    ListOnboardedFileSystemsRequest, ListOnboardedFileSystemsResult, ListFileSystemsInVPCRequest, ListFileSystemsInVPCResult,
    OnboardEFSFileSystemRequest, OnboardFileSystemResult, OnboardLUSTREFileSystemRequest, OnboardS3BucketRequest, OnboardS3BucketResult, 
    UpdateFileSystemRequest, UpdateFileSystemResult, RemoveFileSystemRequest, RemoveFileSystemResult} from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface FileSystemClientProps extends IdeaBaseClientProps {}

class FileSystemClient extends IdeaBaseClient<FileSystemClientProps> {
    listOnboardedFileSystems(req: ListOnboardedFileSystemsRequest): Promise<ListOnboardedFileSystemsResult> {
        return this.apiInvoker.invoke_alt<ListOnboardedFileSystemsRequest, ListOnboardedFileSystemsResult>("FileSystem.ListOnboardedFileSystems", req);
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

    updateFileSystem(req: UpdateFileSystemRequest) {
        return this.apiInvoker.invoke_alt<UpdateFileSystemRequest, UpdateFileSystemResult>("FileSystem.UpdateFileSystem", req);
    }

    removeFileSystem(req: RemoveFileSystemRequest) {
        return this.apiInvoker.invoke_alt<RemoveFileSystemRequest, RemoveFileSystemResult>("FileSystem.RemoveFileSystem", req);
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

    onboardS3Bucket(req: OnboardS3BucketRequest) {
        return this.apiInvoker.invoke_alt<OnboardS3BucketRequest, OnboardS3BucketResult>("FileSystem.OnboardS3Bucket", req);
    }
}

export default FileSystemClient;
