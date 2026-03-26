#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
from typing import Dict, Optional
from unittest.mock import patch

import pytest
import res as res
import res.exceptions as exceptions
from res.resources import permission_profiles as profiles
from res.utils import table_utils

TEST_PROFILE_ID = "test_profile_id"
TEST_PROFILE_ID_2 = "test_profile_id_added"
TEST_TITLE = "Test title"
TEST_TITLE_2 = "Test title added"
TEST_DESCRIPTION = "Test description"
TEST_DESCRIPTION_2 = "Test description added"
RANDOM_TEST_PROFILE_ID = "random_profile_id"


class PermissionProfilesTestContext:
    permission_profile: Optional[Dict]


class TestPermissionProfiles(unittest.TestCase):

    def setUp(self):
        self.context: PermissionProfilesTestContext = PermissionProfilesTestContext()
        self.context.permission_profile = {
            profiles.PERMISSION_PROFILE_DB_HASH_KEY: TEST_PROFILE_ID,
            profiles.PERMISSION_PROFILE_DB_TITLE_KEY: TEST_TITLE,
            profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY: TEST_DESCRIPTION,
            "builtin": True,
        }
        table_utils.create_item(
            profiles.PERMISSION_PROFILE_TABLE_NAME, item=self.context.permission_profile
        )

    def tearDown(self):
        """Clean up test data after each test"""
        # Clean up test profiles that might have been created during tests
        test_profile_ids = [TEST_PROFILE_ID, TEST_PROFILE_ID_2]

        for profile_id in test_profile_ids:
            try:
                # Try to delete the profile if it exists
                table_utils.delete_item(
                    profiles.PERMISSION_PROFILE_TABLE_NAME,
                    key={profiles.PERMISSION_PROFILE_DB_HASH_KEY: profile_id},
                )
            except Exception:
                # Profile might not exist, which is fine
                pass

    def test_permission_profiles_get_invalid_profile_should_fail(self):
        """
        get permission profile failure
        """
        # invalid profile_id
        with pytest.raises(exceptions.PermissionProfileNotFound) as exc_info:
            profiles.get_permission_profile(profile_id=RANDOM_TEST_PROFILE_ID)
        assert f"Permission profile not found" in exc_info.value.args[0]

    def test_permission_profiles_get_valid_profile_should_pass(self):
        """
        get permission profile success
        """
        result = profiles.get_permission_profile(profile_id=TEST_PROFILE_ID)
        assert result is not None
        assert result.get(profiles.PERMISSION_PROFILE_DB_HASH_KEY) == TEST_PROFILE_ID
        assert result.get(profiles.PERMISSION_PROFILE_DB_TITLE_KEY) == TEST_TITLE
        assert (
            result.get(profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY)
            == TEST_DESCRIPTION
        )
        assert result.get("builtin") == True

    def test_permission_profiles_create_profile_should_pass(self):
        """
        create permission profile success
        """
        created_permission_profile = profiles.create_permission_profile(
            permission_profile={
                profiles.PERMISSION_PROFILE_DB_HASH_KEY: TEST_PROFILE_ID_2,
                profiles.PERMISSION_PROFILE_DB_TITLE_KEY: TEST_TITLE_2,
                profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY: TEST_DESCRIPTION_2,
                "builtin": False,
            }
        )

        assert (
            created_permission_profile[profiles.PERMISSION_PROFILE_DB_HASH_KEY]
            is not None
        )
        assert (
            created_permission_profile[profiles.PERMISSION_PROFILE_DB_TITLE_KEY]
            is not None
        )
        assert (
            created_permission_profile[profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY]
            is not None
        )
        assert created_permission_profile["builtin"] is False

        permission_profile = profiles.get_permission_profile(
            profile_id=TEST_PROFILE_ID_2
        )
        assert permission_profile is not None
        assert permission_profile.get(
            profiles.PERMISSION_PROFILE_DB_HASH_KEY
        ) == created_permission_profile.get(profiles.PERMISSION_PROFILE_DB_HASH_KEY)
        assert permission_profile.get(
            profiles.PERMISSION_PROFILE_DB_TITLE_KEY
        ) == created_permission_profile.get(profiles.PERMISSION_PROFILE_DB_TITLE_KEY)
        assert permission_profile.get(
            profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY
        ) == created_permission_profile.get(
            profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY
        )
        assert permission_profile.get("builtin") == created_permission_profile.get(
            "builtin"
        )

    @patch("res.resources.permission_profiles.events_client")
    @patch(
        "res.resources.permission_profiles._propagate_globally_disabled_desktop_permissions"
    )
    def test_permission_profiles_update_profile_should_pass(
        self,
        mock_propagate_globally_disabled_desktop_permissions,
        mock_events_client,
    ):
        """
        update permission profile success
        """
        updated_data = {
            profiles.PERMISSION_PROFILE_DB_HASH_KEY: TEST_PROFILE_ID,
            profiles.PERMISSION_PROFILE_DB_TITLE_KEY: "Updated Title",
            profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY: "Updated Description",
            "builtin": False,
        }

        updated_permission_profile = profiles.update_permission_profile(
            permission_profile=updated_data
        )

        mock_events_client.publish_update_event.assert_called_once()
        mock_propagate_globally_disabled_desktop_permissions.assert_called_once()

        assert updated_permission_profile is not None
        assert (
            updated_permission_profile[profiles.PERMISSION_PROFILE_DB_HASH_KEY]
            == TEST_PROFILE_ID
        )
        assert (
            updated_permission_profile[profiles.PERMISSION_PROFILE_DB_TITLE_KEY]
            == "Updated Title"
        )
        assert (
            updated_permission_profile[profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY]
            == "Updated Description"
        )
        assert updated_permission_profile["builtin"] is False
        assert (
            profiles.PERMISSION_PROFILE_DB_UPDATED_ON_KEY in updated_permission_profile
        )

    def test_permission_profiles_delete_profile_should_pass(self):
        """
        delete permission profile success
        """
        # Verify profile exists before deletion
        result = profiles.get_permission_profile(profile_id=TEST_PROFILE_ID)
        assert result is not None

        # Delete the profile
        profiles.delete_permission_profile(profile_id=TEST_PROFILE_ID)

        # Verify profile no longer exists
        with pytest.raises(exceptions.PermissionProfileNotFound) as exc_info:
            profiles.get_permission_profile(profile_id=TEST_PROFILE_ID)
        assert f"Permission profile not found" in exc_info.value.args[0]

    def test_permission_profiles_delete_invalid_profile_should_fail(self):
        """
        delete permission profile failure
        """
        with pytest.raises(exceptions.PermissionProfileNotFound) as exc_info:
            profiles.delete_permission_profile(profile_id=RANDOM_TEST_PROFILE_ID)
        assert f"Permission profile not found" in exc_info.value.args[0]

    def test_permission_profiles_list_paginated_should_pass(self):
        """
        list permission profiles paginated success
        """
        # Create an additional profile for testing
        profiles.create_permission_profile(
            permission_profile={
                profiles.PERMISSION_PROFILE_DB_HASH_KEY: TEST_PROFILE_ID_2,
                profiles.PERMISSION_PROFILE_DB_TITLE_KEY: TEST_TITLE_2,
                profiles.PERMISSION_PROFILE_DB_DESCRIPTION_KEY: TEST_DESCRIPTION_2,
                "builtin": False,
            }
        )

        # List all profiles
        result, next_token = profiles.list_permission_profiles_paginated()

        assert result is not None
        assert len(result) >= 2  # At least our two test profiles
        assert next_token is None or isinstance(next_token, str)

        # Verify our profiles are in the results
        profile_ids = [
            profile[profiles.PERMISSION_PROFILE_DB_HASH_KEY] for profile in result
        ]
        assert TEST_PROFILE_ID in profile_ids
        assert TEST_PROFILE_ID_2 in profile_ids

    def test_permission_profiles_list_paginated_with_filter_should_pass(self):
        """
        list permission profiles paginated with filter success
        """

        result, next_token = profiles.list_permission_profiles_paginated(
            profile_id=TEST_PROFILE_ID
        )

        assert result is not None
        # All returned profiles should have builtin=True
        for profile in result:
            assert profile.get("profile_id") == TEST_PROFILE_ID

    def test_permission_profiles_is_table_empty_should_return_false(self):
        """
        is_permission_profiles_table_empty should return false when profiles exist
        """
        result = profiles.is_permission_profiles_table_empty()
        assert result is False

    def test_permission_profiles_create_empty_profile_should_fail(self):
        """
        create permission profile with empty data should fail
        """
        with pytest.raises(Exception) as exc_info:
            profiles.create_permission_profile(permission_profile=None)
        assert "Permission profile required" in str(exc_info.value)

    def test_permission_profiles_update_empty_profile_should_fail(self):
        """
        update permission profile with empty data should fail
        """
        with pytest.raises(Exception) as exc_info:
            profiles.update_permission_profile(permission_profile=None)
        assert "Permission profile required" in str(exc_info.value)

    def test_permission_profiles_get_empty_profile_id_should_fail(self):
        """
        get permission profile with empty profile_id should fail
        """
        with pytest.raises(Exception) as exc_info:
            profiles.get_permission_profile(profile_id=None)
        assert "Profile ID required" in str(exc_info.value)

    def test_permission_profiles_delete_empty_profile_id_should_fail(self):
        """
        delete permission profile with empty profile_id should fail
        """
        with pytest.raises(Exception) as exc_info:
            profiles.delete_permission_profile(profile_id=None)
        assert "Profile ID required" in str(exc_info.value)

    @patch("res.resources.permission_profiles.sessions")
    @patch("res.resources.permission_profiles.update_permission_profile")
    @patch("res.resources.permission_profiles.list_permission_profiles_paginated")
    @patch("res.resources.permission_profiles.cluster_settings")
    @patch("res.resources.permission_profiles.events_client")
    def test_propagate_globally_disabled_desktop_permissions_admin_profile(
        self,
        mock_events_client,
        mock_cluster_settings,
        mock_list_permission_profiles_paginated,
        mock_update_permission_profile,
        mock_sessions,
    ):
        """Test propagation of globally disabled permissions for admin profile updates."""
        # Setup mocks
        mock_cluster_settings.get_setting.return_value = TEST_PROFILE_ID

        # Create global admin profile with some permissions disabled
        global_profile = {
            "profile_id": TEST_PROFILE_ID,
            "title": "Admin Profile",
            "permission1": True,
            "permission2": False,
            "permission3": True,
        }

        # Mock existing sharing profiles - use proper DB format with individual permission fields
        sharing_profile_dict = {
            "profile_id": "sharing-profile-1",
            "title": "Sharing Profile",
            "permission1": True,
            "permission2": True,  # Should be disabled
            "permission3": True,
        }

        mock_list_permission_profiles_paginated.return_value = (
            [sharing_profile_dict],
            None,
        )
        mock_update_permission_profile.return_value = sharing_profile_dict

        # Mock existing sessions
        session_dict = {"idea_session_id": "session-1", "owner": "user1"}
        mock_sessions.list_sessions_paginated.return_value = ([session_dict], None)

        # Test
        profiles._propagate_globally_disabled_desktop_permissions(global_profile)

        # Verify cluster settings was checked
        mock_cluster_settings.get_setting.assert_called_once_with(
            "vdc.dcv_session.default_profiles.admin"
        )

        # Verify permission profiles were listed and updated
        mock_list_permission_profiles_paginated.assert_called()
        mock_update_permission_profile.assert_called_once()

        # Verify sessions were listed and events published
        mock_sessions.list_sessions_paginated.assert_called()
        mock_events_client.publish_enforce_session_permissions_event.assert_called_once_with(
            "session-1", "user1"
        )

    @patch("res.resources.permission_profiles.sessions")
    @patch("res.resources.permission_profiles.update_permission_profile")
    @patch("res.resources.permission_profiles.list_permission_profiles_paginated")
    @patch("res.resources.permission_profiles.cluster_settings")
    @patch("res.resources.permission_profiles.events_client")
    def test_propagate_globally_disabled_desktop_permissions_non_admin_profile(
        self,
        mock_events_client,
        mock_cluster_settings,
        mock_list_permission_profiles_paginated,
        mock_update_permission_profile,
        mock_sessions,
    ):
        """Test that propagation is skipped for non-admin profile updates and admin profiles are not updated."""
        # Setup mocks
        admin_profile_id = "admin-profile-1"
        mock_cluster_settings.get_setting.return_value = admin_profile_id

        # Create non-admin profile
        global_profile = {
            "profile_id": TEST_PROFILE_ID,  # Different from admin
            "title": "Regular Profile",
            "permission1": False,
        }

        # Test
        profiles._propagate_globally_disabled_desktop_permissions(global_profile)

        # Verify cluster settings was checked but no further processing occurred
        mock_cluster_settings.get_setting.assert_called_once_with(
            "vdc.dcv_session.default_profiles.admin"
        )

        # Verify that admin profiles are NOT updated for non-admin profile changes
        mock_list_permission_profiles_paginated.assert_not_called()
        mock_update_permission_profile.assert_not_called()
        mock_sessions.list_sessions_paginated.assert_not_called()
        mock_events_client.publish_enforce_session_permissions_event.assert_not_called()

    @patch("res.resources.permission_profiles.sessions")
    @patch("res.resources.permission_profiles.update_permission_profile")
    @patch("res.resources.permission_profiles.list_permission_profiles_paginated")
    @patch("res.resources.permission_profiles.cluster_settings")
    @patch("res.resources.permission_profiles.events_client")
    def test_propagate_globally_disabled_desktop_permissions_pagination(
        self,
        mock_events_client,
        mock_cluster_settings,
        mock_list_permission_profiles_paginated,
        mock_update_permission_profile,
        mock_sessions,
    ):
        """Test that propagation handles pagination correctly."""
        # Setup mocks
        mock_cluster_settings.get_setting.return_value = TEST_PROFILE_ID

        global_profile = {
            "profile_id": TEST_PROFILE_ID,
            "title": "Admin Profile",
            "permission1": False,
        }

        # Mock paginated responses
        mock_list_permission_profiles_paginated.side_effect = [
            ([{"profile_id": "profile-1", "permission1": True}], "token1"),
            ([{"profile_id": "profile-2", "permission1": True}], None),
        ]
        mock_update_permission_profile.return_value = {}

        mock_sessions.list_sessions_paginated.side_effect = [
            ([{"idea_session_id": "session-1", "owner": "user1"}], "token2"),
            ([{"idea_session_id": "session-2", "owner": "user2"}], None),
        ]

        # Test
        profiles._propagate_globally_disabled_desktop_permissions(global_profile)

        # Verify pagination was handled - should be called twice each
        assert mock_list_permission_profiles_paginated.call_count == 2
        assert mock_sessions.list_sessions_paginated.call_count == 2
