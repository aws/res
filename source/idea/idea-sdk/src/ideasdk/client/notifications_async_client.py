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

from ideasdk.protocols import SocaContextProtocol
from ideasdk.utils import Utils

from ideadatamodel import Notification


class NotificationsAsyncClient:

    def __init__(self, context: SocaContextProtocol):
        """
        :param context: Application Context
        """
        self.context = context
        self._logger = context.logger('async-notifications-client')

    def send_notification(self, notification: Notification):
        sqs_queue_url = self.context.config().get_string('cluster-manager.notifications_queue_url', required=True)
        self.context.aws().sqs().send_message(
            QueueUrl=sqs_queue_url,
            MessageBody=Utils.to_json(notification),
            MessageDeduplicationId=Utils.uuid(),
            MessageGroupId=self.context.module_id()
        )
