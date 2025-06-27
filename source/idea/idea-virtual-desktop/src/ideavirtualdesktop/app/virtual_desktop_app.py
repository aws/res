#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

from res.app.res_app import ResApp
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME
from res.resources.dynamodb.dynamodb_stream_subscription import (
    DynamoDBStreamSubscription,
)

from res.utils.sssd_utils import SSSDConfigEventSubscriber
from res.utils import table_utils, logging_utils
import res.constants as constants

class IdeaVirtualDesktopApp(ResApp):
    """
    Virtual desktop app
    """
    def __init__(self):
        self.logger = logging_utils.get_logger(constants.MODULE_ID_VIRTUAL_DESKTOP_APP)
        super().__init__(constants.MODULE_ID_VIRTUAL_DESKTOP_APP, self.logger)
    def app_initialize(self):
        self.logger.info(f"app_initialize start")

        BASE_OS = os.getenv("RES_BASE_OS")

        if BASE_OS == "windows":
            from ideavirtualdesktop.app.windows import bootstrap as windows_bootstrap
            self.logger.info("Configuring Windows VDI")
            windows_bootstrap.run()

        if BASE_OS != "windows":
            DynamoDBStreamSubscription(
                stream_subscriber=SSSDConfigEventSubscriber(
                    self.logger, constants.MODULE_ID_VIRTUAL_DESKTOP_APP
                ),
                table_name=table_utils.resolve_table_name(CLUSTER_SETTINGS_TABLE_NAME),
                table_kinesis_stream_name=table_utils.get_table_kinesis_stream_name(
                    CLUSTER_SETTINGS_TABLE_NAME
                ),
                logger=self.logger,
            )

            from ideavirtualdesktop.app.linux import bootstrap as linux_bootstrap
            self.logger.info("Configuring Linux VDI")
            linux_bootstrap.run()

    def app_start(self):
        pass

    def app_stop(self):
        pass
