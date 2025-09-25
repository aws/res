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

from ideasdk.context import SocaContext
from ideadatamodel import exceptions, errorcodes

from res.constants import AD_AUTOMATION_DB_HASH_KEY, AD_AUTOMATION_TABLE_NAME
from ideaclustermanager.app.accounts.db.ad_automation_dao import ADAutomationDAO
from ideaclustermanager.app.accounts.helpers.ad_computer_helper_base import ADComputerHelperBase

from typing import Dict
from res.utils import table_utils


class DeleteComputeHelper(ADComputerHelperBase):
    """
    Helper to manage deleting Computer Accounts in AD using adcli.

    Errors:
    * AD_AUTOMATION_DELETE_COMPUTER_FAILED - when the request is bad, invalid or cannot be retried.
    * AD_AUTOMATION_DELETE_COMPUTER_RETRY - when request is valid, but delete-computer operation fails due to intermittent or timing errors.
        operation will be retried based on SQS visibility timeout settings.
    """

    def __init__(self, context: SocaContext, ad_automation_dao: ADAutomationDAO, sender_id: str, request: Dict):
        self.logger = context.logger('delete-computer')
        super().__init__(context, self.logger, ad_automation_dao, sender_id, request)
        self._initialize_delete_data()


    def get_retry_error_code(self):
        return errorcodes.AD_AUTOMATION_DELETE_COMPUTER_RETRY

    def get_failed_error_code(self):
        return errorcodes.AD_AUTOMATION_DELETE_COMPUTER_FAILED

    def _initialize_delete_data(self):
        payload = self.request.get("payload", {})

        if not self.sender_id:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_DELETE_COMPUTER_FAILED,
                message='Unable to verify cluster node identity: SenderId is required'
            )

        sender_id_tokens = self.sender_id.split(':')
        if len(sender_id_tokens) != 2:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_DELETE_COMPUTER_FAILED,
                message='Unable to verify cluster node identity: Invalid SenderId'
            )
        
        instance_id = payload.get("instance_id", "")
        if not instance_id:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_DELETE_COMPUTER_FAILED,
                message='instance_id is required'
            )
        self.instance_id = instance_id

    def invoke(self):
        """
        call adcli delete-computer and delete the ad-automation dynamodb table with record
        """

        try:

            authorization = table_utils.get_item(
                AD_AUTOMATION_TABLE_NAME, key={AD_AUTOMATION_DB_HASH_KEY: self.instance_id}
            )
            if not authorization:
                self.logger.info(
                    f"No AD Authorization for instance: {self.instance_id}. skipping..."
                )
                return

            self.hostname = authorization.get("hostname")
            domain_controller_ip = self.get_any_domain_controller_ip()

            if not self.is_existing_computer_account():
                self.logger.info(f'{self.log_tag} found no existing computer account. skipping ...')
                return

            self.logger.info(f'{self.log_tag} deleting computer account using DC: {domain_controller_ip} ...')

            try:
                self.delete_computer(domain_controller_ip=domain_controller_ip)
            except exceptions.SocaException as e:
                if e.error_code == errorcodes.AD_AUTOMATION_DELETE_COMPUTER_FAILED:
                   raise exceptions.soca_exception(
                            error_code=errorcodes.AD_AUTOMATION_DELETE_COMPUTER_RETRY,
                            message=e.message
                        )
                else:
                    raise e
                
            table_utils.delete_item(
                AD_AUTOMATION_TABLE_NAME,
                key={AD_AUTOMATION_DB_HASH_KEY: self.instance_id},
            )

            self.logger.info(f'{self.log_tag} computer account deleted successfully.')
        except exceptions.SocaException as e:
            raise e
