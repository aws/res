#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import time

import res.constants as constants
from ideabastionhost.app.user_event_subscriber import UserEventSubscriber
from ideabootstrap import bootstrap_common
from ideabootstrap.common import (
    amazon_ssm_agent,
    chronyd,
    cloudwatch_agent,
    cognito_modules,
    ebs_volume_tags,
    idea_proxy,
    idea_service_account,
    motd,
    network_interface_tags,
)
from ideabootstrap.common.constants import INSTANCE_READY_LOCK
from ideabootstrap.file_system import shared_storage
from ideabootstrap.sudo import sudoer_secure_path
from res.app.res_app import ResApp
from res.resources import accounts, cluster_settings
from res.resources.dynamodb.dynamodb_stream_subscription import (
    DynamoDBStreamSubscription,
)
from res.utils import logging_utils, table_utils
from res.utils.sssd_utils import SSSDConfigEventSubscriber


class IdeaBastionHostApp(ResApp):
    """
    Bastion host app
    """

    def __init__(self):
        self.logger = logging_utils.get_logger(constants.MODULE_ID_BASTION_HOST)

        super().__init__(constants.MODULE_ID_BASTION_HOST, self.logger)

    def run_bootstrap(self):

        if os.path.isfile(INSTANCE_READY_LOCK):
            self.logger.info(
                f"Configuration was already completed, skipping. INSTANCE_READY_LOCK file: {INSTANCE_READY_LOCK}"
            )
            return
        self.logger.info(f"Starting Boostrap Configuration")

        bootstrap_common.set_reboot_required("no")
        if os.environ.get("IDEA_HTTPS_PROXY"):
            idea_proxy.set_proxy()

        idea_service_account.setup_account()
        amazon_ssm_agent.configure()
        cloudwatch_agent.setup()

        network_interface_tags.setup()
        ebs_volume_tags.setup()

        bootstrap_common.disable_se_linux()
        chronyd.configure()
        bootstrap_common.disable_ulimit()
        bootstrap_common.disable_strict_host_check()
        motd.disable_update()

        messages = [
            f'{os.environ.get("IDEA_MODULE_NAME", "")} (v{os.environ.get("IDEA_MODULE_VERSION", "")}), Cluster: {os.environ.get("IDEA_CLUSTER_NAME", "")}'
        ]
        motd.update(messages)

        cognito_modules.configure()

        # Sudoer configuration
        path = "/sbin:/bin:/usr/sbin:/usr/bin:/opt/idea/python/latest/bin"
        sudoer_secure_path.configure(path)

        # Mount shared storage
        shared_storage.configure()

        self.logger.info("Bastion Configuration Completed")

        timestamp = str(int(time.time()))

        with open(INSTANCE_READY_LOCK, "w") as f:
            f.write(timestamp)

        bootstrap_common.check_reboot_required()

    def app_initialize(self):
        self.run_bootstrap()

        self.create_sssd_config_event_subscription()
        self.create_user_event_subscription()

    def create_sssd_config_event_subscription(self):
        sssd_config_event_subscriber = SSSDConfigEventSubscriber(
            self.logger, constants.MODULE_ID_BASTION_HOST
        )

        # Start SSSD service
        sssd_config_event_subscriber.restart_sssd_service()

        DynamoDBStreamSubscription(
            stream_subscriber=sssd_config_event_subscriber,
            table_name=table_utils.resolve_table_name(
                cluster_settings.CLUSTER_SETTINGS_TABLE_NAME
            ),
            table_kinesis_stream_name=table_utils.get_table_kinesis_stream_name(
                cluster_settings.CLUSTER_SETTINGS_TABLE_NAME
            ),
            logger=self.logger,
        )

    def create_user_event_subscription(self):
        user_event_subscriber = UserEventSubscriber(
            self.logger, constants.MODULE_ID_BASTION_HOST
        )

        # Initialize the DeniedUser list
        user_event_subscriber.deny_ssh_access(
            [
                user.get("username")
                for user in accounts.list_users()
                if not user.get("enabled")
            ]
        )

        DynamoDBStreamSubscription(
            stream_subscriber=user_event_subscriber,
            table_name=table_utils.resolve_table_name(accounts.USERS_TABLE_NAME),
            table_kinesis_stream_name=table_utils.get_table_kinesis_stream_name(
                accounts.USERS_TABLE_NAME
            ),
            logger=self.logger,
        )

    def app_start(self):
        pass

    def app_stop(self):
        pass
