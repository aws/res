#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pytest

# Import the actual serializer
from datamodel.serializers.virtual_desktop_session_screenshot_serializer import VirtualDesktopSessionScreenshotSerializer


class TestVirtualDesktopSessionScreenshotSerializer:
    """Test cases for VirtualDesktopSessionScreenshotSerializer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = VirtualDesktopSessionScreenshotSerializer()

    def test_customize_from_ddb_successful_entry_flattens_primary_image(self):
        """Successful private API entry flattens to wire-name flat fields."""
        input_data = {
            "session_screenshot": {
                "session_id": "session-1",
                "images": [
                    {
                        "format": "png",
                        "data": "AAAA",
                        "created_on": "2026-05-26T00:00:00Z",
                        "primary": True,
                    },
                ],
            },
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["idea_session_id"] == "session-1"
        assert result["format"] == "png"
        assert result["data"] == "AAAA"
        assert result["created_on"] == "2026-05-26T00:00:00Z"
        assert "session_screenshot" not in result

    def test_customize_from_ddb_successful_entry_with_no_images(self):
        """Successful entry with empty images list still sets idea_session_id."""
        input_data = {
            "session_screenshot": {
                "session_id": "session-1",
                "images": [],
            },
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["idea_session_id"] == "session-1"
        assert "format" not in result
        assert "data" not in result
        assert "created_on" not in result
        assert "session_screenshot" not in result

    def test_customize_from_ddb_successful_entry_with_none_images(self):
        """Successful entry with None images is treated as empty."""
        input_data = {
            "session_screenshot": {
                "session_id": "session-1",
                "images": None,
            },
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["idea_session_id"] == "session-1"
        assert "format" not in result
        assert "session_screenshot" not in result

    def test_customize_from_ddb_unsuccessful_entry_translates_failure_reason(self):
        """Unsuccessful entry surfaces session_id and renames failure_reason to wire form."""
        input_data = {
            "get_session_screenshot_request_data": {"session_id": "session-2"},
            "failure_reason": "Session not found or access denied",
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["idea_session_id"] == "session-2"
        assert "get_session_screenshot_request_data" not in result

    def test_customize_from_ddb_unsuccessful_entry_without_failure_reason(self):
        """Unsuccessful entry missing failure_reason still extracts session_id."""
        input_data = {
            "get_session_screenshot_request_data": {"session_id": "session-2"},
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["idea_session_id"] == "session-2"
        assert "get_session_screenshot_request_data" not in result


