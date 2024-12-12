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

from ideadatamodel import exceptions, errorcodes
from ideadatamodel.email_templates import (
    UpdateEmailTemplateRequest,
    UpdateEmailTemplateResult,
    DeleteEmailTemplateRequest,
    DeleteEmailTemplateResult,
    EmailTemplate
)
from ideasdk.utils import Utils
from ideasdk.context import SocaContext

from ideaclustermanager.app.email_templates.email_templates_dao import EmailTemplatesDAO
from ideaclustermanager.app.app_utils import ClusterManagerUtils


class EmailTemplatesService:

    def __init__(self, context: SocaContext):
        self.context = context
        self.logger = context.logger('email-templates')

        self.email_templates_dao = EmailTemplatesDAO(context)
        self.email_templates_dao.initialize()

    def update_email_template(self, request: UpdateEmailTemplateRequest) -> UpdateEmailTemplateResult:
        """
        Update an EmailTemplate
        :param request:
        :return:
        """
        if Utils.is_empty(request):
            raise exceptions.invalid_params('request is required')
        if Utils.are_empty(request.template):
            raise exceptions.invalid_params('template is required')
        if Utils.are_empty(request.template.name):
            raise exceptions.invalid_params('template.name is required')
        if Utils.are_empty(request.template.template_type):
            raise exceptions.invalid_params('template.template_type is required')

        db_email_template = self.email_templates_dao.get_email_template(request.template.name)

        if db_email_template is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.EMAIL_TEMPLATE_NOT_FOUND,
                message=f'email_template not found for name: {request.template.name}'
            )

        db_updated = self.email_templates_dao.update_email_template(self.email_templates_dao.convert_to_db(request.template))
        updated_email_template = self.email_templates_dao.convert_from_db(db_updated)

        return UpdateEmailTemplateResult(
            template=updated_email_template
        )

    def delete_email_template(self, request: DeleteEmailTemplateRequest) -> DeleteEmailTemplateResult:
        if Utils.is_empty(request.name):
            raise exceptions.invalid_params('name is required')
        self.email_templates_dao.delete_email_template(request.name)
        return DeleteEmailTemplateResult()
