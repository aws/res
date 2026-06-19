import unittest

import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.cluster_settings_table_merger import (
    ClusterSettingsTableMerger,
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
    FileSystem,
    OnboardEFSFileSystemRequest,
    RemoveFileSystemRequest,
    UpdateFileSystemRequest,
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
DUMMY_LUSTRE_1 = "dummy_lustre_1"
DUMMY_S3_BUCKET_1 = "bucket-name-uuid"

DUMMY_EFS_1_DEDUP = dummy_unique_resource_id_generator(DUMMY_EFS_1, DUMMY_DEDUP_ID)
DUMMY_ONTAP_1_DEDUP = dummy_unique_resource_id_generator(DUMMY_ONTAP_1, DUMMY_DEDUP_ID)
DUMMY_LUSTRE_1_DEDUP = dummy_unique_resource_id_generator(
    DUMMY_LUSTRE_1, DUMMY_DEDUP_ID
)
DUMMY_S3_BUCKET_1_DEDUP = dummy_unique_resource_id_generator(
    DUMMY_S3_BUCKET_1, DUMMY_DEDUP_ID
)

DUMMY_EFS_FILESYSTEM_ID = "fs-efs-1-id"
DUMMY_ONTAP_FILESYSTEM_ID = "fs-ontap-1-id"
DUMMY_LUSTRE_FILESYSTEM_ID = "fs-lustre-1-id"
DUMMY_S3_BUCKET_BUCKET_ARN = "arn:aws:s3:::example-bucket"

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
            "file_system_id": DUMMY_ONTAP_FILESYSTEM_ID,
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
    DUMMY_LUSTRE_1: {
        "fsx_lustre": {
            "cloudwatch_monitoring": "false",
            "dns": "fs-lustre-1-id.fsx.us-east-1.amazonaws.com",
            "encrypted": "true",
            "file_system_id": DUMMY_LUSTRE_FILESYSTEM_ID,
            "kms_key_id": "arn:aws:kms:us-east-1:1234",
            "performance_mode": "generalPurpose",
            "removal_policy": "RETAIN",
            "throughput_mode": "elastic",
            "transition_to_ia": "AFTER_30_DAYS",
        },
        "mount_dir": "/lustre-1",
        "mount_options": "lustre defaults,noatime,flock,_netdev 0 0",
        "projects": [DUMMY_PROJECT_NAME],
        "provider": "fsx_lustre",
        "scope": ["project"],
        "title": "lustre-1",
    },
    DUMMY_S3_BUCKET_1: {
        "s3_bucket": {
            "read_only": True,
            "bucket_arn": DUMMY_S3_BUCKET_BUCKET_ARN,
        },
        "mount_dir": "/s3-bucket",
        "provider": "s3_bucket",
        "scope": ["project"],
        "projects": [DUMMY_PROJECT_NAME],
        "title": "s3-bucket-1",
    },
}


@pytest.mark.usefixtures("monkeypatch_for_class")
@pytest.mark.usefixtures("context_for_class")
class ClusterSettingsTableMergerFilesystemTest(unittest.TestCase):
    def setUp(self) -> None:
        self.monkeypatch.setattr(
            ClusterSettingsTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_snapshot_filesystem_details_in_dict,
        )
        self.monkeypatch.setattr(
            ClusterSettingsTableMerger,
            "_wait_for_onboarded_filesystem_to_sync_to_config_tree",
            lambda x, y, z: None,
        )
        self.monkeypatch.setattr(
            ClusterSettingsTableMerger,
            "get_list_of_onboarded_filesystem_ids",
            lambda x, y: [],
        )
        self.monkeypatch.setattr(
            ClusterSettingsTableMerger,
            "get_list_of_accessible_filesystem_ids",
            lambda x, y: [
                DUMMY_EFS_FILESYSTEM_ID,
                DUMMY_ONTAP_FILESYSTEM_ID,
                DUMMY_LUSTRE_FILESYSTEM_ID,
            ],
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem, "onboard_efs_filesystem", lambda x: None
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem, "onboard_ontap_filesystem", lambda x: None
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem, "onboard_lustre_filesystem", lambda x: None
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "onboard_s3_bucket",
            lambda x: DUMMY_S3_BUCKET_1,
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

    def test_cluster_settings_table_merger_new_filesystem_succeed(self):
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

        merger = ClusterSettingsTableMerger()

        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 4

        merged_filesystem_names = []
        for record in record_deltas:
            assert record.action_performed == MergedRecordActionType.CREATE
            merged_filesystem_names.append(list(record.resolved_record.keys())[0])

        assert DUMMY_EFS_1 in merged_filesystem_names
        assert DUMMY_EFS_1_DEDUP not in merged_filesystem_names

        assert DUMMY_ONTAP_1 in merged_filesystem_names
        assert DUMMY_ONTAP_1_DEDUP not in merged_filesystem_names

        assert DUMMY_LUSTRE_1 in merged_filesystem_names
        assert DUMMY_LUSTRE_1_DEDUP not in merged_filesystem_names

        assert DUMMY_S3_BUCKET_1 in merged_filesystem_names
        assert DUMMY_S3_BUCKET_1_DEDUP not in merged_filesystem_names

    def test_cluster_settings_table_merger_existing_filesystem_succeed(self):
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

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 4

        merged_filesystem_names = []
        for record in record_deltas:
            assert record.action_performed == MergedRecordActionType.CREATE
            merged_filesystem_names.append(list(record.resolved_record.keys())[0])

        assert DUMMY_EFS_1 not in merged_filesystem_names
        assert DUMMY_EFS_1_DEDUP in merged_filesystem_names

        assert DUMMY_ONTAP_1 in merged_filesystem_names
        assert DUMMY_ONTAP_1_DEDUP not in merged_filesystem_names

        assert DUMMY_LUSTRE_1 in merged_filesystem_names
        assert DUMMY_LUSTRE_1_DEDUP not in merged_filesystem_names

        assert DUMMY_S3_BUCKET_1 in merged_filesystem_names
        assert DUMMY_S3_BUCKET_1_DEDUP not in merged_filesystem_names

    def test_cluster_settings_table_merger_skips_already_onboarded_filesystem(self):
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

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 3

    def test_cluster_settings_table_merger_non_project_scope_filesystem_skipped(
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
            ClusterSettingsTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_non_project_scope_filesystem_details_in_dict,
        )

        merger = ClusterSettingsTableMerger()

        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 0

    def test_cluster_settings_table_merger_adds_existing_project_to_file_system(
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
            ClusterSettingsTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_filesystem_details_in_dict,
        )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "add_filesystem_to_project",
            dummy_add_filesystem_to_project,
        )

        merger = ClusterSettingsTableMerger()
        merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert add_file_system_to_project_called

    def test_cluster_settings_table_merger_skips_adding_nonexisting_project_to_file_system(
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
            ClusterSettingsTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_filesystem_details_in_dict,
        )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "add_filesystem_to_project",
            dummy_add_filesystem_to_project,
        )

        merger = ClusterSettingsTableMerger()
        merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert not add_file_system_to_project_called

    def test_cluster_settings_table_merger_adds_dedup_project_to_filesystem_if_exists(
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
            ClusterSettingsTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: dummy_filesystem_details_in_dict,
        )

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "add_filesystem_to_project",
            dummy_add_filesystem_to_project,
        )

        merger = ClusterSettingsTableMerger()
        merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert add_file_system_to_project_called

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

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            [],
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 3

    def test_cluster_settings_table_merger_rollback_filesystem_succeed(self):
        update_filesystem_called = False
        remove_filesystem_called = False

        def dummy_update_filesystem(request: UpdateFileSystemRequest):
            nonlocal update_filesystem_called
            update_filesystem_called = True
            assert request.filesystem_name == DUMMY_EFS_1
            assert request.projects == []

        def dummy_remove_filesystem(request: RemoveFileSystemRequest):
            nonlocal remove_filesystem_called
            remove_filesystem_called = True
            assert request.filesystem_name == DUMMY_EFS_1

        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "get_filesystem",
            lambda *_: FileSystem(
                name=DUMMY_EFS_1,
                storage={
                    "title": "My EFS",
                    "provider": "efs",
                    "projects": ["dummy-project-1"],
                    "mount_dir": "/efs",
                    "efs": {},
                },
            ),
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "update_filesystem",
            lambda request: dummy_update_filesystem(request),
        )
        self.monkeypatch.setattr(
            self.context.shared_filesystem,
            "remove_filesystem",
            lambda request: dummy_remove_filesystem(request),
        )

        delta_records = [
            MergedRecordDelta(
                original_record={},
                snapshot_record={},
                resolved_record={DUMMY_EFS_1: {}},
                action_performed=MergedRecordActionType.CREATE,
            ),
        ]

        merger = ClusterSettingsTableMerger()
        merger.rollback(
            self.context,
            delta_records,
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert update_filesystem_called
        assert remove_filesystem_called


@pytest.mark.usefixtures("monkeypatch_for_class")
@pytest.mark.usefixtures("context_for_class")
class ClusterSettingsTableMergerSettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        # Disable filesystem logic for settings-only tests
        self.monkeypatch.setattr(
            ClusterSettingsTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: {},
        )
        # Mock transact_set_cluster_settings to capture writes
        self.transact_calls = {}

        def mock_transact_set(module_id, settings):
            for key, value in settings.items():
                self.transact_calls[f"{module_id}.{key}"] = value

        self.monkeypatch.setattr(
            self.context.config().db, "transact_set_cluster_settings", mock_transact_set
        )
        # Mock configure_sso to prevent actual Lambda/AD sync calls
        self.monkeypatch.setattr(
            self.context.accounts, "configure_sso", lambda request: None
        )

    def test_merge_portal_title_and_subtitle_succeed(self):
        table_data = [
            {"key": "cluster-manager.web_portal.title", "value": "My Custom Title"},
            {
                "key": "cluster-manager.web_portal.subtitle",
                "value": "My Custom Subtitle",
            },
        ]

        def mock_get_config_entry(key):
            return None

        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", mock_get_config_entry
        )

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 2
        assert (
            self.transact_calls["cluster-manager.web_portal.title"] == "My Custom Title"
        )
        assert (
            self.transact_calls["cluster-manager.web_portal.subtitle"]
            == "My Custom Subtitle"
        )

    def test_merge_allowed_instance_types_succeed(self):
        table_data = [
            {
                "key": "vdc.dcv_session.instance_types.allow",
                "value": ["t3", "m6a", "g4dn"],
            },
        ]

        def mock_get_config_entry(key):
            return {"key": key, "value": ["t3", "m5"]}

        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", mock_get_config_entry
        )

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 1
        assert record_deltas[0].action_performed == MergedRecordActionType.UPDATE
        assert record_deltas[0].original_record == {
            "key": "vdc.dcv_session.instance_types.allow",
            "value": ["t3", "m5"],
        }
        assert self.transact_calls["vdc.dcv_session.instance_types.allow"] == [
            "t3",
            "m6a",
            "g4dn",
        ]

    def test_merge_sso_settings_not_written_to_ddb_directly(self):
        table_data = [
            {"key": "identity-provider.cognito.sso_enabled", "value": True},
            {
                "key": "identity-provider.cognito.sso_idp_provider_name",
                "value": "MyOkta",
            },
            {"key": "identity-provider.cognito.sso_idp_provider_type", "value": "SAML"},
        ]

        def mock_get_config_entry(key):
            return None

        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", mock_get_config_entry
        )

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        # SSO keys should NOT be written via _merge_settings (configure_sso handles them)
        assert len(record_deltas) == 0
        assert "identity-provider.cognito.sso_enabled" not in self.transact_calls
        assert (
            "identity-provider.cognito.sso_idp_provider_name" not in self.transact_calls
        )

    def test_merge_ignores_unrelated_settings(self):
        table_data = [
            {"key": "cluster.cluster_name", "value": "my-cluster"},
            {"key": "cluster.network.vpc_id", "value": "vpc-123"},
            {"key": "cluster-manager.web_portal.title", "value": "My Title"},
        ]

        def mock_get_config_entry(key):
            return None

        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", mock_get_config_entry
        )

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(record_deltas) == 1
        assert "cluster-manager.web_portal.title" in self.transact_calls
        assert "cluster.cluster_name" not in self.transact_calls
        assert "cluster.network.vpc_id" not in self.transact_calls

    def test_merge_settings_failure_returns_false(self):
        table_data = [
            {"key": "cluster-manager.web_portal.title", "value": "My Title"},
        ]

        def mock_get_config_entry(key):
            return None

        def mock_transact_fail(module_id, settings):
            raise Exception("DDB write failed")

        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", mock_get_config_entry
        )
        self.monkeypatch.setattr(
            self.context.config().db,
            "transact_set_cluster_settings",
            mock_transact_fail,
        )

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert not success

    def test_rollback_settings_restores_original_values(self):
        transact_calls = {}

        def mock_transact_set(module_id, settings):
            for key, value in settings.items():
                transact_calls[f"{module_id}.{key}"] = value

        self.monkeypatch.setattr(
            self.context.config().db, "transact_set_cluster_settings", mock_transact_set
        )

        delta_records = [
            MergedRecordDelta(
                original_record={
                    "key": "cluster-manager.web_portal.title",
                    "value": "Old Title",
                },
                snapshot_record={
                    "key": "cluster-manager.web_portal.title",
                    "value": "New Title",
                },
                resolved_record={
                    "key": "cluster-manager.web_portal.title",
                    "value": "New Title",
                },
                action_performed=MergedRecordActionType.UPDATE,
            ),
            MergedRecordDelta(
                original_record={
                    "key": "vdc.dcv_session.instance_types.allow",
                    "value": None,
                },
                snapshot_record={
                    "key": "vdc.dcv_session.instance_types.allow",
                    "value": ["t3"],
                },
                resolved_record={
                    "key": "vdc.dcv_session.instance_types.allow",
                    "value": ["t3"],
                },
                action_performed=MergedRecordActionType.CREATE,
            ),
        ]

        merger = ClusterSettingsTableMerger()
        merger.rollback(
            self.context,
            delta_records,
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert transact_calls["cluster-manager.web_portal.title"] == "Old Title"
        assert transact_calls["vdc.dcv_session.instance_types.allow"] is None


@pytest.mark.usefixtures("monkeypatch_for_class")
@pytest.mark.usefixtures("context_for_class")
class ClusterSettingsTableMergerSSOConfigureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.monkeypatch.setattr(
            ClusterSettingsTableMerger,
            "extract_filesystem_details_to_dict",
            lambda x, y: {},
        )
        self.monkeypatch.setattr(
            self.context.config().db,
            "transact_set_cluster_settings",
            lambda module_id, settings: None,
        )
        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", lambda key: None
        )

    def test_configure_sso_called_when_sso_enabled_in_snapshot(self):
        table_data = [
            {"key": "identity-provider.cognito.sso_enabled", "value": True},
            {
                "key": "identity-provider.cognito.sso_idp_provider_name",
                "value": "MyOkta",
            },
            {"key": "identity-provider.cognito.sso_idp_provider_type", "value": "SAML"},
            {
                "key": "identity-provider.cognito.sso_idp_provider_email_attribute",
                "value": "email",
            },
            {
                "key": "identity-provider.cognito.sso_saml_metadata_url",
                "value": "https://idp.example.com/metadata",
            },
        ]

        configure_sso_calls = []

        def mock_configure_sso(request):
            configure_sso_calls.append(request)

        self.monkeypatch.setattr(
            self.context.accounts, "configure_sso", mock_configure_sso
        )

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert len(configure_sso_calls) == 1
        assert configure_sso_calls[0].provider_name == "MyOkta"
        assert configure_sso_calls[0].provider_type == "SAML"
        assert (
            configure_sso_calls[0].saml_metadata_url
            == "https://idp.example.com/metadata"
        )

    def test_configure_sso_not_called_when_sso_disabled_in_snapshot(self):
        table_data = [
            {"key": "identity-provider.cognito.sso_enabled", "value": False},
            {
                "key": "identity-provider.cognito.sso_idp_provider_name",
                "value": "MyOkta",
            },
            {"key": "identity-provider.cognito.sso_idp_provider_type", "value": "SAML"},
        ]

        configure_sso_calls = []

        def mock_configure_sso(request):
            configure_sso_calls.append(request)

        self.monkeypatch.setattr(
            self.context.accounts, "configure_sso", mock_configure_sso
        )

        merger = ClusterSettingsTableMerger()
        merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert len(configure_sso_calls) == 0

    def test_configure_sso_failure_causes_merge_failure(self):
        table_data = [
            {"key": "identity-provider.cognito.sso_enabled", "value": True},
            {
                "key": "identity-provider.cognito.sso_idp_provider_name",
                "value": "MyOkta",
            },
            {"key": "identity-provider.cognito.sso_idp_provider_type", "value": "SAML"},
            {
                "key": "identity-provider.cognito.sso_idp_provider_email_attribute",
                "value": "email",
            },
            {
                "key": "identity-provider.cognito.sso_saml_metadata_url",
                "value": "https://idp.example.com/metadata",
            },
        ]

        def mock_configure_sso(request):
            raise Exception("Cognito API failed")

        self.monkeypatch.setattr(
            self.context.accounts, "configure_sso", mock_configure_sso
        )

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        # SSO failure should cause the merge to fail and trigger rollback
        assert not success

    def test_merge_quic_setting_calls_update_quic(self):
        table_data = [
            {"key": "vdc.dcv_session.quic_support", "value": "true"},
        ]

        def mock_get_config_entry(key):
            return {"key": key, "value": "false"}

        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", mock_get_config_entry
        )

        update_quic_called_with = []

        from ideaclustermanager.app.accounts.helpers.quic_update_helper import (
            UpdateQuicResults,
        )

        def mock_update_quic(enable):
            update_quic_called_with.append(enable)
            return UpdateQuicResults.SUCCESS

        self.monkeypatch.setattr(self.context.accounts, "update_quic", mock_update_quic)

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert update_quic_called_with == [True]

    def test_merge_quic_setting_disabled_calls_update_quic_false(self):
        table_data = [
            {"key": "vdc.dcv_session.quic_support", "value": "false"},
        ]

        def mock_get_config_entry(key):
            return {"key": key, "value": "true"}

        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", mock_get_config_entry
        )

        update_quic_called_with = []

        from ideaclustermanager.app.accounts.helpers.quic_update_helper import (
            UpdateQuicResults,
        )

        def mock_update_quic(enable):
            update_quic_called_with.append(enable)
            return UpdateQuicResults.SUCCESS

        self.monkeypatch.setattr(self.context.accounts, "update_quic", mock_update_quic)

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
        assert update_quic_called_with == [False]

    def test_merge_quic_setting_succeeds_when_listener_update_raises(self):
        table_data = [
            {"key": "vdc.dcv_session.quic_support", "value": "true"},
        ]

        def mock_get_config_entry(key):
            return {"key": key, "value": "false"}

        self.monkeypatch.setattr(
            self.context.config().db, "get_config_entry", mock_get_config_entry
        )

        def mock_update_quic(enable):
            raise Exception("Network error")

        self.monkeypatch.setattr(self.context.accounts, "update_quic", mock_update_quic)

        merger = ClusterSettingsTableMerger()
        record_deltas, success = merger.merge(
            self.context,
            table_data,
            DUMMY_DEDUP_ID,
            {},
            ApplySnapshotObservabilityHelper(
                self.context.logger("cluster_settings_table_merger")
            ),
        )

        assert success
