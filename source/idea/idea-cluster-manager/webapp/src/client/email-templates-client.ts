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

import { CreateEmailTemplateRequest, CreateEmailTemplateResult, GetEmailTemplateRequest, GetEmailTemplateResult, DeleteEmailTemplateRequest, DeleteEmailTemplateResult, UpdateEmailTemplateRequest, UpdateEmailTemplateResult, ListEmailTemplatesRequest, ListEmailTemplatesResult } from "./data-model";
import IdeaBaseClient, { IdeaBaseClientProps } from "./base-client";

export interface EmailTemplatesClientProps extends IdeaBaseClientProps {}

class EmailTemplatesClient extends IdeaBaseClient<EmailTemplatesClientProps> {
    createEmailTemplate(req: CreateEmailTemplateRequest): Promise<CreateEmailTemplateResult> {
        return this.apiInvoker.invoke_alt<CreateEmailTemplateRequest, CreateEmailTemplateResult>("EmailTemplates.CreateEmailTemplate", req);
    }

    getEmailTemplate(req: GetEmailTemplateRequest): Promise<GetEmailTemplateResult> {
        return this.apiInvoker.invoke_alt<GetEmailTemplateRequest, GetEmailTemplateResult>("EmailTemplates.GetEmailTemplate", req);
    }

    deleteEmailTemplate(req: DeleteEmailTemplateRequest): Promise<DeleteEmailTemplateResult> {
        return this.apiInvoker.invoke_alt<DeleteEmailTemplateRequest, DeleteEmailTemplateResult>("EmailTemplates.DeleteEmailTemplate", req);
    }

    updateEmailTemplate(req: UpdateEmailTemplateRequest): Promise<UpdateEmailTemplateResult> {
        return this.apiInvoker.invoke_alt<UpdateEmailTemplateRequest, UpdateEmailTemplateResult>("EmailTemplates.UpdateEmailTemplate", req);
    }

    listEmailTemplates(req: ListEmailTemplatesRequest): Promise<ListEmailTemplatesResult> {
        return this.apiInvoker.invoke_alt<ListEmailTemplatesRequest, ListEmailTemplatesResult>("EmailTemplates.ListEmailTemplates", req);
    }
}

export default EmailTemplatesClient;
