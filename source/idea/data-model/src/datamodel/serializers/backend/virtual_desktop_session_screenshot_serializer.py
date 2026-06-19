#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializer for VirtualDesktopSessionScreenshot - handles conversion between API model and DDB dict.

This class inherits from BaseSerializer which provides all the core dynamic
serialization logic. Override _customize_to_ddb() and _customize_from_ddb()
to add model-specific transformation logic.

Available fields: idea_session_id, format, data, created_on, failure_reason
"""

from typing import Dict, Any, Optional
import logging

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils

logger = logging.getLogger(__name__)


class VirtualDesktopSessionScreenshotSerializer(BaseSerializer):
    """
    Serializer for VirtualDesktopSessionScreenshot model.

    Inherits dynamic enum and nested object serialization from BaseSerializer.
    Override the _customize_* methods below to add custom transformation logic.
    """

    def _customize_to_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom API -> DDB transformations for VirtualDesktopSessionScreenshot.
        
        Args:
            data: Converted data dictionary (enums already converted to strings)
            
        Returns:
            Customized data dictionary
        """
        return data
        
    def _customize_from_ddb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add custom DDB -> API transformations for VirtualDesktopSessionScreenshot.

        Flatten the private DCV session-management API response into the public model's
        fields. Each entry is in exactly one of two mutually exclusive
        shapes: successful ({"session_screenshot": {...}}) or unsuccessful
        ({"get_session_screenshot_request_data": {...}, "failure_reason"}).

        Args:
            data: Data dictionary to be customized

        Returns:
            Customized data dictionary
        """
        if "session_screenshot" in data:
            screenshot = data.pop("session_screenshot") or {}
            data["idea_session_id"] = screenshot.get("session_id")
            images = screenshot.get("images") or []
            if images:
                # Note: Using first image as private API returns and front-end consumes one image per session_id
                image = images[0]
                data["format"] = image.get("format")
                data["data"] = image.get("data")
                data["created_on"] = image.get("created_on")
        elif "get_session_screenshot_request_data" in data:
            request_data = data.pop("get_session_screenshot_request_data") or {}
            data["idea_session_id"] = request_data.get("session_id")

        return data


# Create singleton instance for easy import
virtualdesktopsessionscreenshot_serializer = VirtualDesktopSessionScreenshotSerializer()
