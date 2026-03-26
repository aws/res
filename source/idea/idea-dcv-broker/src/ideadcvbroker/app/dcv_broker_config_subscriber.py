#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from logging import Logger
from typing import Dict, Optional

from ideabootstrap.dcv_broker import dcv_broker
from res.resources.dynamodb.dynamodb_stream_subscriber import IDynamoDBStreamSubscriber


class DcvBrokerConfigEventSubscriber(IDynamoDBStreamSubscriber):
    def __init__(self, logger_: Logger) -> None:
        self.logger = logger_

    def on_create(self, entry: Dict):
        self.reconfigure_dcv_broker()

    def on_update(self, old_entry: Dict, new_entry: Dict):
        if new_entry.get("value") != old_entry.get("value"):
            self.reconfigure_dcv_broker()

    def on_delete(self, entry: Dict):
        self.reconfigure_dcv_broker()

    def is_entry_monitored(self, entry: Dict) -> bool:
        key = entry.get("key", "")
        return key.startswith("vdc.dcv_broker.")

    @property
    def subscriber_name(self) -> Optional[str]:
        return "dcv-broker"

    def reconfigure_dcv_broker(self) -> None:
        try:
            dcv_broker.configure_dcv_broker_properties()
            self.logger.info("DCV broker properties reconfigured successfully")
        except Exception as e:
            self.logger.error(f"Failed to reconfigure DCV broker: {e}")
