#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
from typing import Dict, Optional

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

    def test_permission_profiles_create_profile_with_duplicate_id_should_fail(self):
        with pytest.raises(Exception) as exc_info:
            profiles.create_permission_profile(
                permission_profile={
                    profiles.PERMISSION_PROFILE_DB_HASH_KEY: TEST_PROFILE_ID,
                    profiles.PERMISSION_PROFILE_DB_TITLE_KEY: TEST_TITLE_2,
                }
            )
        assert "already exists" in exc_info.value.args[0]

    def test_permission_profiles_create_profile_without_id_should_fail(self):
        with pytest.raises(Exception) as exc_info:
            profiles.create_permission_profile(
                permission_profile={
                    profiles.PERMISSION_PROFILE_DB_TITLE_KEY: TEST_TITLE_2
                }
            )
        assert "profile_id is required" in exc_info.value.args[0]

    def test_permission_profiles_create_profile_without_title_should_fail(self):
        with pytest.raises(Exception) as exc_info:
            profiles.create_permission_profile(
                permission_profile={
                    profiles.PERMISSION_PROFILE_DB_HASH_KEY: TEST_PROFILE_ID,
                }
            )
        assert "title is required" in exc_info.value.args[0]
