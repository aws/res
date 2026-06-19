#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, Mock
import pytest

# Import the actual serializer
from datamodel.serializers.virtual_desktop_session_permission_serializer import VirtualDesktopSessionPermissionSerializer


class TestVirtualDesktopSessionPermissionSerializer:
    """Test cases for VirtualDesktopSessionPermissionSerializer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = VirtualDesktopSessionPermissionSerializer()

    def test_customize_to_ddb_with_permission_profile(self):
        """Test _customize_to_ddb extracts permission_profile_id correctly."""
        input_data = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
            "actor_type": "USER",
            "permission_profile": {
                "profile_id": "profile-456",
                "title": "Test Profile"
            },
            "expiry_date": "1769212800000",
            "idea_session_created_on": "1769146771000"
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["idea_session_id"] == "session-123"
        assert result["actor_name"] == "user1"
        assert result["actor_type"] == "USER"
        assert result["permission_profile_id"] == "profile-456"
        assert "permission_profile" not in result
        assert result["expiry_date"] == 1769212800000
        assert result["idea_session_created_on"] == 1769146771000
        assert isinstance(result["expiry_date"], int)
        assert isinstance(result["idea_session_created_on"], int)

    def test_customize_to_ddb_with_empty_permission_profile(self):
        """Test _customize_to_ddb handles empty permission_profile."""
        input_data = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
            "permission_profile": {}
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["idea_session_id"] == "session-123"
        assert result["actor_name"] == "user1"
        assert result["permission_profile_id"] is None
        assert "permission_profile" not in result

    def test_customize_to_ddb_with_none_permission_profile(self):
        """Test _customize_to_ddb handles None permission_profile."""
        input_data = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
            "permission_profile": None,
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["idea_session_id"] == "session-123"
        assert result["actor_name"] == "user1"
        assert result["permission_profile_id"] is None
        assert "permission_profile" not in result

    def test_customize_to_ddb_without_permission_profile(self):
        """Test _customize_to_ddb handles missing permission_profile field."""
        input_data = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
            "actor_type": "USER"
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["idea_session_id"] == "session-123"
        assert result["actor_name"] == "user1"
        assert result["actor_type"] == "USER"
        assert result["permission_profile_id"] is None

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_with_permission_profile_id(self, mock_timestamps_to_iso):
        """Test _customize_from_ddb creates permission_profile object correctly."""
        input_data = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
            "actor_type": "USER",
            "permission_profile_id": "profile-456"
        }

        # Mock should return the data that gets passed to it (which includes permission_profile)
        mock_timestamps_to_iso.side_effect = lambda data, *args: data

        result = self.serializer._customize_from_ddb(input_data)
        
        assert result["idea_session_id"] == "session-123"
        assert result["actor_name"] == "user1"
        assert result["actor_type"] == "USER"
        assert result["permission_profile"] == {"profile_id": "profile-456"}

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_with_none_permission_profile_id(self, mock_timestamps_to_iso):
        """Test _customize_from_ddb handles None permission_profile_id."""
        input_data = {
            "idea_session_id": "session-123",
            "actor_name": "user1",
            "permission_profile_id": None
        }

        mock_timestamps_to_iso.side_effect = lambda data, *args: data

        result = self.serializer._customize_from_ddb(input_data)
        
        assert result["idea_session_id"] == "session-123"
        assert result["actor_name"] == "user1"
        assert result["permission_profile"] == {"profile_id": None}

    @patch("datamodel.serializers.base_serializer.SerializerUtils.timestamps_to_iso")
    def test_customize_from_ddb_without_permission_profile_id(self, mock_timestamps_to_iso):
        """Test _customize_from_ddb handles missing permission_profile_id field."""
        input_data = {
            "idea_session_id": "session-123",
            "actor_name": "user1"
        }

        mock_timestamps_to_iso.side_effect = lambda data, *args: data

        result = self.serializer._customize_from_ddb(input_data)
        
        assert result["idea_session_id"] == "session-123"
        assert result["actor_name"] == "user1"
        assert result["permission_profile"] == {"profile_id": None}

    def test_customize_to_ddb_permission_profile_missing_profile_id(self):
        """Test _customize_to_ddb handles permission_profile missing profile_id."""
        input_data = {
            "idea_session_id": "session-123",
            "permission_profile": {
                "title": "Test Profile"
                # Missing profile_id
            }
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["idea_session_id"] == "session-123"
        assert result["permission_profile_id"] is None
        assert "permission_profile" not in result
