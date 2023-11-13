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

import { OpenSearchQueryRequest, OpenSearchQueryResult } from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface AnalyticsClientProps extends IdeaBaseClientProps {}

class AnalyticsClient extends IdeaBaseClient<AnalyticsClientProps> {
    queryOpenSearch(req: OpenSearchQueryRequest): Promise<OpenSearchQueryResult> {
        return this.apiInvoker.invoke_alt<OpenSearchQueryRequest, OpenSearchQueryResult>("Analytics.OpenSearchQuery", req);
    }
}

export default AnalyticsClient;
