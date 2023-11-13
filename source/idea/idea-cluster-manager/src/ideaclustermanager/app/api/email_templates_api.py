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

import ideaclustermanager

from ideasdk.api import ApiInvocationContext, BaseAPI
from ideadatamodel.email_templates import (
    CreateEmailTemplateRequest,
    GetEmailTemplateRequest,
    UpdateEmailTemplateRequest,
    DeleteEmailTemplateRequest,
    ListEmailTemplatesRequest
)
from ideadatamodel import exceptions
from ideasdk.utils import Utils


class EmailTemplatesAPI(BaseAPI):

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context

        self.SCOPE_WRITE = f'{self.context.module_id()}/write'
        self.SCOPE_READ = f'{self.context.module_id()}/read'

        self.acl = {
            'EmailTemplates.CreateEmailTemplate': {
                'scope': self.SCOPE_WRITE,
                'method': self.create_email_template
            },
            'EmailTemplates.GetEmailTemplate': {
                'scope': self.SCOPE_READ,
                'method': self.get_email_template
            },
            'EmailTemplates.UpdateEmailTemplate': {
                'scope': self.SCOPE_WRITE,
                'method': self.update_email_template
            },
            'EmailTemplates.ListEmailTemplates': {
                'scope': self.SCOPE_READ,
                'method': self.list_email_templates
            },
            'EmailTemplates.DeleteEmailTemplate': {
                'scope': self.SCOPE_WRITE,
                'method': self.delete_email_template
            }
        }

    def create_email_template(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(CreateEmailTemplateRequest)
        result = self.context.email_templates.create_email_template(request)
        context.success(result)

    def get_email_template(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(GetEmailTemplateRequest)
        result = self.context.email_templates.get_email_template(request)
        context.success(result)

    def update_email_template(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(UpdateEmailTemplateRequest)
        result = self.context.email_templates.update_email_template(request)
        context.success(result)

    def list_email_templates(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(ListEmailTemplatesRequest)
        result = self.context.email_templates.list_email_templates(request)
        context.success(result)

    def delete_email_template(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(DeleteEmailTemplateRequest)
        result = self.context.email_templates.delete_email_template(request)
        context.success(result)

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = Utils.get_value_as_string('scope', acl_entry)
        is_authorized = context.is_authorized(elevated_access=True, scopes=[acl_entry_scope])

        if is_authorized:
            acl_entry['method'](context)
        else:
            raise exceptions.unauthorized_access()
