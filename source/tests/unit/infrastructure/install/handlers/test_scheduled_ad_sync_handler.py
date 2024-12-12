#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from res.exceptions import ADSyncConfigurationNotFound, ADSyncInProcess  # type: ignore

from idea.infrastructure.install.handlers import scheduled_ad_sync_handler


@patch("idea.infrastructure.install.handlers.scheduled_ad_sync_handler.start_ad_sync")
@patch("idea.infrastructure.install.handlers.scheduled_ad_sync_handler.logger")
class TestLambdaHandler(unittest.TestCase):

    def test_handler_scheduled_event(
        self, mock_logger: MagicMock, mock_start_ad_sync: MagicMock
    ) -> None:
        event: Dict[str, Any] = {"detail-type": "Scheduled Event"}

        scheduled_ad_sync_handler.handler(event, None)

        mock_start_ad_sync.assert_called_once()

        mock_logger.exception.assert_not_called()

    def test_handler_invalid_event_type(
        self, mock_logger: MagicMock, mock_start_ad_sync: MagicMock
    ) -> None:
        event: Dict[str, Any] = {"detail-type": "Invalid Event"}

        with self.assertRaises(Exception) as context:
            scheduled_ad_sync_handler.handler(event, None)

        mock_start_ad_sync.assert_not_called()

        mock_logger.exception.assert_called_once()
        self.assertIn(
            "only EventBridge Scheduled Event is supported for the lambda",
            str(context.exception),
        )

    def test_handler_start_ad_sync_exception(
        self, mock_logger: MagicMock, mock_start_ad_sync: MagicMock
    ) -> None:
        event: Dict[str, Any] = {"detail-type": "Scheduled Event"}

        mock_start_ad_sync.side_effect = Exception("start_ad_sync error")

        with self.assertRaises(Exception) as context:
            scheduled_ad_sync_handler.handler(event, None)

        mock_start_ad_sync.assert_called_once()

        mock_logger.exception.assert_called_once()
        self.assertIn("start_ad_sync error", str(context.exception))

    def test_handler_start_ad_sync_ignore_configuration_not_found_exception(
        self, mock_logger: MagicMock, mock_start_ad_sync: MagicMock
    ) -> None:
        event: Dict[str, Any] = {"detail-type": "Scheduled Event"}

        mock_start_ad_sync.side_effect = ADSyncConfigurationNotFound()

        scheduled_ad_sync_handler.handler(event, None)
        mock_start_ad_sync.assert_called_once()
        mock_logger.warning.assert_called_once()

    def test_handler_start_ad_sync_in_progress_not_found_exception(
        self, mock_logger: MagicMock, mock_start_ad_sync: MagicMock
    ) -> None:
        event: Dict[str, Any] = {"detail-type": "Scheduled Event"}

        mock_start_ad_sync.side_effect = ADSyncInProcess()

        scheduled_ad_sync_handler.handler(event, None)
        mock_start_ad_sync.assert_called_once()
        mock_logger.warning.assert_called_once()
