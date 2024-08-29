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

from typing import Dict, List, Tuple
import time

from ideaclustermanager.app.snapshots.apply_snapshot_merge_table.merge_table import (
    MergeTable,

)
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import (
    ApplyResourceStatus,
    ApplySnapshotObservabilityHelper,
)
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import (
    MergedRecordActionType,
    MergedRecordDelta,
)
from ideasdk.context import SocaContext
from pyhocon import ConfigFactory

from ideadatamodel import errorcodes, exceptions, OnboardS3BucketRequest
from ideadatamodel.constants import (
    MODULE_SHARED_STORAGE,
    STORAGE_PROVIDER_EFS,
    STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
    STORAGE_PROVIDER_FSX_LUSTRE,
    STORAGE_PROVIDER_S3_BUCKET
)
from ideadatamodel import (
    OnboardEFSFileSystemRequest,
    AddFileSystemToProjectRequest,
    OnboardONTAPFileSystemRequest,
    OnboardLUSTREFileSystemRequest,
    UpdateFileSystemRequest,
    RemoveFileSystemRequest,
    ListProjectsRequest,
    ListOnboardedFileSystemsRequest

)
from ideadatamodel.snapshots.snapshot_model import TableName

TABLE_NAME = TableName.CLUSTER_SETTINGS_TABLE_NAME

RETRY_COUNT = 15


class FileSystemsClusterSettingTableMerger(MergeTable):
    def merge(self, context: SocaContext, table_data_to_merge: List[Dict], dedup_id: str,
              _merged_record_deltas: Dict[TableName, List[MergedRecordDelta]], logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        record_deltas: List[MergedRecordDelta] = []

        onboarded_filesystem_ids = self.get_list_of_onboarded_filesystem_ids(context)
        accessible_filesystem_ids = self.get_list_of_accessible_filesystem_ids(context)

        env_project_names = set(self.get_names_of_projects_in_env(context))

        details = self.extract_filesystem_details_to_dict(table_data_to_merge)

        for filesystem_name in details:

            if not isinstance(details[filesystem_name], dict):
                continue

            # If 'provider' empty, skip applying filesystem
            provider = details[filesystem_name].get("provider")
            if not provider:
                logger.warning(TABLE_NAME, filesystem_name, ApplyResourceStatus.SKIPPED, f"filesystem provider not mentioned for filesystem {filesystem_name}")
                continue

            # If filesystem of a scope other than 'project' skip applying filesystem
            scope = details[filesystem_name].get('scope')
            if not scope or 'project' not in scope:
                logger.warning(TABLE_NAME, filesystem_name, ApplyResourceStatus.SKIPPED, f"filesystem '{filesystem_name}' not of 'project' scope")
                continue

            # If filesystem does not belong to the same VPC or is already onboarded, skip applying filesystem
            try:
                if provider == STORAGE_PROVIDER_S3_BUCKET:
                    filesystem_id = details[filesystem_name][provider]["bucket_arn"]
                else:
                    filesystem_id = details[filesystem_name][provider]["file_system_id"]
                if filesystem_id in onboarded_filesystem_ids:
                    raise exceptions.soca_exception(
                        error_code=errorcodes.FILESYSTEM_ALREADY_ONBOARDED,
                        message=f"{filesystem_id} has already been onboarded"
                    )
                # Does not apply to S3 buckets
                if filesystem_id not in accessible_filesystem_ids and provider != STORAGE_PROVIDER_S3_BUCKET:
                    raise exceptions.soca_exception(
                        error_code=errorcodes.FILESYSTEM_NOT_IN_VPC,
                        message=f"{filesystem_id} not part of the env's VPC thus not accessible"
                    )
            except exceptions.SocaException as e:
                # Gracefully handling cases when filesystem is already onboarded or not accessible
                if e.error_code == errorcodes.FILESYSTEM_ALREADY_ONBOARDED or e.error_code == errorcodes.FILESYSTEM_NOT_IN_VPC:
                    logger.debug(TABLE_NAME, filesystem_name, ApplyResourceStatus.SKIPPED, f"{e.message}")
                    continue
                else:
                    raise e
            except Exception as e:
                logger.error(TABLE_NAME, filesystem_name, ApplyResourceStatus.FAILED_APPLY, str(e))
                return record_deltas, False

            # Check to see if the env already has a filesystem with the same name. If so apply the filesystem with the dedup_id attached.
            filesystem_with_name_already_present = False
            try:
                context.shared_filesystem.get_filesystem(filesystem_name)

                filesystem_with_name_already_present = True
            except exceptions.SocaException as e:
                if e.error_code != errorcodes.NO_SHARED_FILESYSTEM_FOUND and e.error_code != errorcodes.FILESYSTEM_NOT_FOUND:
                    raise e
            except Exception as e:
                logger.error(
                    TABLE_NAME, filesystem_name, ApplyResourceStatus.FAILED_APPLY, {e}
                )
                return record_deltas, False

            # FileSystem with same name exists.
            # This merge will add a new filesystem by appending the RES version and dedup ID to its name instead of overriding the existing ones,
            filesystem_name_to_use = (
                MergeTable.unique_resource_id_generator(filesystem_name, dedup_id)
                if filesystem_with_name_already_present
                else filesystem_name
            )

            try:
                if provider == STORAGE_PROVIDER_EFS:
                    self._onboard_efs(filesystem_name_to_use, details[filesystem_name], context)
                elif provider == STORAGE_PROVIDER_FSX_NETAPP_ONTAP:
                    self._onboard_ontap(filesystem_name_to_use, details[filesystem_name], context)
                elif provider == STORAGE_PROVIDER_FSX_LUSTRE:
                    self._onboard_lustre(filesystem_name_to_use, details[filesystem_name], context)
                elif provider == STORAGE_PROVIDER_S3_BUCKET:
                    # Onboard s3 bucket generates the filesystem name
                    filesystem_name_to_use = self._onboard_s3_bucket(details[filesystem_name], context)
                # Wait for some time for the filesystem changes to be picked up by the config listener and added to the local config tree
                self._wait_for_onboarded_filesystem_to_sync_to_config_tree(filesystem_name, context)

                # Does not apply to s3 bucket
                if provider != STORAGE_PROVIDER_S3_BUCKET:
                    accessible_filesystem_ids.remove(filesystem_id)

                # All the onboarded filesystem to corresponding projects. This is a soft dependency. If a project does not exist, it will be ignored. A rollback will not be triggered in this case.
                self._add_filesystem_to_projects(filesystem_name_to_use, details[filesystem_name], env_project_names, context, dedup_id, logger)
            except exceptions.SocaException as e:
                # Gracefully handling cases when filesystem is already onboarded or not accessible
                if e.error_code == errorcodes.FILESYSTEM_ALREADY_ONBOARDED or e.error_code == errorcodes.FILESYSTEM_NOT_IN_VPC:
                    logger.debug(TABLE_NAME, filesystem_name, ApplyResourceStatus.SKIPPED, f"{e.message}")
                    continue
                else:
                    raise e
            except Exception as e:
                logger.error(TABLE_NAME, filesystem_name_to_use, ApplyResourceStatus.FAILED_APPLY, str(e))
                return record_deltas, False

            if filesystem_with_name_already_present:
                logger.debug(TABLE_NAME, filesystem_name_to_use, ApplyResourceStatus.APPLIED, f"fileSystem with same name already exists. Onboarded the filesystem successfully with name {filesystem_name_to_use}")
            else:
                logger.debug(TABLE_NAME, filesystem_name_to_use, ApplyResourceStatus.APPLIED, f"onboarded the filesystem successfully")

            record_deltas.append(
                MergedRecordDelta(
                    original_record={},
                    snapshot_record={filesystem_name: details[filesystem_name]},
                    resolved_record={filesystem_name_to_use: details[filesystem_name]},
                    action_performed=MergedRecordActionType.CREATE
                )
            )

        return record_deltas, True

    @staticmethod
    def get_list_of_onboarded_filesystem_ids(context):
        onboarded_filesystems = context.shared_filesystem.list_onboarded_file_systems(ListOnboardedFileSystemsRequest()).listing
        return set([fs.get_filesystem_id() for fs in onboarded_filesystems])

    @staticmethod
    def get_list_of_accessible_filesystem_ids(context):
        efs_filesystems = context.shared_filesystem._list_unonboarded_efs_file_systems([])
        fsx_ontap_filesystems = context.shared_filesystem._list_unonboarded_ontap_file_systems([])
        fsx_lustre_filesystems = context.shared_filesystem._list_unonboarded_lustre_file_systems([])

        filesystems_in_vpc = [*efs_filesystems, *fsx_ontap_filesystems, *fsx_lustre_filesystems]

        return set([fs.get_filesystem_id() for fs in filesystems_in_vpc])

    @staticmethod
    def get_names_of_projects_in_env(context):
        env_projects = context.projects.list_projects(ListProjectsRequest()).listing
        return [project.name for project in env_projects]

    @staticmethod
    def extract_filesystem_details_to_dict(table_data_to_merge: List[Dict]
    ) -> Dict:
        filesystem_details = {}
        for setting in table_data_to_merge:
            key = setting['key']
            value = setting['value']

            if str(key).startswith(MODULE_SHARED_STORAGE):
                filesystem_details[key] = value

        config = ConfigFactory.from_dict(filesystem_details)

        return config.get(MODULE_SHARED_STORAGE, {}).as_plain_ordered_dict()

    @staticmethod
    def _onboard_efs(filesystem_name: str, details: Dict, context: SocaContext):
        onboard_efs_request = OnboardEFSFileSystemRequest(
                filesystem_name=filesystem_name,
                filesystem_title=details["title"],
                filesystem_id=details[STORAGE_PROVIDER_EFS]["file_system_id"],
                mount_directory=details["mount_dir"],
            )
        context.shared_filesystem.onboard_efs_filesystem(
            onboard_efs_request
        )

    @staticmethod
    def _onboard_ontap(filesystem_name: str, details: Dict, context: SocaContext):
        onboard_ontap_request = OnboardONTAPFileSystemRequest(
                filesystem_name=filesystem_name,
                filesystem_title=details["title"],
                filesystem_id=details[STORAGE_PROVIDER_FSX_NETAPP_ONTAP]["file_system_id"],
                mount_directory=details["mount_dir"],
                mount_drive=details["mount_drive"],
                svm_id=details[STORAGE_PROVIDER_FSX_NETAPP_ONTAP]["svm"]["svm_id"],
                volume_id=details[STORAGE_PROVIDER_FSX_NETAPP_ONTAP]["volume"]["volume_id"],
                file_share_name=details[STORAGE_PROVIDER_FSX_NETAPP_ONTAP]["volume"]["cifs_share_name"]
            )
        context.shared_filesystem.onboard_ontap_filesystem(onboard_ontap_request)

    @staticmethod
    def _onboard_lustre(filesystem_name: str, details: Dict, context: SocaContext):
        onboard_lustre_request = OnboardLUSTREFileSystemRequest(
                filesystem_name=filesystem_name,
                filesystem_title=details["title"],
                filesystem_id=details[STORAGE_PROVIDER_FSX_LUSTRE]["file_system_id"],
                mount_directory=details["mount_dir"]
            )
        context.shared_filesystem.onboard_lustre_filesystem(onboard_lustre_request)

    @staticmethod
    def _onboard_s3_bucket(details: Dict, context: SocaContext) -> str:

        onboard_s3_bucket_request = OnboardS3BucketRequest(
            object_storage_title=details["title"],
            mount_directory=details["mount_dir"],
            read_only=details[STORAGE_PROVIDER_S3_BUCKET]["read_only"],
            custom_bucket_prefix=details[STORAGE_PROVIDER_S3_BUCKET].get("custom_bucket_prefix"),
            bucket_arn=details[STORAGE_PROVIDER_S3_BUCKET]["bucket_arn"],
            iam_role_arn=details[STORAGE_PROVIDER_S3_BUCKET].get("iam_role_arn")
        )
        return context.shared_filesystem.onboard_s3_bucket(onboard_s3_bucket_request)

    @staticmethod
    def _wait_for_onboarded_filesystem_to_sync_to_config_tree(filesystem_name, context):
        """Wait for some time for the filesystem changes to be picked up by the config listner and added to the local config tree

        Args:
            filesystem_name (str):
            context (SocaContext):
        """
        retry_count = RETRY_COUNT
        while retry_count:
            retry_count -= 1
            time.sleep(5)

            try:
                context.shared_filesystem.get_filesystem(filesystem_name)
                return
            except exceptions.SocaException as e:
                pass

    @staticmethod
    def _add_filesystem_to_projects(filesystem_name: str, details: Dict, env_project_names: set[str], context: SocaContext, dedup_id: str, logger: ApplySnapshotObservabilityHelper):
        fs_projects = details.get("projects")
        if not fs_projects:
            return

        for project_name in fs_projects:
            # If project not present in env, skip attaching filesystem to project
            if project_name not in env_project_names:
                logger.debug(TABLE_NAME, filesystem_name, ApplyResourceStatus.SKIPPED_SOFT_DEP ,f"project '{project_name}' not present in env.")
                continue

            # If a new project with dedup_id was created while applying the projects table due to name conflict, the filesystem must be attached to the project with dedup_id
            deduped_project_name = MergeTable.unique_resource_id_generator(project_name, dedup_id)
            project_name_to_use = deduped_project_name if deduped_project_name in env_project_names else project_name

            try:
                context.shared_filesystem.add_filesystem_to_project(
                    AddFileSystemToProjectRequest(
                        filesystem_name=filesystem_name, project_name=project_name_to_use
                    )
                )
                logger.debug(TABLE_NAME, filesystem_name, ApplyResourceStatus.APPLIED_SOFT_DEP ,f"added {project_name_to_use} to filesystem successfully")
            except Exception as e:
                logger.debug(TABLE_NAME, filesystem_name, ApplyResourceStatus.SKIPPED_SOFT_DEP ,f"adding project '{project_name_to_use}' to filesystem failed with error {e}")

    def rollback(self, context: SocaContext, record_deltas: List[MergedRecordDelta], logger: ApplySnapshotObservabilityHelper) -> None:
        while record_deltas:
            record_delta = record_deltas[0]
            filesystem_name = list(record_delta.resolved_record.keys())[0]

            if record_delta.action_performed == MergedRecordActionType.CREATE:
                try:
                    context.shared_filesystem.update_filesystem(UpdateFileSystemRequest(filesystem_name=filesystem_name, projects=[]))
                    context.shared_filesystem.remove_filesystem(RemoveFileSystemRequest(filesystem_name=filesystem_name))
                except Exception as e:
                    logger.error(TABLE_NAME, filesystem_name, ApplyResourceStatus.FAILED_ROLLBACK, str(e))
                    raise e

                logger.debug(TABLE_NAME, filesystem_name, ApplyResourceStatus.ROLLBACKED, "offboarded filesystem succeeded")

            record_deltas.pop(0)
