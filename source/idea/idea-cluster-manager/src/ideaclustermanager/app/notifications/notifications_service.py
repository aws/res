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
from ideasdk.service import SocaService
from ideasdk.utils import Utils, Jinja2Utils
from ideadatamodel import GetEmailTemplateRequest, Notification

from ideaclustermanager.app.accounts.accounts_service import AccountsService
from ideaclustermanager.app.email_templates.email_templates_service import EmailTemplatesService

from typing import Dict
from concurrent.futures import ThreadPoolExecutor
import threading
import time

MAX_WORKERS = 1  # must be between 1 and 10


class NotificationsService(SocaService):

    def __init__(self, context: SocaContext, accounts: AccountsService, email_templates: EmailTemplatesService):
        super().__init__(context)

        self.context = context
        self.logger = context.logger('notifications')

        self.accounts = accounts
        self.email_templates = email_templates

        self.exit = threading.Event()
        self.notifications_queue_url = self.context.config().get_string('cluster-manager.notifications_queue_url', required=True)

        self.notifications_monitor_thread = threading.Thread(
            target=self.notifications_queue_listener,
            name='notifications-monitor'
        )
        self.notifications_executors = ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix='notifications-executor'
        )
        self.jinja2_env = Jinja2Utils.env_using_base_loader()

    def send_email(self, notification: Notification):
        """
        send email

        payload must contain below fields:

            username: str
            template_name: str - the name of the email template
            params: dict - containing all parameters required to render the template

        """
        try:

            ses_enabled = self.context.config().get_bool('cluster.ses.enabled', False)
            if not ses_enabled:
                self.logger.debug('ses is disabled. skip.')
                return

            sender_email = self.context.config().get_string('cluster.ses.sender_email', required=True)
            max_sending_rate = self.context.config().get_int('cluster.ses.max_sending_rate', 1)
            max_sending_rate = max(1, max_sending_rate)

            email_notifications_enabled = self.context.config().get_bool('cluster-manager.notifications.email.enabled', False)
            if not email_notifications_enabled:
                self.logger.debug('email notifications are disabled. skip.')
                return

            ses_region = self.context.config().get_string('cluster.ses.region', required=True)

            ses = self.context.aws().ses(region_name=ses_region)

            username = notification.username
            user = self.accounts.get_user(username=username)
            if Utils.is_false(user.enabled):
                self.logger.info(f'user: {username} has been disabled. skip email notification')
                return

            email = user.email
            if Utils.is_empty(email):
                self.logger.warning(f'email address not found for user: {username}. skip email notification')
                return

            template_name = notification.template_name
            get_template_result = self.email_templates.get_email_template(GetEmailTemplateRequest(name=template_name))
            template = get_template_result.template
            subject_template = template.subject
            body_template = template.body

            params = Utils.get_as_dict(notification.params, {})

            subject_template = self.jinja2_env.from_string(subject_template)
            message_template = self.jinja2_env.from_string(body_template)
            subject = subject_template.render(**params)
            body = message_template.render(**params)

            ses.send_email(
                Source=sender_email,
                Destination={
                    'ToAddresses': [email]
                },
                Message={
                    'Subject': {
                        'Data': subject
                    },
                    'Body': {
                        'Html': {
                            'Data': body
                        }
                    }
                }
            )

            delay = float(1 / max_sending_rate)
            time.sleep(delay)

        except Exception as e:
            self.logger.exception(f'failed to send email notification: {e}')

    def execute_notifications(self, sqs_message: Dict):
        notifications_name = None
        try:
            message_body = Utils.get_value_as_string('Body', sqs_message)
            receipt_handle = Utils.get_value_as_string('ReceiptHandle', sqs_message)
            payload = Utils.from_json(message_body)
            self.send_email(Notification(**payload))
            self.context.aws().sqs().delete_message(
                QueueUrl=self.notifications_queue_url,
                ReceiptHandle=receipt_handle
            )
        except Exception as e:
            self.logger.exception(f'failed to execute notifications: {notifications_name} - {e}')

    def notifications_queue_listener(self):
        while not self.exit.is_set():
            try:
                result = self.context.aws().sqs().receive_message(
                    QueueUrl=self.notifications_queue_url,
                    MaxNumberOfMessages=MAX_WORKERS,
                    WaitTimeSeconds=20
                )
                messages = Utils.get_value_as_list('Messages', result, [])
                if len(messages) == 0:
                    continue
                self.logger.info(f'received {len(messages)} messages')
                for message in messages:
                    self.notifications_executors.submit(lambda message_: self.execute_notifications(message_), message)

            except Exception as e:
                self.logger.exception(f'failed to poll queue: {e}')

    def start(self):
        self.notifications_monitor_thread.start()

    def stop(self):
        self.exit.set()
        if self.notifications_monitor_thread.is_alive():
            self.notifications_monitor_thread.join()
        self.notifications_executors.shutdown(wait=True)
