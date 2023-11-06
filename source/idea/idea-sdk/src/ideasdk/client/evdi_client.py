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
from ideadatamodel import SocaEnvelope, SocaHeader
from ideasdk.protocols import SocaContextProtocol

from ideasdk.utils import Utils


class EvdiClient:
    """
    Client to send notifications to eVDI module
    """

    def __init__(self, context: SocaContextProtocol):
        self.context = context
        self._logger = context.logger('evdi-client')

    def publish_user_disabled_event(self, username: str):
        controller_sqs_queue_url = self.context.config().get_string('virtual-desktop-controller.controller_sqs_queue_url', default=None)
        if Utils.is_empty(controller_sqs_queue_url):
            # if the queue is empty then either vdc is not yet deployed or it is not enabled
            # either ways this event can be ignored
            return

        message = SocaEnvelope(
            header=SocaHeader(
                namespace='Accounts.UserDisabledEvent',
                request_id=Utils.uuid()
            ),
            payload={
                'username': username
            }
        )
        self.context.aws().sqs().send_message(
            QueueUrl=controller_sqs_queue_url,
            MessageBody=Utils.to_json(message)
        )
