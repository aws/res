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
from decimal import Decimal
import botocore.exceptions

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
from ideaclustermanager.app.accounts.helpers.quic_update_helper import UpdateQuicResults
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
from ideadatamodel.auth.auth_api import ConfigureSSORequest

TABLE_NAME = TableName.CLUSTER_SETTINGS_TABLE_NAME

RETRY_COUNT = 15

# Cluster settings keys to restore from snapshot (non-filesystem settings)
SETTINGS_KEYS_TO_RESTORE = [
    "cluster-manager.web_portal.title",
    "cluster-manager.web_portal.subtitle",
    "cluster-manager.web_portal.links",
    "cluster-manager.web_portal.number_of_links",
    "vdc.dcv_session.instance_types.allow",
    "vdc.dcv_session.instance_types.deny",
    "vdc.dcv_session.quic_support",
    "vdc.dcv_session.default_allowed_sessions_per_user_per_project",
    "vdc.dcv_session.default_dcv_session_type",
    "vdc.dcv_session.idle_timeout",
    "vdc.dcv_session.idle_timeout_warning",
    "vdc.dcv_session.cpu_utilization_threshold",
    "vdc.dcv_session.max_root_volume_memory",
    "vdc.dcv_session.working_hours.start_up_time",
    "vdc.dcv_session.working_hours.shut_down_time",
    "vdc.dcv_session.schedule.monday.type",
    "vdc.dcv_session.schedule.monday.start_up_time",
    "vdc.dcv_session.schedule.monday.shut_down_time",
    "vdc.dcv_session.schedule.tuesday.type",
    "vdc.dcv_session.schedule.tuesday.start_up_time",
    "vdc.dcv_session.schedule.tuesday.shut_down_time",
    "vdc.dcv_session.schedule.wednesday.type",
    "vdc.dcv_session.schedule.wednesday.start_up_time",
    "vdc.dcv_session.schedule.wednesday.shut_down_time",
    "vdc.dcv_session.schedule.thursday.type",
    "vdc.dcv_session.schedule.thursday.start_up_time",
    "vdc.dcv_session.schedule.thursday.shut_down_time",
    "vdc.dcv_session.schedule.friday.type",
    "vdc.dcv_session.schedule.friday.start_up_time",
    "vdc.dcv_session.schedule.friday.shut_down_time",
    "vdc.dcv_session.schedule.saturday.type",
    "vdc.dcv_session.schedule.saturday.start_up_time",
    "vdc.dcv_session.schedule.saturday.shut_down_time",
    "vdc.dcv_session.schedule.sunday.type",
    "vdc.dcv_session.schedule.sunday.start_up_time",
    "vdc.dcv_session.schedule.sunday.shut_down_time",
]

# SSO settings to configure (not written to DDB directly, instead handled by configure_sso())
SSO_SNAPSHOT_KEYS = [
    "identity-provider.cognito.sso_enabled",
    "identity-provider.cognito.sso_idp_provider_name",
    "identity-provider.cognito.sso_idp_provider_type",
    "identity-provider.cognito.sso_idp_provider_email_attribute",
    "identity-provider.cognito.sso_saml_metadata_url",
    "identity-provider.cognito.sso_oidc_client_id",
    "identity-provider.cognito.sso_oidc_client_secret_name",
    "identity-provider.cognito.sso_oidc_issuer",
    "identity-provider.cognito.sso_oidc_attributes_request_method",
    "identity-provider.cognito.sso_oidc_authorize_scopes",
    "identity-provider.cognito.sso_oidc_authorize_url",
    "identity-provider.cognito.sso_oidc_token_url",
    "identity-provider.cognito.sso_oidc_attributes_url",
    "identity-provider.cognito.sso_oidc_jwks_uri",
]


class ClusterSettingsTableMerger(MergeTable):
    def merge(self, context: SocaContext, table_data_to_merge: List[Dict], dedup_id: str,
              _merged_record_deltas: Dict[TableName, List[MergedRecordDelta]], logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        record_deltas: List[MergedRecordDelta] = []

        # Step 1: Merge simple key-value settings (title, instance types, etc.)
        settings_deltas, settings_success = self._merge_settings(context, table_data_to_merge, logger)
        record_deltas.extend(settings_deltas)
        if not settings_success:
            return record_deltas, False

        # Step 2: Merge filesystem settings
        filesystem_deltas, filesystem_success = self._merge_filesystems(context, table_data_to_merge, dedup_id, logger)
        record_deltas.extend(filesystem_deltas)
        if not filesystem_success:
            return record_deltas, False

        # Step 3: Auto-configure SSO if SSO params are present in snapshot
        # Runs last so that if settings or filesystems fail and trigger rollback, SSO is never attempted.
        sso_success = self._configure_sso_from_snapshot(context, table_data_to_merge, logger)
        if not sso_success:
            return record_deltas, False

        return record_deltas, True

    def _merge_settings(self, context: SocaContext, table_data_to_merge: List[Dict],
                        logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        record_deltas: List[MergedRecordDelta] = []

        # Group settings by module_id for transact_set_cluster_settings
        settings_by_module: Dict[str, Dict[str, any]] = {}
        settings_to_apply: List[Dict] = []

        for setting in table_data_to_merge:
            key = setting.get('key')
            value = setting.get('value')

            if key not in SETTINGS_KEYS_TO_RESTORE:
                continue

            # key format is "module_id.setting_path" — split on first dot
            parts = key.split('.', 1)
            if len(parts) != 2:
                continue
            module_id, setting_key = parts[0], parts[1]

            if module_id not in settings_by_module:
                settings_by_module[module_id] = {}
            settings_by_module[module_id][setting_key] = value
            settings_to_apply.append({'key': key, 'value': value, 'module_id': module_id, 'setting_key': setting_key})

        try:
            # Record original values for rollback
            for item in settings_to_apply:
                existing_entry = context.config().db.get_config_entry(item['key'])
                original_value = existing_entry.get('value') if existing_entry else None
                record_deltas.append(
                    MergedRecordDelta(
                        original_record={'key': item['key'], 'value': original_value},
                        snapshot_record={'key': item['key'], 'value': item['value']},
                        resolved_record={'key': item['key'], 'value': item['value']},
                        action_performed=MergedRecordActionType.UPDATE if original_value is not None else MergedRecordActionType.CREATE
                    )
                )

            self._apply_settings_to_cluster(context, settings_by_module)

            # If QUIC setting was applied, also update the ALB listener
            quic_setting = next((s for s in settings_to_apply if s['key'] == 'vdc.dcv_session.quic_support'), None)
            if quic_setting is not None:
                enable_quic = str(quic_setting['value']).lower() == 'true'
                try:
                    result = context.accounts.update_quic(enable_quic)
                    if result == UpdateQuicResults.SUCCESS:
                        logger.debug(TABLE_NAME, "quic_support", ApplyResourceStatus.APPLIED, "QUIC listener updated successfully")
                    else:
                        logger.warning(TABLE_NAME, "quic_support", ApplyResourceStatus.SKIPPED_SOFT_DEP,
                                       f"QUIC setting written to DDB but listener update failed: {result}")
                except Exception as quic_err:
                    logger.warning(TABLE_NAME, "quic_support", ApplyResourceStatus.SKIPPED_SOFT_DEP,
                                   f"QUIC setting written to DDB but listener update raised exception: {quic_err}")

            for item in settings_to_apply:
                logger.debug(TABLE_NAME, item['key'], ApplyResourceStatus.APPLIED, f"applied setting '{item['key']}'")

        except Exception as e:
            logger.error(TABLE_NAME, "settings", ApplyResourceStatus.FAILED_APPLY, str(e))
            return record_deltas, False

        return record_deltas, True

    @staticmethod
    def _apply_settings_to_cluster(context: SocaContext, settings_by_module: Dict[str, Dict[str, any]]) -> None:
        """Write settings to DDB and update in-memory config, grouped by module."""
        for module_id, settings in settings_by_module.items():
            # DynamoDB returns numbers as Decimal; convert for transact_set_cluster_settings
            converted = {}
            for k, v in settings.items():
                if isinstance(v, Decimal):
                    v = int(v) if v == int(v) else float(v)
                converted[k] = v
            context.config().db.transact_set_cluster_settings(module_id, converted)
            for setting_key, value in converted.items():
                context.config().put(f'{module_id}.{setting_key}', value)

    def _configure_sso_from_snapshot(self, context: SocaContext, table_data_to_merge: List[Dict],
                                     logger: ApplySnapshotObservabilityHelper) -> bool:
        """
        If SSO was enabled in the snapshot, auto-configure SSO on the new environment
        using the existing configure_sso service method.
        Returns True if SSO was not needed or succeeded, False if it failed.
        """
        snapshot_settings = {s['key']: s.get('value') for s in table_data_to_merge if s.get('key') in SSO_SNAPSHOT_KEYS}

        sso_enabled = snapshot_settings.get('identity-provider.cognito.sso_enabled')
        provider_name = snapshot_settings.get('identity-provider.cognito.sso_idp_provider_name')
        provider_type = snapshot_settings.get('identity-provider.cognito.sso_idp_provider_type')
        provider_email_attribute = snapshot_settings.get('identity-provider.cognito.sso_idp_provider_email_attribute')

        if not sso_enabled or not provider_name or not provider_type:
            if sso_enabled:
                logger.warning(TABLE_NAME, "sso_configuration", ApplyResourceStatus.SKIPPED,
                               f"SSO was enabled but missing required params: provider_name={provider_name}, provider_type={provider_type}")
            return True

        try:
            # Retrieve OIDC client secret from Secrets Manager if present
            oidc_client_secret = None
            oidc_secret_name = snapshot_settings.get('identity-provider.cognito.sso_oidc_client_secret_name')
            if oidc_secret_name:
                try:
                    secret_value = context.aws().secretsmanager().get_secret_value(SecretId=oidc_secret_name)
                    oidc_client_secret = secret_value['SecretString']
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        logger.warning(TABLE_NAME, "sso_configuration", ApplyResourceStatus.SKIPPED,
                                       f"OIDC client secret '{oidc_secret_name}' not found in this environment. "
                                       "SSO must be configured manually with the OIDC client secret.")
                        return True
                    raise

            request = ConfigureSSORequest(
                provider_name=provider_name,
                provider_type=provider_type,
                provider_email_attribute=provider_email_attribute or 'email',
                saml_metadata_url=snapshot_settings.get('identity-provider.cognito.sso_saml_metadata_url'),
                oidc_client_id=snapshot_settings.get('identity-provider.cognito.sso_oidc_client_id'),
                oidc_client_secret=oidc_client_secret,
                oidc_issuer=snapshot_settings.get('identity-provider.cognito.sso_oidc_issuer'),
                oidc_attributes_request_method=snapshot_settings.get('identity-provider.cognito.sso_oidc_attributes_request_method'),
                oidc_authorize_scopes=snapshot_settings.get('identity-provider.cognito.sso_oidc_authorize_scopes'),
                oidc_authorize_url=snapshot_settings.get('identity-provider.cognito.sso_oidc_authorize_url'),
                oidc_token_url=snapshot_settings.get('identity-provider.cognito.sso_oidc_token_url'),
                oidc_attributes_url=snapshot_settings.get('identity-provider.cognito.sso_oidc_attributes_url'),
                oidc_jwks_uri=snapshot_settings.get('identity-provider.cognito.sso_oidc_jwks_uri'),
            )

            context.accounts.configure_sso(request)
            logger.debug(TABLE_NAME, "sso_configuration", ApplyResourceStatus.APPLIED, "SSO auto-configured from snapshot")
            return True

        except Exception as e:
            logger.error(TABLE_NAME, "sso_configuration", ApplyResourceStatus.FAILED_APPLY, f"SSO auto-configuration failed: {e}")
            return False

    def _merge_filesystems(self, context: SocaContext, table_data_to_merge: List[Dict], dedup_id: str,
                           logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
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
                        message=f"{filesystem_id} is not part of the env's VPC thus not accessible"
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
                    TABLE_NAME, filesystem_name, ApplyResourceStatus.FAILED_APPLY, str(e)
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
                self._wait_for_onboarded_filesystem_to_sync_to_config_tree(filesystem_name_to_use, context)

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
        """Wait for the filesystem changes to be picked up by the config listener and added to the local config tree."""
        retry_count = RETRY_COUNT
        while retry_count:
            retry_count -= 1
            time.sleep(5)

            try:
                context.shared_filesystem.get_filesystem(filesystem_name)
                return
            except exceptions.SocaException:
                pass

        raise exceptions.soca_exception(
            error_code=errorcodes.GENERAL_ERROR,
            message=f"Timed out waiting for filesystem '{filesystem_name}' to sync to config tree after {RETRY_COUNT * 5}s"
        )

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
        # Collect settings to rollback and group by module
        settings_by_module: Dict[str, Dict[str, any]] = {}
        filesystem_deltas = []

        for record_delta in record_deltas:
            if 'key' in record_delta.original_record:
                key = record_delta.original_record['key']
                original_value = record_delta.original_record['value']
                parts = key.split('.', 1)
                if len(parts) == 2:
                    module_id, setting_key = parts[0], parts[1]
                    if module_id not in settings_by_module:
                        settings_by_module[module_id] = {}
                    settings_by_module[module_id][setting_key] = original_value
            elif record_delta.action_performed == MergedRecordActionType.CREATE:
                filesystem_deltas.append(record_delta)

        # Rollback settings using transact_set_cluster_settings
        try:
            self._apply_settings_to_cluster(context, settings_by_module)
            for module_id, settings in settings_by_module.items():
                for setting_key in settings:
                    logger.debug(TABLE_NAME, f'{module_id}.{setting_key}', ApplyResourceStatus.ROLLBACKED, "rolled back setting")
        except Exception as e:
            logger.error(TABLE_NAME, "settings", ApplyResourceStatus.FAILED_ROLLBACK, str(e))
            raise e

        # Rollback filesystem onboarding
        for record_delta in filesystem_deltas:
            filesystem_name = list(record_delta.resolved_record.keys())[0]

            try:
                context.shared_filesystem.update_filesystem(UpdateFileSystemRequest(filesystem_name=filesystem_name, projects=[]))
                context.shared_filesystem.remove_filesystem(RemoveFileSystemRequest(filesystem_name=filesystem_name))
            except Exception as e:
                logger.error(TABLE_NAME, filesystem_name, ApplyResourceStatus.FAILED_ROLLBACK, str(e))
                raise e

            logger.debug(TABLE_NAME, filesystem_name, ApplyResourceStatus.ROLLBACKED, "offboarded filesystem succeeded")
