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

import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";


export interface BackendClientProps extends IdeaBaseClientProps {
}

class BackendClient extends IdeaBaseClient<BackendClientProps> {
    config(body?: {ssh_enabled: boolean}): Promise<any> {
        return this.apiInvoker.invoke_alt("config", body, false, true, {}, body ? "PUT" : "GET");
    }
    start_ad_sync(): Promise<any> {
        return this.apiInvoker.invoke_alt("ad-sync", {}, false, true, {}, "PUT");
    }
    check_ad_sync_status(body?: {id: string}): Promise<any> {
        let name_space = "ad-sync"
        if (body && body.id) {
            name_space = `ad-sync?id=${encodeURIComponent(body.id)}`
        }
        return this.apiInvoker.invoke_alt(name_space, body, false, true, {}, "GET");
    }
    stop_ad_sync(body?: {id: string}): Promise<any> {
        return this.apiInvoker.invoke_alt("ad-sync", body, false, true, {}, "DELETE");
    }
}

export default BackendClient;
