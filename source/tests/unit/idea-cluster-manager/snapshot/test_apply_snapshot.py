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
from enum import Enum
from logging import Logger
from typing import Dict, List, Tuple
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager.app.snapshots.apply_snapshot import ApplySnapshot
from ideaclustermanager.app.snapshots.apply_snapshot_data_transformation_from_version.abstract_transformation_from_res_version import (
    TransformationFromRESVersion,
)
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import (
    MergeTable,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_version_control_helper import (
    get_table_keys_by_res_version,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshots_config import (
    RES_VERSION_TO_DATA_TRANSFORMATION_CLASS,
    TABLE_TO_TABLE_KEYS_BY_VERSION,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordDelta,
)
from ideaclustermanager.app.snapshots.snapshot_constants import (
    TABLE_EXPORT_DESCRIPTION_KEY,
    VERSION_KEY,
)
from ideasdk.context import SocaContext

from ideadatamodel import errorcodes, exceptions
from ideadatamodel.snapshots import RESVersion, Snapshot, TableKeys, TableName


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = MonkeyPatch()


@pytest.fixture(scope="class")
def context_for_class(request, context):
    request.cls.context = context


class DummyTableName(str, Enum):
    TABLE1 = "table1"
    TABLE2 = "table2"
    TABLE3 = "table3"


class DummyResVersion(str, Enum):
    VERSION1 = "version1"
    VERSION2 = "version2"
    VERSION3 = "version3"


DUMMY_TABLE_TO_TABLE_KEYS_BY_VERSION = {
    DummyTableName.TABLE1: {
        DummyResVersion.VERSION1: TableKeys(partition_key="table1-version1")
    },
    DummyTableName.TABLE2: {
        DummyResVersion.VERSION1: TableKeys(partition_key="table2-version1"),
        DummyResVersion.VERSION2: TableKeys(partition_key="table2-version2"),
    },
    DummyTableName.TABLE3: {
        DummyResVersion.VERSION1: TableKeys(partition_key="table3-version1"),
        DummyResVersion.VERSION2: TableKeys(partition_key="table3-version2"),
        DummyResVersion.VERSION3: TableKeys(partition_key="table3-version3"),
    },
}

DUMMY_RES_VERSION_IN_TOPOLOGICAL_ORDER = [
    DummyResVersion.VERSION1,
    DummyResVersion.VERSION2,
    DummyResVersion.VERSION3,
]

dummy_table_export_descriptions = {
    "table1": "table1",
    "table2": "table2",
    "table4": "table4",
}


class DummyTransformationFromVersion1(TransformationFromRESVersion):
    def transform_data(
        self, env_data_by_table: Dict[TableName, List], logger=Logger
    ) -> Dict[TableName, List]:
        env_data_by_table[DummyTableName.TABLE1].append(
            "Transformation from V1 applied"
        )
        return env_data_by_table


class DummyTransformationFromVersion3(TransformationFromRESVersion):
    def transform_data(
        self, env_data_by_table: Dict[TableName, List], logger=Logger
    ) -> Dict[TableName, List]:
        env_data_by_table[DummyTableName.TABLE1].append(
            "Transformation from V3 applied"
        )
        return env_data_by_table


DUMMY_RES_VERSION_TO_DATA_TRANSFORMATION_CLASS = {
    DummyResVersion.VERSION1: DummyTransformationFromVersion1,
    DummyResVersion.VERSION3: DummyTransformationFromVersion3,
}


ROLLEDBACK = "rolledback"
MERGED = "merged"

MERGE_TABLE_RESULT_TRACKER = {
    DummyTableName.TABLE1: "",
    DummyTableName.TABLE2: "",
    DummyTableName.TABLE3: "",
}

DUMMY_TABLES_IN_MERGE_DEPENDENCY_ORDER = [
    DummyTableName.TABLE1,
    DummyTableName.TABLE2,
    DummyTableName.TABLE3,
]


class MergeTableTable1(MergeTable):
    def merge(
        self,
        context: SocaContext,
        table_data_to_merge: List,
        dedup_id: str,
        merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
        logger=Logger,
    ) -> Tuple[Dict, bool]:
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE1] = MERGED
        return {}, True

    def rollback(self, context: SocaContext, merge_delta: Dict, logger: Logger):
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE1] = ROLLEDBACK


class MergeTableTable2(MergeTable):
    def merge(
        self,
        context: SocaContext,
        table_data_to_merge: List,
        dedup_id: str,
        merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
        logger=Logger,
    ) -> Tuple[Dict, bool]:
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] = MERGED
        return {}, True

    def rollback(self, context: SocaContext, merge_delta: Dict, logger: Logger):
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] = ROLLEDBACK


class MergeTableTable2MergeFail(MergeTable):
    def merge(
        self,
        context: SocaContext,
        table_data_to_merge: List,
        dedup_id: str,
        merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
        logger=Logger,
    ) -> Tuple[Dict, bool]:
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] = MERGED
        return {}, False

    def rollback(self, context: SocaContext, merge_delta: Dict, logger: Logger):
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] = ROLLEDBACK


class MergeTableTable2RollbackFail(MergeTable):
    def merge(
        self,
        context: SocaContext,
        table_data_to_merge: List,
        dedup_id: str,
        merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
        logger=Logger,
    ) -> Tuple[Dict, bool]:
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] = MERGED
        return {}, True

    def rollback(self, context: SocaContext, merge_delta: Dict, logger: Logger):
        raise exceptions.SocaException(
            error_code=errorcodes.GENERAL_ERROR, message="Fake error"
        )


class MergeTableTable3(MergeTable):
    def merge(
        self,
        context: SocaContext,
        table_data_to_merge: List,
        dedup_id: str,
        merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
        logger=Logger,
    ) -> Tuple[Dict, bool]:
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE3] = MERGED
        return {}, True

    def rollback(self, context: SocaContext, merge_delta: Dict, logger: Logger):
        global MERGE_TABLE_RESULT_TRACKER
        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE3] = ROLLEDBACK


class MergeTableTable3MergeFail(MergeTable):
    def merge(
        self,
        context: SocaContext,
        table_data_to_merge: List,
        dedup_id: str,
        merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
        logger=Logger,
    ) -> Tuple[Dict, bool]:
        return {}, False

    def rollback(self, context: SocaContext, merge_delta: Dict, logger: Logger):
        global MERGE_TABLE_RESULT_TRACKER

        MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE3] = ROLLEDBACK


@pytest.mark.usefixtures("monkeypatch_for_class")
@pytest.mark.usefixtures("context_for_class")
class ApplySnapshotsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.apply_snapshot.TableName", DummyTableName
        )
        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.helpers.apply_snapshot_version_control_helper.TableName",
            DummyTableName,
        )
        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.helpers.apply_snapshot_version_control_helper.RESVersion",
            DummyResVersion,
        )
        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.apply_snapshot.RES_VERSION_IN_TOPOLOGICAL_ORDER",
            DUMMY_RES_VERSION_IN_TOPOLOGICAL_ORDER,
        )
        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.helpers.apply_snapshot_version_control_helper.RES_VERSION_IN_TOPOLOGICAL_ORDER",
            DUMMY_RES_VERSION_IN_TOPOLOGICAL_ORDER,
        )
        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.helpers.apply_snapshot_version_control_helper.TABLE_TO_TABLE_KEYS_BY_VERSION",
            DUMMY_TABLE_TO_TABLE_KEYS_BY_VERSION,
        )
        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.apply_snapshot.RES_VERSION_TO_DATA_TRANSFORMATION_CLASS",
            DUMMY_RES_VERSION_TO_DATA_TRANSFORMATION_CLASS,
        )
        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.apply_snapshot.TABLES_IN_MERGE_DEPENDENCY_ORDER",
            DUMMY_TABLES_IN_MERGE_DEPENDENCY_ORDER,
        )
        self.monkeypatch.setattr(
            ApplySnapshot,
            "fetch_snapshot_metadata",
            lambda x: {
                VERSION_KEY: DummyResVersion.VERSION1,
                TABLE_EXPORT_DESCRIPTION_KEY: dummy_table_export_descriptions,
            },
        )

        self.monkeypatch.setattr(ApplySnapshot, "apply_snapshot_main", lambda x: None)

        self.monkeypatch.setattr(
            self.context.snapshots.apply_snapshot_dao,
            "create",
            lambda x, created_on: x,
        )
        self.monkeypatch.setattr(
            self.context.snapshots.apply_snapshot_dao,
            "update_status",
            MagicMock(),
        )

        global MERGE_TABLE_RESULT_TRACKER
        MERGE_TABLE_RESULT_TRACKER = {
            DummyTableName.TABLE1: "",
            DummyTableName.TABLE2: "",
            DummyTableName.TABLE3: "",
        }

    def test_get_table_keys_by_res_version_function(self):
        response = get_table_keys_by_res_version(
            [DummyTableName.TABLE1, DummyTableName.TABLE2, DummyTableName.TABLE3],
            DummyResVersion.VERSION3,
        )

        assert (
            response[DummyTableName.TABLE1]
            == DUMMY_TABLE_TO_TABLE_KEYS_BY_VERSION[DummyTableName.TABLE1][
                DummyResVersion.VERSION1
            ]
        )
        assert (
            response[DummyTableName.TABLE2]
            == DUMMY_TABLE_TO_TABLE_KEYS_BY_VERSION[DummyTableName.TABLE2][
                DummyResVersion.VERSION2
            ]
        )
        assert (
            response[DummyTableName.TABLE3]
            == DUMMY_TABLE_TO_TABLE_KEYS_BY_VERSION[DummyTableName.TABLE3][
                DummyResVersion.VERSION3
            ]
        )

    def test_get_list_of_tables_to_be_imported_function(self):
        obj = ApplySnapshot(
            snapshot=Snapshot(
                s3_bucket_name="some_bucket_name", snapshot_path="valid/path"
            ),
            context=self.context,
            apply_snapshot_dao=self.context.snapshots.apply_snapshot_dao,
        )
        obj.initialize()

        response = obj.get_list_of_tables_to_be_imported()

        assert len(response) == 2

        assert DummyTableName.TABLE1 in response

        assert DummyTableName.TABLE2 in response

        assert DummyTableName.TABLE3 not in response

        # table4 is not identified by the ApplySnapshot process thus is not a key in DummyTableName
        assert "table4" not in response

    def test_key_error_exception_handling_apply_snapshot(self):
        self.monkeypatch.setattr(
            ApplySnapshot,
            "fetch_snapshot_metadata",
            lambda x: {
                "wrong_version_key": DummyResVersion.VERSION2,
                "table_export_description": {},
            },
        )

        with pytest.raises(KeyError) as exc_info:
            obj = ApplySnapshot(
                snapshot=Snapshot(
                    s3_bucket_name="some_bucket_name", snapshot_path="some_path"
                ),
                apply_snapshot_dao=self.context.snapshots.apply_snapshot_dao,
                context=self.context,
            )
            obj.initialize()
        assert "version" in exc_info.value.args[0]

    def test_get_table_keys_by_res_version_exception_handling_apply_snapshot(self):
        dummy_table_to_table_keys_by_version = {
            DummyTableName.TABLE1: {},
            DummyTableName.TABLE2: {},
            DummyTableName.TABLE3: {},
        }

        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.helpers.apply_snapshot_version_control_helper.TABLE_TO_TABLE_KEYS_BY_VERSION",
            dummy_table_to_table_keys_by_version,
        )

        with pytest.raises(Exception) as exc_info:
            obj = ApplySnapshot(
                snapshot=Snapshot(
                    s3_bucket_name="some_bucket_name", snapshot_path="some_path"
                ),
                apply_snapshot_dao=self.context.snapshots.apply_snapshot_dao,
                context=self.context,
            )
            obj.initialize()

        assert (
            "Could not fetch partition_key and sort_key for" in exc_info.value.args[0]
        )

    def test_apply_data_transformation_function(self):
        obj = ApplySnapshot(
            snapshot=Snapshot(
                s3_bucket_name="some_bucket_name", snapshot_path="valid/path"
            ),
            context=self.context,
            apply_snapshot_dao=self.context.snapshots.apply_snapshot_dao,
        )
        obj.initialize()

        data = {DummyTableName.TABLE1: [], DummyTableName.TABLE2: []}

        response = obj.apply_data_transformations(data=data)

        table_1_response = response["table1"]

        assert len(table_1_response) == 2

        assert "Transformation from V1 applied" in table_1_response

        assert "Transformation from V3 applied" in table_1_response

        assert "Transformation from V2 applied" not in table_1_response

    def test_apply_snapshot_merge_function_succeeds(self):
        global MERGE_TABLE_RESULT_TRACKER

        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE1] == ""
        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] == ""
        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE3] == ""

        DUMMY_TABLE_TO_MERGE_LOGIC_CLASS_MERGE_FAIL_TEST = {
            DummyTableName.TABLE1: MergeTableTable1,
            DummyTableName.TABLE2: MergeTableTable2,
            DummyTableName.TABLE3: MergeTableTable3,
        }

        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.apply_snapshot.TABLE_TO_MERGE_LOGIC_CLASS",
            DUMMY_TABLE_TO_MERGE_LOGIC_CLASS_MERGE_FAIL_TEST,
        )

        obj = ApplySnapshot(
            snapshot=Snapshot(
                s3_bucket_name="some_bucket_name", snapshot_path="valid/path"
            ),
            context=self.context,
            apply_snapshot_dao=self.context.snapshots.apply_snapshot_dao,
        )
        obj.initialize()

        obj.merge_transformed_data_for_all_tables({})

        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE1] == MERGED
        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] == MERGED
        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE3] == MERGED

    def test_apply_snapshot_merge_function_handles_merge_failure(self):
        DUMMY_TABLE_TO_MERGE_LOGIC_CLASS_MERGE_FAIL_TEST = return_value = {
            DummyTableName.TABLE1: MergeTableTable1,
            DummyTableName.TABLE2: MergeTableTable2MergeFail,
            DummyTableName.TABLE3: MergeTableTable3,
        }

        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.apply_snapshot.TABLE_TO_MERGE_LOGIC_CLASS",
            DUMMY_TABLE_TO_MERGE_LOGIC_CLASS_MERGE_FAIL_TEST,
        )

        obj = ApplySnapshot(
            snapshot=Snapshot(
                s3_bucket_name="some_bucket_name", snapshot_path="valid/path"
            ),
            context=self.context,
            apply_snapshot_dao=self.context.snapshots.apply_snapshot_dao,
        )
        obj.initialize()

        obj.merge_transformed_data_for_all_tables({})

        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE1] == ROLLEDBACK
        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] == ROLLEDBACK
        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE3] == ""

    def test_apply_snapshot_merge_function_handles_rollback_failure(self):
        DUMMY_TABLE_TO_MERGE_LOGIC_CLASS_MERGE_FAIL_TEST = {
            DummyTableName.TABLE1: MergeTableTable1,
            DummyTableName.TABLE2: MergeTableTable2RollbackFail,
            DummyTableName.TABLE3: MergeTableTable3MergeFail,
        }

        self.monkeypatch.setattr(
            "ideaclustermanager.app.snapshots.apply_snapshot.TABLE_TO_MERGE_LOGIC_CLASS",
            DUMMY_TABLE_TO_MERGE_LOGIC_CLASS_MERGE_FAIL_TEST,
        )

        obj = ApplySnapshot(
            snapshot=Snapshot(
                s3_bucket_name="some_bucket_name", snapshot_path="valid/path"
            ),
            context=self.context,
            apply_snapshot_dao=self.context.snapshots.apply_snapshot_dao,
        )
        obj.initialize()

        obj.merge_transformed_data_for_all_tables({})

        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE1] == MERGED
        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE2] == MERGED
        assert MERGE_TABLE_RESULT_TRACKER[DummyTableName.TABLE3] == ROLLEDBACK


def test_every_table_has_a_corresponding_entry_in_table_to_table_keys_by_version():
    assert len(TableName) == len(TABLE_TO_TABLE_KEYS_BY_VERSION)


def test_every_data_transformation_class_inherits_the_abstarct_class():
    for key in RES_VERSION_TO_DATA_TRANSFORMATION_CLASS:
        assert key in RESVersion

        value = RES_VERSION_TO_DATA_TRANSFORMATION_CLASS[key]

        assert value is not None

        assert TransformationFromRESVersion in value.__bases__
