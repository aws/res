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
    'CreateEmailTemplateRequest',
    'CreateEmailTemplateResult',
    'GetEmailTemplateRequest',
    'GetEmailTemplateResult',
    'UpdateEmailTemplateRequest',
    'UpdateEmailTemplateResult',
    'DeleteEmailTemplateRequest',
    'DeleteEmailTemplateResult',
    'ListEmailTemplatesRequest',
    'ListEmailTemplatesResult',
    'OPEN_API_SPEC_ENTRIES_EMAIL_TEMPLATES'
)

from ideadatamodel import SocaPayload, SocaListingPayload, IdeaOpenAPISpecEntry
from ideadatamodel.email_templates.email_templates_model import EmailTemplate
from typing import Optional, List


# EmailTemplates.CreateEmailTemplate
class CreateEmailTemplateRequest(SocaPayload):
    template: Optional[EmailTemplate]


class CreateEmailTemplateResult(SocaPayload):
    template: Optional[EmailTemplate]


# EmailTemplates.CreateEmailTemplate
class GetEmailTemplateRequest(SocaPayload):
    name: Optional[str]


class GetEmailTemplateResult(SocaPayload):
    template: Optional[EmailTemplate]


# EmailTemplates.UpdateEmailTemplate
class UpdateEmailTemplateRequest(SocaPayload):
    template: Optional[EmailTemplate]


class UpdateEmailTemplateResult(SocaPayload):
    template: Optional[EmailTemplate]


# EmailTemplates.DeleteEmailTemplate
class DeleteEmailTemplateRequest(SocaPayload):
    name: Optional[str]


class DeleteEmailTemplateResult(SocaPayload):
    pass


# EmailTemplates.ListEmailTemplates
class ListEmailTemplatesRequest(SocaListingPayload):
    pass


class ListEmailTemplatesResult(SocaListingPayload):
    listing: Optional[List[EmailTemplate]]


OPEN_API_SPEC_ENTRIES_EMAIL_TEMPLATES = [
    IdeaOpenAPISpecEntry(
        namespace='EmailTemplates.CreateEmailTemplate',
        request=CreateEmailTemplateRequest,
        result=CreateEmailTemplateResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='EmailTemplates.GetEmailTemplate',
        request=GetEmailTemplateRequest,
        result=GetEmailTemplateResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='EmailTemplates.UpdateEmailTemplate',
        request=UpdateEmailTemplateRequest,
        result=UpdateEmailTemplateResult,
        is_listing=False,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='EmailTemplates.ListEmailTemplates',
        request=ListEmailTemplatesRequest,
        result=ListEmailTemplatesResult,
        is_listing=True,
        is_public=False
    ),
    IdeaOpenAPISpecEntry(
        namespace='EmailTemplates.DeleteEmailTemplate',
        request=DeleteEmailTemplateRequest,
        result=DeleteEmailTemplateResult,
        is_listing=False,
        is_public=False
    )
]
