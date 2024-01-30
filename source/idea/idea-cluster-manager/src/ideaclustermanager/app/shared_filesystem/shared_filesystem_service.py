import time
from typing import List, Dict, Set, Union

import ideaclustermanager
from ideasdk.context import SocaContext
from ideadatamodel import (
    constants,
    CommonCreateFileSystemRequest,
    CreateEFSFileSystemRequest,
    EFSFileSystem,
    FSxONTAPSVM,
    FSxONTAPVolume,
    CreateONTAPFileSystemRequest,
    exceptions,
    errorcodes
)
from ideadatamodel.shared_filesystem import (
    AddFileSystemToProjectRequest,
    OnboardEFSFileSystemRequest,
    OnboardONTAPFileSystemRequest,
    RemoveFileSystemFromProjectRequest,
    CommonOnboardFileSystemRequest,
    OffboardFileSystemRequest,
    FileSystem,
    FSxONTAPFileSystem,
    ListFileSystemInVPCResult
)
from ideadatamodel.shared_filesystem.shared_filesystem_api import FSxONTAPDeploymentType
from ideasdk.utils import Utils, ApiUtils
import botocore.exceptions


class SharedFilesystemService:
    def __init__(self, context: SocaContext):
        self.context = context
        self.config = self.context.config()
        self.logger = self.context.logger("shared-filesystem")

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

    def onboard_efs_filesystem(self, request: OnboardEFSFileSystemRequest):
        self._validate_onboard_filesystem_request(request)
        self._validate_filesystem_does_not_exist(request.filesystem_name)
        self._validate_filesystem_present_in_vpc_and_not_onboarded(request.filesystem_id)

        config_entries = self.build_config_for_vpc_efs(request)

        self.context.config().db.sync_cluster_settings_in_db(
            config_entries=config_entries,
            overwrite=True
        )

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

    def create_efs(self, request: CreateEFSFileSystemRequest):
        self._validate_create_filesystem_request(request)
        self._validate_correct_subnet_selection({request.subnet_id_1, request.subnet_id_2})
        self._validate_filesystem_does_not_exist(request.filesystem_name)
        ApiUtils.validate_input(request.mount_directory,
                                constants.MOUNT_DIRECTORY_REGEX,
                                constants.MOUNT_DIRECTORY_ERROR_MESSAGE)
        try:
            efs_client = self.context.aws().efs()
            security_group_id = self.config.get_string(
                f"{constants.MODULE_SHARED_STORAGE}.security_group_id"
            )

            tags_for_fs = self.create_tags(
                request.filesystem_name
            )

            efs_create_response = efs_client.create_file_system(
                ThroughputMode="elastic", Encrypted=True, Tags=tags_for_fs
            )
            efs_filesystem = EFSFileSystem(efs=efs_create_response)
            efs_filesystem_id = efs_filesystem.get_filesystem_id()

            self.efs_check_filesystem_exists(
                filesystem_id=efs_filesystem_id, wait=True
            )
            filesystem_policy = {
                "Version": "2012-10-17",
                "Id": "efs-prevent-anonymous-access-policy",
                "Statement": [
                    {
                        "Sid": "efs-statement",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": [
                            "elasticfilesystem:ClientRootAccess",
                            "elasticfilesystem:ClientWrite",
                            "elasticfilesystem:ClientMount",
                        ],
                        "Resource": f"arn:{self.context.aws().aws_partition()}:elasticfilesystem:{self.context.aws().aws_region()}:{self.context.aws().aws_account_id()}:file-system/{efs_filesystem_id}",
                        "Condition": {
                            "Bool": {"elasticfilesystem:AccessedViaMountTarget": "true"}
                        },
                    }
                ],
            }
            efs_client.put_file_system_policy(
                FileSystemId=efs_filesystem_id, Policy=Utils.to_json(filesystem_policy)
            )

            # Create mount targets
            efs_client.create_mount_target(
                FileSystemId=efs_filesystem_id,
                SubnetId=request.subnet_id_1,
                SecurityGroups=[security_group_id],
            )
            efs_client.create_mount_target(
                FileSystemId=efs_filesystem_id,
                SubnetId=request.subnet_id_2,
                SecurityGroups=[security_group_id],
            )

            # Sync cluster-settings ddb
            config_entries = self.build_config_for_new_efs(
                efs=efs_filesystem, request=request
            )
            self.config.db.sync_cluster_settings_in_db(
                config_entries=config_entries, overwrite=True
            )
        except botocore.exceptions.ClientError as e:
            error_message = e.response["Error"]["Message"]
            raise exceptions.general_exception(error_message)

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

    def onboard_ontap_filesystem(self, request: OnboardONTAPFileSystemRequest):
        self._validate_onboard_filesystem_request(request)
        self._validate_filesystem_does_not_exist(request.filesystem_name)
        self._validate_filesystem_present_in_vpc_and_not_onboarded(request.filesystem_id)

        config_entries = self.build_config_for_vpc_ontap(request)

        self.context.config().db.sync_cluster_settings_in_db(
            config_entries=config_entries,
            overwrite=True
        )

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

    def create_fsx_ontap(self, request: CreateONTAPFileSystemRequest):
        self._validate_create_filesystem_request(request)
        self._validate_correct_subnet_selection({request.primary_subnet, request.standby_subnet})
        self._validate_filesystem_does_not_exist(request.filesystem_name)
        if not request.mount_directory and not request.mount_drive:
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_PARAMS,
                message="One of mount drive or mount directory is required",
            )

        if request.mount_directory:
            ApiUtils.validate_input(request.mount_directory,
                                    constants.MOUNT_DIRECTORY_REGEX,
                                    constants.MOUNT_DIRECTORY_ERROR_MESSAGE)

        if request.mount_drive:
            ApiUtils.validate_input(request.mount_drive,
                                    constants.MOUNT_DRIVE_REGEX,
                                    constants.MOUNT_DRIVE_ERROR_MESSAGE)

            ApiUtils.validate_input(request.file_share_name,
                                    constants.FILE_SYSTEM_NAME_REGEX,
                                    constants.FILE_SYSTEM_NAME_ERROR_MESSAGE)
        ApiUtils.validate_input_range(request.storage_capacity, constants.ONTAP_STORAGE_CAPACITY_RANGE)
        try:
            fsx_client = self.context.aws().fsx()
            security_group_id = self.config.get_string(
                f"{constants.MODULE_SHARED_STORAGE}.security_group_id"
            )

            tags_for_fs = self.create_tags(
                request.filesystem_name
            )

            _subnet_ids = []
            if request.deployment_type == FSxONTAPDeploymentType.SINGLE_AZ:
                _subnet_ids = [request.primary_subnet]
            else:
                _subnet_ids = [request.primary_subnet, request.standby_subnet]
            fs_create_response = fsx_client.create_file_system(
                FileSystemType="ONTAP",
                SecurityGroupIds=[
                    security_group_id,
                ],
                Tags=tags_for_fs,
                StorageCapacity=request.storage_capacity,
                SubnetIds=_subnet_ids,
                OntapConfiguration={
                    "PreferredSubnetId": request.primary_subnet,
                    "DeploymentType": request.deployment_type,
                    "ThroughputCapacity": 128,  # parameter required
                },
            )

            fsx_ontap_filesystem = FSxONTAPFileSystem(
                filesystem=fs_create_response["FileSystem"]
            )
            fs_id = fsx_ontap_filesystem.get_filesystem_id()

            svm = fsx_client.create_storage_virtual_machine(
                FileSystemId=fs_id,
                Name="fsx",
            )

            svm_volume = fsx_client.create_volume(
                VolumeType="ONTAP",
                Name="vol1",
                OntapConfiguration={
                    "JunctionPath": "/vol1",
                    "SecurityStyle": request.volume_security_style,
                    "SizeInMegabytes": 1024,
                    "StorageVirtualMachineId": svm["StorageVirtualMachine"][
                        "StorageVirtualMachineId"
                    ],
                    "StorageEfficiencyEnabled": True,
                },
            )

            fsx_ontap_svm = FSxONTAPSVM(
                storage_virtual_machine=svm["StorageVirtualMachine"]
            )
            fsx_ontap_volume = FSxONTAPVolume(volume=svm_volume["Volume"])

            # Update cluster-settings dynamodb
            config_entries = self.build_config_for_new_ontap(
                svm=fsx_ontap_svm, volume=fsx_ontap_volume, request=request
            )
            self.config.db.sync_cluster_settings_in_db(
                config_entries=config_entries, overwrite=True
            )
        except botocore.exceptions.ClientError as e:
            error_message = e.response["Error"]["Message"]
            self.logger.error(error_message)
            raise exceptions.general_exception(error_message)

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

    def offboard_filesystem(self, request: OffboardFileSystemRequest):
        filesystem_name = request.filesystem_name
        self.config.db.delete_config_entries(f'{constants.MODULE_SHARED_STORAGE}.{filesystem_name}')

    def add_filesystem_to_project(self, request: AddFileSystemToProjectRequest):
        filesystem_name = request.filesystem_name
        project_name = request.project_name
        self._check_required_parameters(request=request)
        self.update_filesystem_to_project_mapping(filesystem_name, project_name)

    def remove_filesystem_from_project(self, request: RemoveFileSystemFromProjectRequest):
        filesystem_name = request.filesystem_name
        project_name = request.project_name
        self._check_required_parameters(request=request)

        fs = self.get_filesystem(filesystem_name)
        projects = fs.get_projects()
        if project_name in projects:
            projects.remove(project_name)
            self._update_projects_for_filesystem(fs, projects)

    def list_file_systems_in_vpc(self) -> ListFileSystemInVPCResult:
        onboarded_filesystems = self._list_shared_filesystems()
        onboarded_filesystem_ids = set([fs.get_filesystem_id() for fs in onboarded_filesystems])

        efs_filesystems = self._list_unonboarded_efs_file_systems(onboarded_filesystem_ids)
        fsx_filesystems = self._list_unonboarded_ontap_file_systems(onboarded_filesystem_ids)

        return ListFileSystemInVPCResult(efs=efs_filesystems, fsx=fsx_filesystems)

    def update_filesystem_to_project_mapping(self, filesystem_name: str, project_name: str):
        fs = self.get_filesystem(filesystem_name)
        projects = fs.get_projects()
        if Utils.is_empty(projects):
            projects = []
        if project_name not in projects:
            projects.append(project_name)
            self._update_projects_for_filesystem(fs, projects)

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

    def _validate_onboard_filesystem_request(self, request: CommonOnboardFileSystemRequest):
        if not request.filesystem_id or not request.filesystem_name or not request.filesystem_title:
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_PARAMS,
                message="needed parameters cannot be empty",
            )

    def _validate_create_filesystem_request(self, request: CommonCreateFileSystemRequest):
        if not request.filesystem_name or not request.filesystem_title:
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_PARAMS,
                message="needed parameters cannot be empty",
            )
        ApiUtils.validate_input(request.filesystem_name,
            constants.FILE_SYSTEM_NAME_REGEX,
            constants.FILE_SYSTEM_NAME_ERROR_MESSAGE)

    def _validate_filesystem_does_not_exist(self, filesystem_name: str):
        try:
            if Utils.is_not_empty(self.get_filesystem(filesystem_name)):
                raise exceptions.soca_exception(
                    error_code=errorcodes.INVALID_PARAMS,
                    message=f"{filesystem_name} already exists",
                )
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.FILESYSTEM_NOT_FOUND or e.error_code == errorcodes.NO_SHARED_FILESYSTEM_FOUND:
                pass
            else:
                raise e

    def _validate_correct_subnet_selection(self, subnet_ids: Set[str]):
        res_private_subnets = self.config.db.get_config_entry("cluster.network.private_subnets")['value']
        for subnet_id in subnet_ids:
            if subnet_id is not None and subnet_id not in res_private_subnets:
                self.logger.error(f"{subnet_id} is not a RES private subnet")
                raise exceptions.soca_exception(
                    error_code=errorcodes.INVALID_PARAMS,
                    message=f"{subnet_id} is not a RES private subnet",
                )

    def _validate_filesystem_present_in_vpc_and_not_onboarded(self, filesystem_id):
        onboarded_filesystems = self._list_shared_filesystems()
        onboarded_filesystem_ids = set([fs.get_filesystem_id() for fs in onboarded_filesystems])

        if filesystem_id in onboarded_filesystem_ids:
            raise exceptions.soca_exception(
            error_code=errorcodes.FILESYSTEM_ALREADY_ONBOARDED,
            message=f"{filesystem_id} has already been onboarded"
        )

        efs_filesystems = self._list_unonboarded_efs_file_systems(onboarded_filesystem_ids)
        fsx_filesystems = self._list_unonboarded_ontap_file_systems(onboarded_filesystem_ids)

        filesystems_in_vpc = [*efs_filesystems, *fsx_filesystems]

        for filesystem in filesystems_in_vpc:
            if filesystem_id == filesystem.get_filesystem_id():
                return True

        raise exceptions.soca_exception(
            error_code=errorcodes.FILESYSTEM_NOT_IN_VPC,
            message=f"{filesystem_id} not part of the env's VPC thus not accessible"
        )

    def _update_projects_for_filesystem(
        self, filesystem: FileSystem, projects: List[str]
    ):
        self.config.db.set_config_entry(
            f"{constants.MODULE_SHARED_STORAGE}.{filesystem.get_name()}.projects",  # update entry on cluster settings dynamodb table
            projects,
        )
        self.config.put(
            f"{constants.MODULE_SHARED_STORAGE}.{filesystem.get_name()}.projects",  # update local config tree
            projects,
        )

    def _list_shared_filesystems(self) -> List[FileSystem]:
        shared_storage_config = self.config.get_config(constants.MODULE_SHARED_STORAGE)
        shared_storage_config_dict = shared_storage_config.as_plain_ordered_dict()

        filesystem: List[FileSystem] = []
        for fs_name, config in shared_storage_config_dict.items():
            if Utils.is_not_empty(Utils.get_as_dict(config)) and "projects" in list(
                config.keys()
            ):
                filesystem.append(FileSystem(name=fs_name, storage=config))

        return filesystem

    def get_filesystem(self, filesystem_name: str):
        filesystems = self._list_shared_filesystems()

        if Utils.is_empty(filesystems):
            raise exceptions.soca_exception(
                error_code=errorcodes.NO_SHARED_FILESYSTEM_FOUND,
                message="did not find any shared filesystem",
            )

        for fs in filesystems:
            if fs.get_name() == filesystem_name:
                return fs

        raise exceptions.soca_exception(
            error_code=errorcodes.FILESYSTEM_NOT_FOUND,
            message=f"could not find filesystem {filesystem_name}",
        )

    def _list_unonboarded_efs_file_systems(self, onboarded_filesystem_ids: Set[str]) -> List[EFSFileSystem]:
        try:
            onboarded_internal_filesystem_ids = [
                self.config.db.get_config_entry("shared-storage.home.efs.file_system_id")['value'],
                self.config.db.get_config_entry("shared-storage.internal.efs.file_system_id")['value']
            ]
            env_vpc_id = self.config.db.get_config_entry("cluster.network.vpc_id")['value']
            efs_client = self.context.aws().efs()
            efs_response = efs_client.describe_file_systems()["FileSystems"]

            filesystems: List[EFSFileSystem] = []
            for efs in efs_response:
                if efs['LifeCycleState'] != 'available':
                    continue
                fs_id = efs['FileSystemId']
                efs_mt_response = efs_client.describe_mount_targets(FileSystemId=fs_id)
                if len(efs_mt_response['MountTargets']) == 0:
                    continue
                if env_vpc_id == efs_mt_response['MountTargets'][0]['VpcId'] and \
                    fs_id not in onboarded_filesystem_ids and \
                    fs_id not in onboarded_internal_filesystem_ids:
                    filesystems.append(EFSFileSystem(efs = efs))
            return filesystems
        except botocore.exceptions.ClientError as e:
            error_message = e.response["Error"]["Message"]
            raise exceptions.general_exception(error_message)

    def _list_unonboarded_ontap_file_systems(self, onboarded_filesystem_ids: Set[str]) -> List[FSxONTAPFileSystem]:
        try:
            env_vpc_id = self.config.db.get_config_entry("cluster.network.vpc_id")['value']

            fsx_client = self.context.aws().fsx()
            fsx_response = fsx_client.describe_file_systems()["FileSystems"]
            ec2_client = self.context.aws().ec2()

            filesystems: List[FSxONTAPFileSystem] = []
            for fsx in fsx_response:
                if fsx['Lifecycle'] != 'AVAILABLE':
                    continue
                fs_id = fsx['FileSystemId']
                subnet_response = ec2_client.describe_subnets(SubnetIds=fsx['SubnetIds'])
                if env_vpc_id == subnet_response['Subnets'][0]['VpcId'] and \
                    fs_id not in onboarded_filesystem_ids:
                    volume_response = fsx_client.describe_volumes(
                        Filters=[{
                            'Name': 'file-system-id',
                            'Values': [fs_id]
                        }]
                    )
                    svm_response = fsx_client.describe_storage_virtual_machines(
                        Filters=[{
                            'Name': 'file-system-id',
                            'Values': [fs_id]
                        }]
                    )
                    if len(svm_response['StorageVirtualMachines']) == 0 or len(volume_response['Volumes']) == 0:
                        continue
                    list_created_svms = list(filter(
                        lambda svm_obj: svm_obj['Lifecycle'] == "CREATED",
                        svm_response['StorageVirtualMachines']
                    ))
                    list_created_volumes = list(filter(
                        lambda volume_obj: volume_obj['Lifecycle'] == "CREATED",
                        volume_response['Volumes']
                    ))
                    svm_list = [FSxONTAPSVM(storage_virtual_machine = svm) for svm in list_created_svms]
                    volume_list = [FSxONTAPVolume(volume = volume) for volume in list_created_volumes]
                    filesystems.append(FSxONTAPFileSystem(filesystem = fsx, svm = svm_list, volume = volume_list))
            return filesystems
        except botocore.exceptions.ClientError as e:
            error_message = e.response["Error"]["Message"]
            raise exceptions.general_exception(error_message)


    @staticmethod
    def _check_required_parameters(
        request: Union[
            AddFileSystemToProjectRequest, RemoveFileSystemFromProjectRequest
        ]
    ):
        if Utils.is_empty(request.filesystem_name):
            raise exceptions.invalid_params("filesystem_name is required")
        if Utils.is_empty(request.project_name):
            raise exceptions.invalid_params("project_name is required")
