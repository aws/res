import unittest

import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.filesystems_cluster_settings_table_merger import (
    FileSystemsClusterSettingTableMerger,
)
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import (
    MergeTable,
)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplySnapshotObservabilityHelper,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordActionType,
    MergedRecordDelta,
)

from ideadatamodel import (
    AddFileSystemToProjectRequest,
    OffboardFileSystemRequest,
    OnboardEFSFileSystemRequest,
    errorcodes,
    exceptions,
)


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = MonkeyPatch()


@pytest.fixture(scope="class")
def context_for_class(request, context):
    request.cls.context = context


def dummy_unique_resource_id_generator(key, dedup_id):
    return f"{key}_{dedup_id}"


DUMMY_DEDUP_ID = "dedup_id"

DUMMY_EFS_1 = "dummy_efs_1"
DUMMY_ONTAP_1 = "dummy_ontap_1"

DUMMY_EFS_1_DEDUP = dummy_unique_resource_id_generator(DUMMY_EFS_1, DUMMY_DEDUP_ID)
DUMMY_ONTAP_1_DEDUP = dummy_unique_resource_id_generator(DUMMY_ONTAP_1, DUMMY_DEDUP_ID)

DUMMY_EFS_FILESYSTEM_ID = "fs-efs-1-id"
DUMMY_ONTAP_FLESYSTEM_ID = "fs-ontap-1-id"

DUMMY_PROJECT_NAME = "dummy_project"

dummy_snapshot_filesystem_details_in_dict = {
    DUMMY_EFS_1: {
        "efs": {
            "cloudwatch_monitoring": "false",
            "dns": "fs-efs-1-id.efs.us-east-1.amazonaws.com",
            "encrypted": "true",
            "file_system_id": DUMMY_EFS_FILESYSTEM_ID,
            "kms_key_id": "arn:aws:kms:us-east-1:1234",
            "performance_mode": "generalPurpose",
            "removal_policy": "RETAIN",
            "throughput_mode": "elastic",
            "transition_to_ia": "AFTER_30_DAYS",
        },
        "mount_dir": "/efs-1",
        "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
        "projects": [DUMMY_PROJECT_NAME],
        "provider": "efs",
        "scope": ["project"],
        "title": "efs-1",
    },
    DUMMY_ONTAP_1: {
        "fsx_netapp_ontap": {
            "file_system_id": DUMMY_ONTAP_FLESYSTEM_ID,
            "removal_policy": "RETAIN",
            "svm": {
                "iscsi_dns": "iscsi.svm-1234.fs-1234.fsx.us-east-1.amazonaws.com",
                "management_dns": "svm-1234.fs-1234.fsx.us-east-1.amazonaws.com",
                "nfs_dns": "svm-1234.fs-1234.fsx.us-east-1.amazonaws.com",
                "smb_dns": "null",
                "svm_id": "svm-1234",
            },
            "use_existing_fs": "true",
            "volume": {
                "cifs_share_name": "share_name",
                "security_style": "null",
                "volume_id": "fsvol-1234",
                "volume_path": "/vol1",
            },
        },
        "mount_dir": "/ontap-1",
        "mount_drive": "X",
        "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
        "projects": [DUMMY_PROJECT_NAME],
        "provider": "fsx_netapp_ontap",
        "scope": ["project"],
        "title": "ontap_1",
    },
}


@pytest.mark.usefixtures("monkeypatch_for_class")
@pytest.mark.usefixtures("context_for_class")
class FileSystemClusterSettingsTableMergerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.monkeypatch.setattr(
            FileSystemsClusterSettingTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_snapshot_filesystem_details_in_dict,
        )
        self.monkeypatch.setattr(
            FileSystemsClusterSettingTableMerger,
            "_wait_for_onboarded_filesystem_to_sync_to_config_tree",
            lambda x, y, z: None,
        )
        self.monkeypatch.setattr(
            FileSystemsClusterSettingTableMerger,
            "get_list_of_onboarded_filesystem_ids",
            lambda x, y: [],
        )
        self.monkeypatch.setattr(
            FileSystemsClusterSettingTableMerger,
            "get_list_of_accessible_filesystem_ids",
            lambda x, y: [DUMMY_EFS_FILESYSTEM_ID, DUMMY_ONTAP_FLESYSTEM_ID],
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem, "onboard_efs_filesystem", lambda x: None
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem, "onboard_ontap_filesystem", lambda x: None
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem, "add_filesystem_to_project", lambda x: None
        )
        self.monkeypatch.setattr(
            MergeTable,
            "unique_resource_id_generator",
            dummy_unique_resource_id_generator,
        )
        self.context.projects.projects_dao.create_project(
            {
                "project_id": "dummy_project_id",
                "created_on": 0,
                "description": "dummy_project",
                "enable_budgets": False,
                "enabled": True,
                "ldap_groups": ["test_group_1"],
                "name": DUMMY_PROJECT_NAME,
                "title": "dummy_project",
                "updated_on": 0,
                "users": [],
            }
        )

    def test_filesystems_cluster_settings_table_merger_new_filesystem_succeed(self):
        def dummy_get_filesystem(filesystem_name):
            raise exceptions.soca_exception(
                error_code=errorcodes.FILESYSTEM_NOT_FOUND,
                message=f"could not find filesystem {filesystem_name}",
            )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "get_filesystem",
            lambda filesystem_name: dummy_get_filesystem(filesystem_name),
        )

        merger = FileSystemsClusterSettingTableMerger()

        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 2

        merged_filesystem_names = []
        for record in record_deltas:
            assert record.action_performed == MergedRecordActionType.CREATE
            merged_filesystem_names.append(list(record.resolved_record.keys())[0])

        assert DUMMY_EFS_1 in merged_filesystem_names
        assert DUMMY_EFS_1_DEDUP not in merged_filesystem_names

        assert DUMMY_ONTAP_1 in merged_filesystem_names
        assert DUMMY_ONTAP_1_DEDUP not in merged_filesystem_names

    def test_filesystem_cluster_settings_table_merger_non_project_scope_filesystem_skipped(
        self,
    ):
        efs_details = {
            "efs": {
                "cloudwatch_monitoring": "false",
                "dns": "fs-efs-1-id.efs.us-east-1.amazonaws.com",
                "encrypted": "true",
                "file_system_id": DUMMY_EFS_FILESYSTEM_ID,
                "kms_key_id": "arn:aws:kms:us-east-1:1234",
                "performance_mode": "generalPurpose",
                "removal_policy": "RETAIN",
                "throughput_mode": "elastic",
                "transition_to_ia": "AFTER_30_DAYS",
            },
            "mount_dir": "/efs-1",
            "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
            "projects": ["test-p-1", "efs-p", "res-integ-test-1"],
            "provider": "efs",
            "scope": ["project"],
            "title": "efs-1",
        }
        dummy_non_project_scope_filesystem_details_in_dict = {
            "dummy_cluster_efs": {**efs_details, "scope": ["cluster"]},
            "dummy_module_efs": {**efs_details, "scope": ["module"]},
        }

        self.monkeypatch.setattr(
            FileSystemsClusterSettingTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_non_project_scope_filesystem_details_in_dict,
        )

        merger = FileSystemsClusterSettingTableMerger()

        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 0

    def test_filesystems_cluster_settings_table_merger_existing_filesystem_succeed(
        self,
    ):
        def dummy_get_filesystem(filesystem_name):
            if filesystem_name == DUMMY_EFS_1:
                return {}
            raise exceptions.soca_exception(
                error_code=errorcodes.FILESYSTEM_NOT_FOUND,
                message=f"could not find filesystem {filesystem_name}",
            )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "get_filesystem",
            lambda filesystem_name: dummy_get_filesystem(filesystem_name),
        )

        merger = FileSystemsClusterSettingTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 2

        merged_filesystem_names = []
        for record in record_deltas:
            assert record.action_performed == MergedRecordActionType.CREATE
            merged_filesystem_names.append(list(record.resolved_record.keys())[0])

        assert DUMMY_EFS_1 not in merged_filesystem_names
        assert DUMMY_EFS_1_DEDUP in merged_filesystem_names

        assert DUMMY_ONTAP_1 in merged_filesystem_names
        assert DUMMY_ONTAP_1_DEDUP not in merged_filesystem_names

    def test_filesystem_cluster_settings_table_merger_adds_existing_project_to_file_system(
        self,
    ):
        def dummy_get_filesystem(filesystem_name):
            return {}

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "get_filesystem",
            lambda filesystem_name: dummy_get_filesystem(filesystem_name),
        )

        dummy_filesystem_details_in_dict = {
            "dummy_cluster_efs": {
                "efs": {
                    "cloudwatch_monitoring": "false",
                    "dns": "fs-efs-1-id.efs.us-east-1.amazonaws.com",
                    "encrypted": "true",
                    "file_system_id": DUMMY_EFS_FILESYSTEM_ID,
                    "kms_key_id": "arn:aws:kms:us-east-1:1234",
                    "performance_mode": "generalPurpose",
                    "removal_policy": "RETAIN",
                    "throughput_mode": "elastic",
                    "transition_to_ia": "AFTER_30_DAYS",
                },
                "mount_dir": "/efs-1",
                "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
                "projects": [DUMMY_PROJECT_NAME],
                "provider": "efs",
                "scope": ["project"],
                "title": "efs-1",
            },
        }

        add_file_system_to_project_called = False

        def dummy_add_filesystem_to_project(request: AddFileSystemToProjectRequest):
            nonlocal add_file_system_to_project_called
            add_file_system_to_project_called = True

        self.monkeypatch.setattr(
            FileSystemsClusterSettingTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_filesystem_details_in_dict,
        )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "add_filesystem_to_project",
            dummy_add_filesystem_to_project,
        )

        merger = FileSystemsClusterSettingTableMerger()
        merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert add_file_system_to_project_called

    def test_filesystem_cluster_settings_table_merger_skips_adding_nonexisting_project_to_file_system(
        self,
    ):
        def dummy_get_filesystem(filesystem_name):
            return {}

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "get_filesystem",
            lambda filesystem_name: dummy_get_filesystem(filesystem_name),
        )

        dummy_filesystem_details_in_dict = {
            "dummy_cluster_efs": {
                "efs": {
                    "cloudwatch_monitoring": "false",
                    "dns": "fs-efs-1-id.efs.us-east-1.amazonaws.com",
                    "encrypted": "true",
                    "file_system_id": DUMMY_EFS_FILESYSTEM_ID,
                    "kms_key_id": "arn:aws:kms:us-east-1:1234",
                    "performance_mode": "generalPurpose",
                    "removal_policy": "RETAIN",
                    "throughput_mode": "elastic",
                    "transition_to_ia": "AFTER_30_DAYS",
                },
                "mount_dir": "/efs-1",
                "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
                "projects": ["nonexisting-project"],
                "provider": "efs",
                "scope": ["project"],
                "title": "efs-1",
            },
        }

        add_file_system_to_project_called = False

        def dummy_add_filesystem_to_project(request: AddFileSystemToProjectRequest):
            nonlocal add_file_system_to_project_called
            add_file_system_to_project_called = True

        self.monkeypatch.setattr(
            FileSystemsClusterSettingTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_filesystem_details_in_dict,
        )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "add_filesystem_to_project",
            dummy_add_filesystem_to_project,
        )

        merger = FileSystemsClusterSettingTableMerger()
        merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert not add_file_system_to_project_called

    def test_filesystem_cluster_settings_table_merger_adds_dedup_project_to_filesystem_if_exists(
        self,
    ):
        self.context.projects.projects_dao.create_project(
            {
                "project_id": "dummy_project_id",
                "created_on": 0,
                "description": "dummy_project",
                "enable_budgets": False,
                "enabled": True,
                "ldap_groups": ["test_group_1"],
                "name": dummy_unique_resource_id_generator(
                    DUMMY_PROJECT_NAME, DUMMY_DEDUP_ID
                ),
                "title": "dummy_project",
                "updated_on": 0,
                "users": [],
            }
        )

        def dummy_get_filesystem(filesystem_name):
            return {}

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "get_filesystem",
            lambda filesystem_name: dummy_get_filesystem(filesystem_name),
        )

        dummy_filesystem_details_in_dict = {
            "dummy_cluster_efs": {
                "efs": {
                    "cloudwatch_monitoring": "false",
                    "dns": "fs-efs-1-id.efs.us-east-1.amazonaws.com",
                    "encrypted": "true",
                    "file_system_id": DUMMY_EFS_FILESYSTEM_ID,
                    "kms_key_id": "arn:aws:kms:us-east-1:1234",
                    "performance_mode": "generalPurpose",
                    "removal_policy": "RETAIN",
                    "throughput_mode": "elastic",
                    "transition_to_ia": "AFTER_30_DAYS",
                },
                "mount_dir": "/efs-1",
                "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
                "projects": [DUMMY_PROJECT_NAME],
                "provider": "efs",
                "scope": ["project"],
                "title": "efs-1",
            },
        }

        add_file_system_to_project_called = False

        def dummy_add_filesystem_to_project(request: AddFileSystemToProjectRequest):
            nonlocal add_file_system_to_project_called
            add_file_system_to_project_called = True

            assert request.project_name == dummy_unique_resource_id_generator(
                DUMMY_PROJECT_NAME, DUMMY_DEDUP_ID
            )

        self.monkeypatch.setattr(
            FileSystemsClusterSettingTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_filesystem_details_in_dict,
        )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "add_filesystem_to_project",
            dummy_add_filesystem_to_project,
        )

        merger = FileSystemsClusterSettingTableMerger()
        merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert add_file_system_to_project_called

    def test_filesystem_cluter_settings_table_merger_skips_already_onboarded_filesystem(
        self,
    ):
        def dummy_get_filesystem(filesystem_name):
            return {}

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "get_filesystem",
            lambda filesystem_name: dummy_get_filesystem(filesystem_name),
        )

        def dummy_onboard_efs_filesystem(request: OnboardEFSFileSystemRequest):
            if (
                request.filesystem_name == DUMMY_EFS_1
                or request.filesystem_name == DUMMY_EFS_1_DEDUP
            ):
                raise exceptions.soca_exception(
                    error_code=errorcodes.FILESYSTEM_ALREADY_ONBOARDED,
                    message="dummy_message",
                )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "onboard_efs_filesystem",
            dummy_onboard_efs_filesystem,
        )

        merger = FileSystemsClusterSettingTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 1

    def test_filesystem_cluter_settings_table_merger_skips_not_accessible_filesystem(
        self,
    ):
        def dummy_get_filesystem(filesystem_name):
            return {}

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "get_filesystem",
            lambda filesystem_name: dummy_get_filesystem(filesystem_name),
        )

        def dummy_onboard_efs_filesystem(request: OnboardEFSFileSystemRequest):
            if (
                request.filesystem_name == DUMMY_EFS_1
                or request.filesystem_name == DUMMY_EFS_1_DEDUP
            ):
                raise exceptions.soca_exception(
                    error_code=errorcodes.FILESYSTEM_NOT_IN_VPC,
                    message="dummy_message",
                )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "onboard_efs_filesystem",
            dummy_onboard_efs_filesystem,
        )

        merger = FileSystemsClusterSettingTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 1

    def test_filesystem_cluster_settings_table_merger_rollback_succeed(self):
        offboard_filesystem_called = False

        def dummy_offboard_filesystem(request: OffboardFileSystemRequest):
            nonlocal offboard_filesystem_called
            offboard_filesystem_called = True

            assert request.filesystem_name == DUMMY_EFS_1

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "offboard_filesystem",
            lambda filesystem_name: dummy_offboard_filesystem(filesystem_name),
        )

        delta_records = [
            MergedRecordDelta(
                original_record={},
                snapshot_record={},
                resolved_record={DUMMY_EFS_1: {}},
                action_performed=MergedRecordActionType.CREATE,
            ),
        ]

        merger = FileSystemsClusterSettingTableMerger()
        merger.rollback(
            self.context,
            delta_records,
            ApplySnapshotObservabilityHelper(
                self.context.logger("filesystem_cluster_settings_table_merger")
            ),
        )

        assert offboard_filesystem_called
