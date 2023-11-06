#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List, Union, Set
import botocore.exceptions
from pydantic import ValidationError

import ideaclustermanager
from ideaclustermanager.app.shared_filesystem.shared_filesystem_service import (
    SharedFilesystemService,
)
from ideadatamodel.exceptions import SocaException
from ideadatamodel.shared_filesystem.shared_filesystem_api import FSxONTAPDeploymentType

from ideasdk.api import ApiInvocationContext, BaseAPI
from ideadatamodel.shared_filesystem import (
    AddFileSystemToProjectRequest,
    RemoveFileSystemFromProjectRequest,
    AddFileSystemToProjectResult,
    RemoveFileSystemFromProjectResult,
    CommonCreateFileSystemRequest,
    CreateFileSystemResult,
    FileSystem,
    FSxONTAPSVM,
    FSxONTAPVolume,
    ListFileSystemInVPCResult,
    CommonOnboardFileSystemRequest,
    OnboardEFSFileSystemRequest,
    OnboardONTAPFileSystemRequest,
    OnboardFileSystemResult,
    CreateEFSFileSystemRequest,
    CreateONTAPFileSystemRequest,
    EFSFileSystem,
    FSxONTAPFileSystem,
)
from ideadatamodel import (
    exceptions,
    constants,
    errorcodes,
)
from ideasdk.utils import Utils


class FileSystemAPI(BaseAPI):
    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context
        self.config = self.context.config()
        self.shared_filesystem_service = SharedFilesystemService(context=self.context)
        self.logger = self.context.logger("shared-filesystem")

        self.SCOPE_WRITE = f"{self.context.module_id()}/write"
        self.SCOPE_READ = f"{self.context.module_id()}/read"

        self.acl = {
            "FileSystem.AddFileSystemToProject": {
                "scope": self.SCOPE_WRITE,
                "method": self.add_filesystem_to_project,
            },
            "FileSystem.RemoveFileSystemFromProject": {
                "scope": self.SCOPE_WRITE,
                "method": self.remove_filesystem_from_project,
            },
            "FileSystem.CreateEFS": {
                "scope": self.SCOPE_WRITE,
                "method": self.create_filesystem,
            },
            "FileSystem.CreateONTAP": {
                "scope": self.SCOPE_WRITE,
                "method": self.create_filesystem,
            },
            "FileSystem.ListFSinVPC": {
                "scope": self.SCOPE_READ,
                "method": self.list_file_systems_in_vpc,
            },
            "FileSystem.OnboardEFSFileSystem": {
                "scope": self.SCOPE_WRITE,
                "method": self.onboard_filesystem,
            },
            "FileSystem.OnboardONTAPFileSystem": {
                "scope": self.SCOPE_WRITE,
                "method": self.onboard_filesystem,
            }
        }

    def create_filesystem(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(CommonCreateFileSystemRequest)
        if Utils.is_any_empty(
            request.filesystem_name,
            request.filesystem_title,
        ):
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_PARAMS,
                message="needed parameters cannot be empty",
            )
        try:
            if context.namespace == "FileSystem.CreateEFS":
                self._create_efs(
                    context.get_request_payload_as(CreateEFSFileSystemRequest)
                )
            elif context.namespace == "FileSystem.CreateONTAP":
                self._create_fsx_ontap(
                    context.get_request_payload_as(CreateONTAPFileSystemRequest)
                )
        except ValidationError as e:
            self.logger.error(e.json())
            raise exceptions.general_exception(str(e.errors()))

        context.success(CreateFileSystemResult())

    def _create_efs(self, request: CreateEFSFileSystemRequest):
        self._validate_correct_subnet_selection({request.subnet_id_1, request.subnet_id_2})
        self._validate_filesystem_does_not_exist(request.filesystem_name)
        try:
            efs_client = self.context.aws().efs()
            security_group_id = self.config.get_string(
                f"{constants.MODULE_SHARED_STORAGE}.security_group_id"
            )

            tags_for_fs = self.shared_filesystem_service.create_tags(
                request.filesystem_name
            )

            efs_create_response = efs_client.create_file_system(
                ThroughputMode="elastic", Encrypted=True, Tags=tags_for_fs
            )
            efs_filesystem = EFSFileSystem(efs=efs_create_response)
            efs_filesystem_id = efs_filesystem.get_filesystem_id()

            self.shared_filesystem_service.efs_check_filesystem_exists(
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
                        "Resource": f"arn:aws:elasticfilesystem:{self.context.aws().aws_region()}:{self.context.aws().aws_account_id()}:file-system/{efs_filesystem_id}",
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
            config_entries = self.shared_filesystem_service.build_config_for_new_efs(
                efs=efs_filesystem, request=request
            )
            self.config.db.sync_cluster_settings_in_db(
                config_entries=config_entries, overwrite=True
            )
        except botocore.exceptions.ClientError as e:
            error_message = e.response["Error"]["Message"]
            raise exceptions.general_exception(error_message)

    def _create_fsx_ontap(self, request: CreateONTAPFileSystemRequest):
        self._validate_correct_subnet_selection({request.primary_subnet, request.standby_subnet})
        self._validate_filesystem_does_not_exist(request.filesystem_name)
        try:
            fsx_client = self.context.aws().fsx()
            security_group_id = self.config.get_string(
                f"{constants.MODULE_SHARED_STORAGE}.security_group_id"
            )

            tags_for_fs = self.shared_filesystem_service.create_tags(
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
            config_entries = self.shared_filesystem_service.build_config_for_new_ontap(
                svm=fsx_ontap_svm, volume=fsx_ontap_volume, request=request
            )
            self.config.db.sync_cluster_settings_in_db(
                config_entries=config_entries, overwrite=True
            )
        except botocore.exceptions.ClientError as e:
            error_message = e.response["Error"]["Message"]
            self.logger.error(error_message)
            raise exceptions.general_exception(error_message)

    def add_filesystem_to_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(AddFileSystemToProjectRequest)

        filesystem_name = request.filesystem_name
        project_name = request.project_name
        self._check_required_parameters(request=request)
        self.update_filesystem_to_project_mapping(filesystem_name, project_name)
        context.success(AddFileSystemToProjectResult())

    def update_filesystem_to_project_mapping(self, filesystem_name: str, project_name: str):
        fs = self._get_filesystem(filesystem_name)
        projects = fs.get_projects()
        if Utils.is_empty(projects):
            projects = []
        if project_name not in projects:
            projects.append(project_name)
            self._update_projects_for_filesystem(fs, projects)

    def remove_filesystem_from_project(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(RemoveFileSystemFromProjectRequest)

        filesystem_name = request.filesystem_name
        project_name = request.project_name
        self._check_required_parameters(request=request)

        fs = self._get_filesystem(filesystem_name)
        projects = fs.get_projects()
        if project_name in projects:
            projects.remove(project_name)
            self._update_projects_for_filesystem(fs, projects)

        context.success(RemoveFileSystemFromProjectResult())

    def list_file_systems_in_vpc(self, context: ApiInvocationContext):
        onboarded_filesystems = self._list_shared_filesystems()
        onboarded_filesystem_ids = set([fs.get_filesystem_id() for fs in onboarded_filesystems])

        efs_filesystems = self._list_unonboarded_efs_file_systems(onboarded_filesystem_ids)
        fsx_filesystems = self._list_unonboarded_ontap_file_systems()
        context.success(ListFileSystemInVPCResult(efs=efs_filesystems, fsx=fsx_filesystems))

    def onboard_filesystem(self, context: ApiInvocationContext):
        request = context.get_request_payload_as(CommonOnboardFileSystemRequest)
        if Utils.is_any_empty(
            request.filesystem_id,
            request.filesystem_name,
            request.filesystem_title,
        ):
            raise exceptions.soca_exception(
                error_code=errorcodes.INVALID_PARAMS,
                message="needed parameters cannot be empty",
            )
        self._validate_filesystem_does_not_exist(request.filesystem_name)
        if context.namespace == 'FileSystem.OnboardEFSFileSystem':
            config_entries = self.shared_filesystem_service.build_config_for_vpc_efs(context.get_request_payload_as(OnboardEFSFileSystemRequest))
            self.context.config().db.sync_cluster_settings_in_db(
                config_entries=config_entries,
                overwrite=True
            )
        elif context.namespace == 'FileSystem.OnboardONTAPFileSystem':
            config_entries = self.shared_filesystem_service.build_config_for_vpc_ontap(context.get_request_payload_as(OnboardONTAPFileSystemRequest))
            self.context.config().db.sync_cluster_settings_in_db(
                config_entries=config_entries,
                overwrite=True
            )
        context.success(OnboardFileSystemResult())

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

    def _list_unonboarded_ontap_file_systems(self) -> List[FSxONTAPFileSystem]:
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
                if env_vpc_id == subnet_response['Subnets'][0]['VpcId']:
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

    def _get_filesystem(self, filesystem_name: str):
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

    def _validate_filesystem_does_not_exist(self, filesystem_name: str):
        try:
            if Utils.is_not_empty(self._get_filesystem(filesystem_name)):
                raise exceptions.soca_exception(
                    error_code=errorcodes.INVALID_PARAMS,
                    message=f"{filesystem_name} already exists",
                )
        except SocaException as e:
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

    def invoke(self, context: ApiInvocationContext):
        namespace = context.namespace

        acl_entry = Utils.get_value_as_dict(namespace, self.acl)
        if acl_entry is None:
            raise exceptions.unauthorized_access()

        acl_entry_scope = Utils.get_value_as_string("scope", acl_entry)
        is_authorized = context.is_authorized(
            elevated_access=True, scopes=[acl_entry_scope]
        )

        if is_authorized:
            acl_entry["method"](context)
        else:
            raise exceptions.unauthorized_access()
