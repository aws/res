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
from datamodel.models.backend.create_software_stack_response_content import (
    CreateSoftwareStackResponseContent,
)
from datamodel.models.backend.list_software_stacks_response_content import (
    ListSoftwareStacksResponseContent,
)
from datamodel.models.backend.virtual_desktop_software_stack import (
    VirtualDesktopSoftwareStack,
)
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.software_stacks_table_merger import (
    SoftwareStacksTableMerger,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordActionType,
    MergedRecordDelta,
)

from ideadatamodel.api.api_model import ApiAuthorization, ApiAuthorizationType
from ideadatamodel.snapshots.snapshot_model import TableName


def _http_error_with_body(
    status_code: int, reason: str, body: str
) -> requests.HTTPError:
    """Build an HTTPError mimicking what ResApiClient raises on non-2xx."""
    response = requests.Response()
    response.status_code = status_code
    response.reason = reason
    response._content = body.encode("utf-8")
    return requests.HTTPError(f"{status_code} {reason}", response=response)


def _software_stack_from_db(db_entry: dict) -> VirtualDesktopSoftwareStack:
    """Build a software stack from a DB dict, mirroring how the merger does it."""
    software_stack = VirtualDesktopSoftwareStack.from_ddb_dict(db_entry)
    db_utils.rebuild_software_stack_projects_from_db_dict(software_stack, db_entry)
    return software_stack


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = MonkeyPatch()


@pytest.fixture(scope="class")
def context_for_class(request, context):
    request.cls.context = context


@pytest.mark.usefixtures("monkeypatch_for_class")
@pytest.mark.usefixtures("context_for_class")
class TestSoftwareStacksTableMerger(unittest.TestCase):
    def setUp(self):
        self.monkeypatch.setattr(
            self.context.token_service, "decode_token", lambda token: {}
        )
        self.monkeypatch.setattr(
            self.context.api_authorization_service,
            "get_authorization",
            lambda decoded_token: ApiAuthorization(type=ApiAuthorizationType.USER),
        )

    def _patch_list_returns(self, listing):
        self.monkeypatch.setattr(
            self.context.res_api_client,
            "list_software_stacks",
            lambda **_kwargs: ListSoftwareStacksResponseContent(
                listing=listing, next_token=None
            ),
        )

    def _patch_list_returns_pages(self, pages):
        page_by_token = {None: pages[0]}
        for prev, curr in zip(pages, pages[1:]):
            _, prev_next = prev
            page_by_token[prev_next] = curr

        def _list(**kwargs):
            listing, next_token = page_by_token[kwargs.get("next_token")]
            return ListSoftwareStacksResponseContent(
                listing=listing, next_token=next_token
            )

        self.monkeypatch.setattr(
            self.context.res_api_client, "list_software_stacks", _list
        )

    def test_software_stacks_table_resolver_merge_new_software_stack_succeed(self):
        create_software_stack_called = False

        def _create_software_stack_mock(request_content):
            nonlocal create_software_stack_called
            create_software_stack_called = True
            assert request_content.software_stack.name == "test_software_stack"
            # Simulate the backend assigning a stack_id on create.
            request_content.software_stack.stack_id = "server-generated-stack-id"
            return CreateSoftwareStackResponseContent(
                software_stack=request_content.software_stack
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
        self._patch_list_returns([])

        table_data_to_merge = [
            {
                db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
                db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            },
        ]

        resolver = SoftwareStacksTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            table_data_to_merge,
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("software_stacks_table_resolver")
            ),
        )

        assert success
        assert len(record_deltas) == 1
        assert record_deltas[0].original_record is None
        assert (
            record_deltas[0].snapshot_record.get(db_utils.SOFTWARE_STACK_DB_NAME_KEY)
            == "test_software_stack"
        )
        assert (
            record_deltas[0].resolved_record.get(db_utils.SOFTWARE_STACK_DB_NAME_KEY)
            == "test_software_stack"
        )
        assert (
            record_deltas[0].resolved_record.get(
                db_utils.SOFTWARE_STACK_DB_STACK_ID_KEY
            )
            == "server-generated-stack-id"
        )
        assert record_deltas[0].action_performed == MergedRecordActionType.CREATE
        assert create_software_stack_called

    def test_software_stacks_table_resolver_merge_existing_software_stack_without_allowed_instance_types_list_succeed(
        self,
    ):
        create_software_stack_called = False

        def _create_software_stack_mock(request_content):
            nonlocal create_software_stack_called
            create_software_stack_called = True
            assert request_content.software_stack.name == "test_software_stack_dedup_id"
            # Merger must clear stack_id so the backend can regenerate it.
            assert request_content.software_stack.stack_id is None
            request_content.software_stack.stack_id = "server-generated-stack-id"
            return CreateSoftwareStackResponseContent(
                software_stack=request_content.software_stack
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
        # Existing stack with same name but DIFFERENT ami_id → rename + create.
        existing_software_stack = _software_stack_from_db(
            {
                db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
                db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
                db_utils.SOFTWARE_STACK_DB_AMI_ID_KEY: "ami-existing",
            }
        )
        self._patch_list_returns([existing_software_stack])

        table_data_to_merge = [
            {
                db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
                db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
                db_utils.SOFTWARE_STACK_DB_AMI_ID_KEY: "ami-snapshot",
                db_utils.SOFTWARE_STACK_DB_VERSION_KEY: 3,
            },
        ]

        resolver = SoftwareStacksTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            table_data_to_merge,
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("software_stacks_table_resolver")
            ),
        )

        assert success
        assert len(record_deltas) == 1
        assert record_deltas[0].original_record is None
        assert (
            record_deltas[0].snapshot_record.get(db_utils.SOFTWARE_STACK_DB_NAME_KEY)
            == "test_software_stack"
        )
        assert (
            record_deltas[0].resolved_record.get(db_utils.SOFTWARE_STACK_DB_NAME_KEY)
            == "test_software_stack_dedup_id"
        )
        assert record_deltas[0].action_performed == MergedRecordActionType.CREATE
        assert create_software_stack_called

    def test_software_stacks_table_resolver_rollback_original_data_succeed(self):
        test_stack_id = "test_stack_id"
        test_base_os = "amazonlinux2"
        delete_software_stack_called = False

        def _delete_software_stack_mock(stack_id, request_content):
            nonlocal delete_software_stack_called
            delete_software_stack_called = True
            assert stack_id == test_stack_id
            assert request_content.base_os == test_base_os

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "delete_software_stack",
            _delete_software_stack_mock,
        )

        delta_records = [
            MergedRecordDelta(
                snapshot_record={
                    db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                    db_utils.SOFTWARE_STACK_DB_STACK_ID_KEY: test_stack_id,
                    db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: test_base_os,
                },
                resolved_record={
                    db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                    db_utils.SOFTWARE_STACK_DB_STACK_ID_KEY: test_stack_id,
                    db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: test_base_os,
                },
                action_performed=MergedRecordActionType.CREATE,
            ),
        ]

        resolver = SoftwareStacksTableMerger()
        resolver.rollback(
            self.context,
            delta_records,
            ApplySnapshotObservabilityHelper(
                self.context.logger("users_table_resolver")
            ),
        )

        assert delete_software_stack_called

    def test_software_stacks_table_resolver_finds_match_across_pages_succeed(self):
        """When list_software_stacks paginates, the merger must scan all pages
        before deciding the snapshot stack is new."""
        create_software_stack_called = False

        def _create_software_stack_mock(request_content):
            nonlocal create_software_stack_called
            create_software_stack_called = True
            return CreateSoftwareStackResponseContent(
                software_stack=request_content.software_stack
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_software_stack",
            _create_software_stack_mock,
        )

        # Existing stack on page 2 is equal to the snapshot record → merger
        # should detect the match and skip CREATE.
        db_entry = {
            db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
            db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
            db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
            db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
            db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
            db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
            db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            db_utils.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }
        unrelated_db_entry = {
            **db_entry,
            db_utils.SOFTWARE_STACK_DB_AMI_ID_KEY: "ami-different",
        }
        self._patch_list_returns_pages(
            [
                ([_software_stack_from_db(unrelated_db_entry)], "page-2-token"),
                ([_software_stack_from_db(db_entry)], None),
            ]
        )

        resolver = SoftwareStacksTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            [dict(db_entry)],
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("software_stacks_table_resolver")
            ),
        )

        assert success
        assert len(record_deltas) == 0
        assert not create_software_stack_called

    def test_software_stacks_table_resolver_resolve_project_id_succeed(self):
        def _create_software_stack_mock(request_content):
            request_content.software_stack.stack_id = "server-generated-stack-id"
            return CreateSoftwareStackResponseContent(
                software_stack=request_content.software_stack
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
        self._patch_list_returns([])
        table_data_to_merge = [
            {
                db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
                db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
                db_utils.SOFTWARE_STACK_DB_PROJECTS_KEY: ["snapshot_project_id"],
            },
        ]

        resolver = SoftwareStacksTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            table_data_to_merge,
            "dedup_id",
            {
                TableName.PROJECTS_TABLE_NAME: [
                    MergedRecordDelta(
                        snapshot_record={"project_id": "snapshot_project_id"},
                        resolved_record={"project_id": "resolved_project_id"},
                    )
                ]
            },
            ApplySnapshotObservabilityHelper(
                self.context.logger("software_stacks_table_resolver")
            ),
        )

        assert success
        assert len(record_deltas) == 1
        assert record_deltas[0].original_record is None
        # ``resolved_record`` after CREATE is the post-create DB shape from the
        # backend response; backend echoed the rebuilt projects.
        assert len(record_deltas[0].resolved_record.get("projects")) == 1
        assert record_deltas[0].resolved_record["projects"][0] == "resolved_project_id"

    def test_software_stacks_table_resolver_ignore_unchanged_software_stack_succeed(
        self,
    ):
        create_software_stack_called = False

        def _create_software_stack_mock(request_content):
            nonlocal create_software_stack_called
            create_software_stack_called = True
            return CreateSoftwareStackResponseContent(
                software_stack=request_content.software_stack
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
        # Existing stack with identical compared fields → no CREATE.
        db_entry = {
            db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
            db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
            db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
            db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
            db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
            db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
            db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
            db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
            db_utils.SOFTWARE_STACK_DB_PROJECTS_KEY: ["project_id"],
            db_utils.SOFTWARE_STACK_DB_TENANCY_KEY: "default",
        }
        self._patch_list_returns([_software_stack_from_db(db_entry)])

        resolver = SoftwareStacksTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            [dict(db_entry)],
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("software_stacks_table_resolver")
            ),
        )

        assert success
        assert len(record_deltas) == 0
        assert not create_software_stack_called

    def test_software_stacks_table_resolver_ignore_software_stack_with_invalid_ami_id_succeed(
        self,
    ):
        def _create_software_stack_mock(_request_content):
            raise _http_error_with_body(
                400,
                "Bad Request",
                '{"message": "Invalid software_stack.ami_id: ami-bad"}',
            )

        self.monkeypatch.setattr(
            self.context.res_api_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
        self._patch_list_returns([])

        table_data_to_merge = [
            {
                db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: "amazonlinux2",
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
                db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
                db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
                db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
                db_utils.SOFTWARE_STACK_DB_PROJECTS_KEY: ["project_id"],
            },
        ]

        resolver = SoftwareStacksTableMerger()
        record_deltas, success = resolver.merge(
            self.context,
            table_data_to_merge,
            "dedup_id",
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("software_stacks_table_resolver")
            ),
        )

        assert success
        assert len(record_deltas) == 0
