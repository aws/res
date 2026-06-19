#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, Mock
import pytest

# Import the actual serializer
from datamodel.serializers.virtual_desktop_permission_profile_serializer import VirtualDesktopPermissionProfileSerializer


class TestVirtualDesktopPermissionProfileSerializer:
    """Test cases for VirtualDesktopPermissionProfileSerializer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = VirtualDesktopPermissionProfileSerializer()

    def test_customize_to_ddb_with_permissions(self):
        """Test _customize_to_ddb converts permissions correctly."""
        input_data = {
            "profile_id": "test-profile-123",
            "title": "Test Profile",
            "permissions": [
                {"key": "audio_in", "enabled": True},
                {"key": "clipboard_out", "enabled": False},
            ]
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["profile_id"] == "test-profile-123"
        assert result["title"] == "Test Profile"
        assert result["audio_in"] is True
        assert result["clipboard_out"] is False
        assert "permissions" not in result

    def test_customize_to_ddb_with_empty_permissions(self):
        """Test _customize_to_ddb handles empty permissions list."""
        input_data = {
            "profile_id": "test-profile-123",
            "title": "Test Profile",
            "permissions": []
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["profile_id"] == "test-profile-123"
        assert result["title"] == "Test Profile"
        assert "permissions" not in result

    def test_customize_to_ddb_with_none_permissions(self):
        """Test _customize_to_ddb handles None permissions."""
        input_data = {
            "profile_id": "test-profile-123",
            "title": "Test Profile",
            "permissions": None,
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["profile_id"] == "test-profile-123"
        assert result["title"] == "Test Profile"
        assert "permissions" not in result

    def test_customize_to_ddb_without_permissions(self):
        """Test _customize_to_ddb handles None permissions."""
        input_data = {
            "profile_id": "test-profile-123",
            "title": "Test Profile",
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["profile_id"] == "test-profile-123"
        assert result["title"] == "Test Profile"
        assert "permissions" not in result

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_with_permission_fields(self, mock_timestamps_to_iso):
        """Test _customize_from_ddb converts permission fields correctly."""
        input_data = {
            "profile_id": "test-profile-123",
            "title": "Test Profile",
            "audio_in": True,
            "clipboard_out": False,
            "file_transfer": None,
        }

        result = self.serializer._customize_from_ddb(input_data)
        
        # Check permissions array is created correctly
        assert "permissions" in result
        permissions = result["permissions"]
        assert len(permissions) == 3
        
        # Check audio_in permission exists and is correct
        audio_in_perm = next((p for p in permissions if p["key"] == "audio_in"), None)
        assert audio_in_perm is not None
        assert audio_in_perm["enabled"] is True

        # Check clipboard_out permission exists and is correct
        clipboard_out_perm = next((p for p in permissions if p["key"] == "clipboard_out"), None)
        assert clipboard_out_perm is not None
        assert clipboard_out_perm["enabled"] is False

        # Check file_transfer permission (None value should become False)
        file_transfer_perm = next((p for p in permissions if p["key"] == "file_transfer"), None)
        assert file_transfer_perm is not None
        assert file_transfer_perm["enabled"] is False

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_only_default_fields(self, mock_timestamps_to_iso):
        """Test _customize_from_ddb with only default profile fields."""
        input_data = {
            "profile_id": "test-profile-123",
            "title": "Test Profile",
            "description": "Test description",
            "created_on": "2023-01-01T00:00:00Z",
            "updated_on": "2023-01-01T00:00:00Z",
        }

        mock_timestamps_to_iso.side_effect = lambda data, *args: data

        result = self.serializer._customize_from_ddb(input_data)
        
        # Should have empty permissions array since no permission fields
        assert "permissions" in result
        assert result["permissions"] == []

    def test_customize_to_ddb_with_missing_enabled_field(self):
        """Test _customize_to_ddb handles permissions missing enabled field."""
        input_data = {
            "profile_id": "test-profile-123",
            "permissions": [
                {"key": "audio_in"},  # Missing enabled field
            ]
        }

        result = self.serializer._customize_to_ddb(input_data)

        # Should default to False when enabled field is missing
        assert result["audio_in"] is False
        assert "permissions" not in result
