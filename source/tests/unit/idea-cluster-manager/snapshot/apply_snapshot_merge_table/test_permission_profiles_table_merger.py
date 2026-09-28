#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import unittest

import ideaclustermanager.app.snapshots.helpers.db_utils as db_utils
import pytest
import requests
from _pytest.monkeypatch import MonkeyPatch
from datamodel.models.backend.create_permission_profile_response_content import (
    CreatePermissionProfileResponseContent,
)
from datamodel.models.backend.get_permission_profile_response_content import (
    GetPermissionProfileResponseContent,
)
from datamodel.models.backend.virtual_desktop_permission_profile import (
    VirtualDesktopPermissionProfile,
)
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.permission_profiles_table_merger import (
    PermissionProfilesTableMerger,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordActionType,
    MergedRecordDelta,
)

from ideadatamodel.api.api_model import ApiAuthorization, ApiAuthorizationType


def _http_error(status_code: int, reason: str, body: str = "") -> requests.HTTPError:
    """Build an HTTPError mimicking what ResApiClient raises on non-2xx."""
    response = requests.Response()
    response.status_code = status_code
    response.reason = reason
    if body:
        response._content = body.encode("utf-8")
    return requests.HTTPError(f"{status_code} {reason}", response=response)


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = MonkeyPatch()


@pytest.fixture(scope="class")
def context_for_class(request, context):
    request.cls.context = context


@pytest.mark.usefixtures("monkeypatch_for_class")
@pytest.mark.usefixtures("context_for_class")
class TestPermissionProfilesTableMerger(unittest.TestCase):
    def setUp(self):
        self.monkeypatch.setattr(
            self.context.token_service, "decode_token", lambda token: {}
        )
        self.monkeypatch.setattr(
            self.context.api_authorization_service,
            "get_authorization",
            lambda decoded_token: ApiAuthorization(type=ApiAuthorizationType.USER),
        )

    def test_permission_profiles_table_resolver_merge_new_permission_profile_succeed(
        self,
    ):
        create_permission_profile_called = False

        def _create_permission_profile_mock(request_content):
            nonlocal create_permission_profile_called
            create_permission_profile_called = True
            assert request_content.profile.profile_id == "test_permission_profile"
            return CreatePermissionProfileResponseContent(
                profile=request_content.profile
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_permission_profile",
            _create_permission_profile_mock,
        )

        def _get_permission_profile_mock(_profile_id):
            raise _http_error(
                404, "Not Found", '{"message": "Permission profile not found"}'
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "get_permission_profile",
            _get_permission_profile_mock,
        )

        table_data_to_merge = [
            {db_utils.PERMISSION_PROFILE_DB_HASH_KEY: "test_permission_profile"},
        ]

        resolver = PermissionProfilesTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            table_data_to_merge,
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("permission_profiles_table_resolver")
            ),
        )

        assert success
        assert len(record_deltas) == 1
        assert record_deltas[0].original_record is None
        assert (
            record_deltas[0].snapshot_record.get(
                db_utils.PERMISSION_PROFILE_DB_HASH_KEY
            )
            == "test_permission_profile"
        )
        assert (
            record_deltas[0].resolved_record.get(
                db_utils.PERMISSION_PROFILE_DB_HASH_KEY
            )
            == "test_permission_profile"
        )
        assert record_deltas[0].action_performed == MergedRecordActionType.CREATE
        assert create_permission_profile_called

    def test_permission_profiles_table_resolver_merge_existing_permission_profile_succeed(
        self,
    ):
        create_permission_profile_called = False

        def _create_permission_profile_mock(request_content):
            nonlocal create_permission_profile_called
            create_permission_profile_called = True
            assert (
                request_content.profile.profile_id == "test_permission_profile_dedup_id"
            )
            return CreatePermissionProfileResponseContent(
                profile=request_content.profile
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_permission_profile",
            _create_permission_profile_mock,
        )

        existing_permission_profile = VirtualDesktopPermissionProfile(
            profile_id="test_permission_profile",
            title="existing-title",
            description="",
            permissions=[],
        )
        self.monkeypatch.setattr(
            self.context.res_api_client,
            "get_permission_profile",
            lambda _profile_id: GetPermissionProfileResponseContent(
                profile=existing_permission_profile
            ),
        )

        table_data_to_merge = [
            {db_utils.PERMISSION_PROFILE_DB_HASH_KEY: "test_permission_profile"},
        ]

        resolver = PermissionProfilesTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            table_data_to_merge,
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("permission_profiles_table_resolver")
            ),
        )

        assert success
        assert len(record_deltas) == 1
        assert record_deltas[0].original_record is None
        assert (
            record_deltas[0].snapshot_record.get(
                db_utils.PERMISSION_PROFILE_DB_HASH_KEY
            )
            == "test_permission_profile"
        )
        assert (
            record_deltas[0].resolved_record.get(
                db_utils.PERMISSION_PROFILE_DB_HASH_KEY
            )
            == "test_permission_profile_dedup_id"
        )
        assert record_deltas[0].action_performed == MergedRecordActionType.CREATE
        assert create_permission_profile_called

    def test_permission_profiles_table_resolver_rollback_original_data_succeed(self):
        test_profile_id = "test_permission_profile_dedup_id"
        delete_permission_profile_called = False

        def _delete_permission_profile_mock(profile_id):
            nonlocal delete_permission_profile_called
            delete_permission_profile_called = True
            assert profile_id == test_profile_id

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "delete_permission_profile",
            _delete_permission_profile_mock,
        )

        delta_records = [
            MergedRecordDelta(
                snapshot_record={
                    db_utils.PERMISSION_PROFILE_DB_HASH_KEY: test_profile_id
                },
                resolved_record={
                    db_utils.PERMISSION_PROFILE_DB_HASH_KEY: test_profile_id
                },
                action_performed=MergedRecordActionType.CREATE,
            ),
        ]

        resolver = PermissionProfilesTableMerger()
        resolver.rollback(
            self.context,
            delta_records,
            ApplySnapshotObservabilityHelper(
                self.context.logger("users_table_resolver")
            ),
        )

        assert delete_permission_profile_called

    def test_permission_profiles_table_resolver_ignore_unchanged_permission_profile_succeed(
        self,
    ):
        create_permission_profile_called = False

        def _create_permission_profile_mock(request_content):
            nonlocal create_permission_profile_called
            create_permission_profile_called = True
            return CreatePermissionProfileResponseContent(
                profile=request_content.profile
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_permission_profile",
            _create_permission_profile_mock,
        )

        # Existing profile built from the same db_entry as the snapshot, so
        # the merger should compare them equal and skip CREATE.
        db_entry = {
            db_utils.PERMISSION_PROFILE_DB_HASH_KEY: "test_permission_profile",
            db_utils.PERMISSION_PROFILE_DB_TITLE_KEY: "test_title",
            db_utils.PERMISSION_PROFILE_DB_DESCRIPTION_KEY: "",
        }
        existing_permission_profile = VirtualDesktopPermissionProfile.from_ddb_dict(
            db_entry
        )
        self.monkeypatch.setattr(
            self.context.res_api_client,
            "get_permission_profile",
            lambda _profile_id: GetPermissionProfileResponseContent(
                profile=existing_permission_profile
            ),
        )

        resolver = PermissionProfilesTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            [dict(db_entry)],
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("permission_profiles_table_resolver")
            ),
        )

        assert success
        assert not create_permission_profile_called
        assert len(record_deltas) == 0

    def test_permission_profiles_table_resolver_propagates_non_404_errors(self):
        create_permission_profile_called = False

        def _create_permission_profile_mock(request_content):
            nonlocal create_permission_profile_called
            create_permission_profile_called = True
            return CreatePermissionProfileResponseContent(
                profile=request_content.profile
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_permission_profile",
            _create_permission_profile_mock,
        )

        def _get_permission_profile_mock(_profile_id):
            raise _http_error(500, "Internal Server Error", '{"message": "boom"}')

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "get_permission_profile",
            _get_permission_profile_mock,
        )

        resolver = PermissionProfilesTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            [{db_utils.PERMISSION_PROFILE_DB_HASH_KEY: "test_permission_profile"}],
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("permission_profiles_table_resolver")
            ),
        )

        assert not success
        assert not create_permission_profile_called
        assert len(record_deltas) == 0
