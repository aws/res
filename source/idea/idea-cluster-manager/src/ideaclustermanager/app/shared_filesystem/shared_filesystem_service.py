import time
from typing import List, Dict

import ideaclustermanager
from ideadatamodel import (
    constants,
    CommonCreateFileSystemRequest,
    CreateEFSFileSystemRequest,
    EFSFileSystem,
    FSxONTAPSVM,
    FSxONTAPVolume,
    CreateONTAPFileSystemRequest,
    exceptions,
)
from ideadatamodel.shared_filesystem import (
    OnboardEFSFileSystemRequest,
    OnboardONTAPFileSystemRequest,
)
from ideasdk.utils import Utils
import botocore.exceptions


class SharedFilesystemService:
    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.config = self.context.config()

    def create_tags(self, filesystem_name: str):
        backup_plan_tags = self.config.get_list(
            f"{constants.MODULE_CLUSTER}.backups.backup_plan.selection.tags"
        )
        _backup_tags = Utils.convert_custom_tags_to_key_value_pairs(backup_plan_tags)
        _backup_aws_tags = Utils.convert_tags_dict_to_aws_tags(_backup_tags)
        tags_for_fs = [
            {"Key": "Name", "Value": filesystem_name},
            {
                "Key": "res:EnvironmentName",
                "Value": self.config.get_string(
                    f"{constants.MODULE_CLUSTER}.cluster_name"
                ),
            },
            {
                "Key": "res:ModuleId",
                "Value": self.config.get_module_id(constants.MODULE_SHARED_STORAGE),
            },
            {"Key": "res:ModuleName", "Value": constants.MODULE_SHARED_STORAGE},
            {"Key": "res:ModuleVersion", "Value": self.context.module_version()},
        ]
        tags_for_fs.extend(_backup_aws_tags)
        return tags_for_fs

    @staticmethod
    def common_filesystem_config(request: CommonCreateFileSystemRequest):
        return {
            "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
            "projects": request.projects,
            "scope": ["project"],
            "title": request.filesystem_title,
        }

    def build_config_for_vpc_efs(
        self, request: OnboardEFSFileSystemRequest
    ):
        efs_client = self.context.aws().efs()
        filesystem_id = request.filesystem_id
        describe_fs_result = efs_client.describe_file_systems(FileSystemId=filesystem_id)
        file_system = describe_fs_result['FileSystems'][0]
        config = {
            request.filesystem_name: {
                "title": request.filesystem_title,
                "provider": constants.STORAGE_PROVIDER_EFS,
                "scope": ["project"],
                "projects": [],
                "mount_dir": request.mount_directory,
                "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
                constants.STORAGE_PROVIDER_EFS: {
                    "removal_policy": "RETAIN",
                    "use_existing_fs": True,
                    "file_system_id": filesystem_id,
                    "dns": f"{filesystem_id}.efs.{self.context.aws().aws_region()}.amazonaws.com",
                    "encrypted": Utils.get_value_as_string('Encrypted', file_system)
                }
            }
        }
        config_entries = []
        self.traverse_config(
            config_entries=config_entries,
            prefix=constants.MODULE_SHARED_STORAGE,
            config=config,
        )
        return config_entries

    def build_config_for_new_efs(
        self, efs: EFSFileSystem, request: CreateEFSFileSystemRequest
    ):
        config = {
            request.filesystem_name: {
                constants.STORAGE_PROVIDER_EFS: {
                    "cloudwatch_monitoring": False,
                    "dns": f"{efs.get_filesystem_id()}.efs.{self.context.aws().aws_region()}.amazonaws.com",
                    "encrypted": efs.get_encrypted(),
                    "file_system_id": efs.get_filesystem_id(),
                    "kms_key_id": Utils.get_as_string(efs.get_kms_key_id()),
                    "performance_mode": efs.get_performance_mode(),
                    "removal_policy": "RETAIN",
                    "throughput_mode": efs.get_throughput_mode(),
                    "transition_to_ia": "AFTER_30_DAYS",
                },
                "provider": constants.STORAGE_PROVIDER_EFS,
                "mount_dir": request.mount_directory,
                **self.common_filesystem_config(request),
            }
        }
        config_entries = []
        self.traverse_config(
            config_entries=config_entries,
            prefix=constants.MODULE_SHARED_STORAGE,
            config=config,
        )
        return config_entries

    def build_config_for_vpc_ontap(
        self, request: OnboardONTAPFileSystemRequest,
    ):
        fsx_client = self.context.aws().fsx()

        describe_svm_response = fsx_client.describe_storage_virtual_machines(StorageVirtualMachineIds=[request.svm_id])
        describe_volumes_response = fsx_client.describe_volumes(VolumeIds=[request.volume_id])

        svm = FSxONTAPSVM(storage_virtual_machine=describe_svm_response['StorageVirtualMachines'][0])
        volume = FSxONTAPVolume(volume=describe_volumes_response['Volumes'][0])

        config = {
            request.filesystem_name: {
                "title": request.filesystem_title,
                "provider":  constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
                "scope": ["project"],
                "projects": [],
                "mount_dir": request.mount_directory,
                "mount_drive": request.mount_drive,
                "mount_options": "nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0",
                constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP: {
                    "removal_policy": "RETAIN",
                    "use_existing_fs": True,
                    "file_system_id": request.filesystem_id,
                    "svm": {
                        "svm_id": svm.get_svm_id(),
                        "smb_dns": svm.get_svm_smb_dns(),
                        "nfs_dns": svm.get_svm_nfs_dns(),
                        "management_dns": svm.get_svm_mgmt_dns(),
                        "iscsi_dns": svm.get_svm_iscsi_dns(),
                    },
                    "volume": {
                        "volume_id": volume.get_volume_id(),
                        "volume_path": volume.get_volume_path(),
                        "security_style": volume.get_security_style(),
                        "cifs_share_name": request.file_share_name,
                    },
                },
            }
        }

        config_entries = []
        self.traverse_config(
            config_entries=config_entries,
            prefix=constants.MODULE_SHARED_STORAGE,
            config=config,
        )
        return config_entries

    def build_config_for_new_ontap(
        self,
        svm: FSxONTAPSVM,
        volume: FSxONTAPVolume,
        request: CreateONTAPFileSystemRequest,
    ):
        config = {
            request.filesystem_name: {
                constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP: {
                    "removal_policy": "RETAIN",
                    "file_system_id": svm.get_filesystem_id(),
                    "svm": {
                        "svm_id": svm.get_svm_id(),
                        "smb_dns": None,
                        "nfs_dns": svm.get_svm_nfs_dns(),
                        "management_dns": svm.get_svm_mgmt_dns(),
                        "iscsi_dns": svm.get_svm_iscsi_dns(),
                    },
                    "volume": {
                        "volume_id": volume.get_volume_id(),
                        "volume_path": volume.get_volume_path(),
                        "security_style": volume.get_security_style(),
                        "cifs_share_name": request.file_share_name,
                    },
                },
                "provider": constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
                "mount_dir": request.mount_directory,
                "mount_drive": request.mount_drive,
                **self.common_filesystem_config(request),
            }
        }

        config_entries = []
        self.traverse_config(
            config_entries=config_entries,
            prefix=constants.MODULE_SHARED_STORAGE,
            config=config,
        )
        return config_entries

    def traverse_config(self, config_entries: List[Dict], prefix: str, config: Dict):
        for key in config:
            if "." in key or ":" in key:
                raise exceptions.general_exception(
                    f"Config key name: {key} under: {prefix} cannot contain a dot(.), colon(:) or comma(,)"
                )

            value = Utils.get_any_value(key, config)

            if Utils.is_not_empty(prefix):
                path_prefix = f"{prefix}.{key}"
            else:
                path_prefix = key

            if isinstance(value, dict):
                self.traverse_config(config_entries, path_prefix, value)

            else:
                config_entries.append({"key": path_prefix, "value": value})

    def efs_check_filesystem_exists(
        self, filesystem_id: str, wait: bool = False
    ) -> bool:
        try:
            while True:
                describe_efs_result = (
                    self.context.aws()
                    .efs()
                    .describe_file_systems(FileSystemId=filesystem_id)
                )

                if not wait:
                    return True

                filesystem = describe_efs_result["FileSystems"][0]
                available = filesystem["LifeCycleState"] == "available"

                if available:
                    return True

                time.sleep(2)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            else:
                raise e
