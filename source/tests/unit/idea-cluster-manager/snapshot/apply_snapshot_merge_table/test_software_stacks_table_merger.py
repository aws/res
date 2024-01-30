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
from _pytest.monkeypatch import MonkeyPatch
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

from ideadatamodel import (
    Project,
    SocaMemory,
    SocaMemoryUnit,
    VirtualDesktopArchitecture,
    VirtualDesktopBaseOS,
    VirtualDesktopGPU,
    VirtualDesktopSoftwareStack,
    errorcodes,
    exceptions,
)
from ideadatamodel.api.api_model import ApiAuthorization, ApiAuthorizationType
from ideadatamodel.snapshots.snapshot_model import TableName


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

    def test_software_stacks_table_resolver_merge_new_software_stack_succeed(
        self,
    ):
        create_software_stack_called = False

        def _create_software_stack_mock(software_stack):
            nonlocal create_software_stack_called
            create_software_stack_called = True
            assert software_stack.name == "test_software_stack"
            return software_stack

        self.monkeypatch.setattr(
            self.context.vdc_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
        self.monkeypatch.setattr(
            self.context.vdc_client,
            "get_software_stacks_by_name",
            lambda _stack_name: [],
        )

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
        assert record_deltas[0].action_performed == MergedRecordActionType.CREATE
        assert create_software_stack_called

    def test_software_stacks_table_resolver_merge_existing_software_stack_succeed(
        self,
    ):
        create_software_stack_called = False

        def _create_software_stack_mock(software_stack):
            nonlocal create_software_stack_called
            create_software_stack_called = True
            assert software_stack.name == "test_software_stack_dedup_id"
            return software_stack

        self.monkeypatch.setattr(
            self.context.vdc_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
        self.monkeypatch.setattr(
            self.context.vdc_client,
            "get_software_stacks_by_name",
            lambda _stack_name: [
                VirtualDesktopSoftwareStack(name="test_software_stack"),
            ],
        )

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
            == "test_software_stack_dedup_id"
        )
        assert record_deltas[0].action_performed == MergedRecordActionType.CREATE
        assert create_software_stack_called

    def test_software_stacks_table_resolver_rollback_original_data_succeed(self):
        test_stack_id = "test_stack_id"
        test_base_os = "amazonlinux2"
        delete_software_stack_called = False

        def _delete_software_stack_mock(software_stack: VirtualDesktopSoftwareStack):
            nonlocal delete_software_stack_called
            delete_software_stack_called = True
            assert software_stack.stack_id == test_stack_id
            assert software_stack.base_os == test_base_os

        self.monkeypatch.setattr(
            self.context.vdc_client,
            "delete_software_stack",
            _delete_software_stack_mock,
        )

        delta_records = [
            MergedRecordDelta(
                snapshot_record={
                    db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                    db_utils.SOFTWARE_STACK_DB_STACK_ID_KEY: test_stack_id,
                    db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: test_base_os,
                    db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
                    db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
                    db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
                    db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
                    db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
                    db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
                },
                resolved_record={
                    db_utils.SOFTWARE_STACK_DB_NAME_KEY: "test_software_stack",
                    db_utils.SOFTWARE_STACK_DB_STACK_ID_KEY: test_stack_id,
                    db_utils.SOFTWARE_STACK_DB_BASE_OS_KEY: test_base_os,
                    db_utils.SOFTWARE_STACK_DB_MIN_RAM_VALUE_KEY: 10.0,
                    db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_VALUE_KEY: 10.0,
                    db_utils.SOFTWARE_STACK_DB_MIN_RAM_UNIT_KEY: "gb",
                    db_utils.SOFTWARE_STACK_DB_MIN_STORAGE_UNIT_KEY: "gb",
                    db_utils.SOFTWARE_STACK_DB_ARCHITECTURE_KEY: "x86_64",
                    db_utils.SOFTWARE_STACK_DB_GPU_KEY: "NO_GPU",
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

    def test_software_stacks_table_resolver_resolve_project_id_succeed(self):
        def _create_software_stack_mock(software_stack):
            return software_stack

        self.monkeypatch.setattr(
            self.context.vdc_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
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
        assert len(record_deltas[0].resolved_record.get("projects")) == 1
        assert record_deltas[0].resolved_record["projects"][0] == "resolved_project_id"

    def test_software_stacks_table_resolver_ignore_unchanged_software_stack_succeed(
        self,
    ):
        create_software_stack_called = False

        def _create_software_stack_mock(software_stack):
            nonlocal create_software_stack_called
            create_software_stack_called = True
            return software_stack

        self.monkeypatch.setattr(
            self.context.vdc_client,
            "create_software_stack",
            _create_software_stack_mock,
        )
        self.monkeypatch.setattr(
            self.context.vdc_client,
            "get_software_stacks_by_name",
            lambda _stack_name: [
                VirtualDesktopSoftwareStack(
                    name="test_software_stack",
                    base_os=VirtualDesktopBaseOS.AMAZON_LINUX2,
                    min_storage=SocaMemory(value=10, unit=SocaMemoryUnit.GB),
                    min_ram=SocaMemory(value=10, unit=SocaMemoryUnit.GB),
                    architecture=VirtualDesktopArchitecture.X86_64,
                    gpu=VirtualDesktopGPU.NO_GPU,
                    projects=[Project(project_id="project_id")],
                ),
            ],
        )

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
        assert not create_software_stack_called

    def test_software_stacks_table_resolver_ignore_software_stack_with_invalid_ami_id_succeed(
        self,
    ):
        create_software_stack_called = False

        def _create_software_stack_mock(_software_stack):
            raise exceptions.SocaException(
                error_code=errorcodes.INVALID_PARAMS,
                message="Invalid software_stack.ami_id",
            )

        self.monkeypatch.setattr(
            self.context.vdc_client,
            "create_software_stack",
            _create_software_stack_mock,
        )

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
        assert not create_software_stack_called
