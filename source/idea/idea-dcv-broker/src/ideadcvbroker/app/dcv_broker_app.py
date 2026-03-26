#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import time

import res.constants as constants
from ideabootstrap import bootstrap_common
from ideabootstrap.common import chronyd, cloudwatch_agent
from ideabootstrap.common import constants as bootstrap_constants
from ideabootstrap.common import (
    ebs_volume_tags,
    idea_proxy,
    idea_service_account,
    motd,
    network_interface_tags,
)
from ideabootstrap.dcv_broker import dcv_broker
from ideabootstrap.ssh import disable_ssh, restrict_ssh
from ideabootstrap.sudo import sudoer_secure_path
from ideasdk.metrics.cloudwatch.cloudwatch_agent_config import (
    CloudWatchAgentLogFileOptions,
)
from res.app.res_app import ResApp
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME
from res.resources.dynamodb.dynamodb_stream_subscription import (
    DynamoDBStreamSubscription,
)
from res.utils import logging_utils, table_utils
from ideadcvbroker.app.dcv_broker_config_subscriber import (
    DcvBrokerConfigEventSubscriber,
)


class DcvBrokerApp(ResApp):
    """
    DCV broker app
    """

    def __init__(self):
        self.logger = logging_utils.get_logger(constants.MODULE_ID_VDC)

        super().__init__(constants.MODULE_ID_VDC, self.logger)

    def app_initialize(self):
        if os.path.isfile(bootstrap_constants.INSTANCE_READY_LOCK):
            self.logger.info(
                f"Configuration was already completed, skipping. INSTANCE_READY_LOCK file: {bootstrap_constants.INSTANCE_READY_LOCK}"
            )
            return

        bootstrap_common.set_reboot_required("no")

        if os.environ.get("IDEA_HTTPS_PROXY"):
            idea_proxy.set_proxy()

        idea_service_account.setup_account()

        cloudwatch_agent.setup(
            [
                CloudWatchAgentLogFileOptions(
                    file_path="/opt/idea/app/logs/**.log",
                    log_group_name=f'/{os.environ.get("environment_name")}/vdc/dcv-broker',
                    log_stream_name="application_{ip_address}",
                    retention_in_days=90,
                ),
                CloudWatchAgentLogFileOptions(
                    file_path="/var/log/dcv-session-manager-broker/**.log",
                    log_group_name=f'/{os.environ.get("environment_name")}/vdc/dcv-broker',
                    log_stream_name="dcv-session-manager-broker_{ip_address}",
                ),
            ]
        )

        restrict_ssh.configure(session_owner=True)
        disable_ssh.configure()

        network_interface_tags.setup()
        ebs_volume_tags.setup()

        chronyd.configure()
        bootstrap_common.disable_ulimit()
        bootstrap_common.disable_strict_host_check()
        motd.disable_update()

        sudoer_secure_path.configure(os.environ["PATH"])

        messages = [
            f'{os.environ.get("IDEA_MODULE_NAME", "")} (v{os.environ.get("IDEA_MODULE_VERSION", "")}), Cluster: {os.environ.get("IDEA_CLUSTER_NAME", "")}'
        ]
        motd.update(messages)

        # Configure DCV broker
        dcv_broker.configure_dcv_broker_properties()
        dcv_broker.verify_broker_installation()
        dcv_broker.configure_dcv_broker()
        dcv_broker.clean_staging_area()
        dcv_broker.notify_controller()

        # Subscribe to cluster-settings changes
        DynamoDBStreamSubscription(
            stream_subscriber=DcvBrokerConfigEventSubscriber(self.logger),
            table_name=table_utils.resolve_table_name(CLUSTER_SETTINGS_TABLE_NAME),
            table_kinesis_stream_name=table_utils.get_table_kinesis_stream_name(
                CLUSTER_SETTINGS_TABLE_NAME
            ),
            logger=self.logger,
        )

        timestamp = str(int(time.time()))
        with open(bootstrap_constants.INSTANCE_READY_LOCK, "w") as f:
            f.write(timestamp)

        bootstrap_common.check_reboot_required()

    def app_start(self):
        pass

    def app_stop(self):
        pass
