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

import { ListFilesRequest, ListFilesResult, ReadFileRequest, ReadFileResult, SaveFileRequest, SaveFileResult, DownloadFilesRequest, DownloadFilesResult, CreateFileRequest, CreateFileResult, DeleteFilesRequest, DeleteFilesResult, TailFileRequest, TailFileResult } from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface FileBrowserClientProps extends IdeaBaseClientProps {}

class FileBrowserClient extends IdeaBaseClient<FileBrowserClientProps> {
    listFiles(req: ListFilesRequest): Promise<ListFilesResult> {
        return this.apiInvoker.invoke_alt<ListFilesRequest, ListFilesResult>("FileBrowser.ListFiles", req);
    }

    downloadFiles(req: DownloadFilesRequest): Promise<DownloadFilesResult> {
        return this.apiInvoker.invoke_alt<DownloadFilesRequest, DownloadFilesResult>("FileBrowser.DownloadFiles", req);
    }

    readFile(req: ReadFileRequest): Promise<ReadFileResult> {
        return this.apiInvoker.invoke_alt<ReadFileRequest, ReadFileResult>("FileBrowser.ReadFile", req);
    }

    tailFile(req: TailFileRequest): Promise<TailFileResult> {
        return this.apiInvoker.invoke_alt<TailFileRequest, TailFileResult>("FileBrowser.TailFile", req);
    }

    saveFile(req: SaveFileRequest): Promise<SaveFileResult> {
        return this.apiInvoker.invoke_alt<SaveFileRequest, SaveFileResult>("FileBrowser.SaveFile", req);
    }

    createFile(req: CreateFileRequest): Promise<CreateFileResult> {
        return this.apiInvoker.invoke_alt<CreateFileRequest, CreateFileResult>("FileBrowser.CreateFile", req);
    }

    deleteFiles(req: DeleteFilesRequest): Promise<DeleteFilesResult> {
        return this.apiInvoker.invoke_alt<DeleteFilesRequest, DeleteFilesResult>("FileBrowser.DeleteFiles", req);
    }
}

export default FileBrowserClient;
