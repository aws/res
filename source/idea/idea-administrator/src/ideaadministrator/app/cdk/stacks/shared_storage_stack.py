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

from ideadatamodel import (
    constants, exceptions
)
from ideasdk.utils import Utils

import ideaadministrator
from ideaadministrator.app.cdk.stacks import IdeaBaseStack
from ideaadministrator import app_constants
from ideaadministrator.app_context import AdministratorContext

from ideaadministrator.app.cdk.constructs import (
    AmazonEFS,
    FSxForLustre,
    SharedStorageSecurityGroup,
    ExistingSocaCluster
)
from typing import Optional, Union, Dict, List
import aws_cdk as cdk
import constructs


class FileSystemHolder:
    """
    Holder object to build cluster settings
    """

    def __init__(self, context: AdministratorContext,
                 name: str,
                 storage_config: Dict,
                 file_system_id: str,
                 file_system: Optional[Union[AmazonEFS, FSxForLustre]] = None):

        self._context = context
        self.name = name
        self.storage_config = storage_config
        self.file_system_id = file_system_id
        self.file_system = file_system

    @property
    def provider(self) -> str:
        return self.storage_config.get('provider')

    def get_fs_type(self) -> str:
        if self.provider == 'efs':
            return 'efs'
        else:
            return 'fsx'

    @property
    def file_system_dns(self) -> str:
        aws_region = self._context.config().get_string('cluster.aws.region', required=True)
        aws_dns_suffix = self._context.config().get_string('cluster.aws.dns_suffix', required=True)
        return f'{self.file_system_id}.{self.get_fs_type()}.{aws_region}.{aws_dns_suffix}'


class SharedStorageStack(IdeaBaseStack):
    """
    Shared Storage Stack
     * Provisions applicable file systems configured in shared-storage settings.
     * Internal and Data file systems are mandatory and must exist in configuration.
    """

    def __init__(self, scope: constructs.Construct,
                 cluster_name: str,
                 aws_region: str,
                 aws_profile: str,
                 module_id: str,
                 deployment_id: str,
                 termination_protection: bool = True,
                 env: cdk.Environment = None):

        super().__init__(
            scope=scope,
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            module_id=module_id,
            deployment_id=deployment_id,
            termination_protection=termination_protection,
            description=f'ModuleId: {module_id}, Cluster: {cluster_name}, Version: {ideaadministrator.props.current_release_version}',
            tags={
                constants.IDEA_TAG_MODULE_ID: module_id,
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_SHARED_STORAGE,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.security_group: Optional[SharedStorageSecurityGroup] = None
        self.file_systems: List[FileSystemHolder] = []

        self.cluster = ExistingSocaCluster(self.context, self.stack)

        # verify if `internal` and `home` storage is configured
        # simple check to ensure internal and home config keys exist
        self.context.config().get_string('shared-storage.internal.provider', required=True)
        self.context.config().get_string('shared-storage.home.provider', required=True)

        # build security group
        self.build_security_group()

        # build applicable file systems
        self.build_shared_storage()

        # build cluster settings
        self.build_cluster_settings()

    def build_security_group(self):
        self.security_group = SharedStorageSecurityGroup(
            context=self.context,
            name='shared-storage-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc
        )

    def build_shared_storage(self):
        """
        loop over all file system settings and provisions new file systems for applicable provider
        provisioning of new file systems is limited to Internal and Home.
        """
        storage_configs = self.context.config().get_config('shared-storage', required=True)
        for key in storage_configs:
            storage_config = storage_configs.get(key)

            # future-proof - so that if/when new non storage config keys are added, implementation should not bomb
            if not isinstance(storage_config, Dict):
                continue

            # if the dict/config object does not contain 'provider' and 'mount_dir' key, assume it is not a storage config
            provider = storage_config.get('provider', default=None)
            mount_dir = storage_config.get('mount_dir', default=None)
            if Utils.is_empty(provider) or Utils.is_empty(mount_dir):
                continue

            if provider not in constants.SUPPORTED_STORAGE_PROVIDERS:
                raise exceptions.cluster_config_error(f'file system provider: {provider} not supported')

            # if existing file system, add to registry and skip provisioning.
            existing_fs = storage_config.get(f'{provider}.use_existing_fs', default=False)
            if existing_fs:
                file_system_id = storage_config.get(f'{provider}.file_system_id')
                if not file_system_id:
                    raise exceptions.cluster_config_error(f'shared-storage.{key}.{provider}.file_system_id is required')

                self.file_systems.append(FileSystemHolder(
                    context=self.context,
                    name=key,
                    storage_config=storage_config,
                    file_system_id=file_system_id
                ))
                continue

            if key == 'home' or key == 'internal':
                # provision new file systems
                if provider == constants.STORAGE_PROVIDER_EFS:
                    self.build_efs(name=key, storage_config=storage_config)
                elif provider == constants.STORAGE_PROVIDER_FSX_LUSTRE:
                    self.build_fsx_lustre(name=key, storage_config=storage_config)

    def build_efs(self, name: str, storage_config: Dict):
        """
        provision new EFS
        """
        efs = AmazonEFS(
            context=self.context,
            name=f'{name}-storage-efs',
            scope=self.stack,
            vpc=self.cluster.vpc,
            efs_config=storage_config.get('efs'),
            security_group=self.security_group,
            log_retention_role=self.cluster.get_role(app_constants.LOG_RETENTION_ROLE_NAME),
            subnets=self.cluster.private_subnets
        )
        self.file_systems.append(FileSystemHolder(
            context=self.context,
            name=name,
            storage_config=storage_config,
            file_system_id=efs.file_system.ref,
            file_system=efs
        ))

    def build_fsx_lustre(self, name: str, storage_config: Dict):
        """
        provision new FSx for Lustre file system
        """
        fsx_lustre = FSxForLustre(
            context=self.context,
            name=f'{name}-storage-fsx-lustre',
            scope=self.stack,
            vpc=self.cluster.vpc,
            fsx_lustre_config=storage_config.get('fsx_lustre'),
            security_group=self.security_group,
            subnets=self.cluster.private_subnets
        )
        self.file_systems.append(FileSystemHolder(
            context=self.context,
            name=name,
            storage_config=storage_config,
            file_system_id=fsx_lustre.file_system.ref,
            file_system=fsx_lustre
        ))

    def build_cluster_settings(self):

        cluster_settings = {
            'deployment_id': self.deployment_id,
            'security_group_id': self.security_group.security_group_id
        }

        for file_system in self.file_systems:

            # cluster settings for file system dns need to be updated only if new file systems are provisioned for efs and fsx_lustre
            # if existing file systems configurations are added/updated via ./res-admin.sh shared-storage utility, dns property will already exist.
            if file_system.provider in [
                constants.STORAGE_PROVIDER_EFS,
                constants.STORAGE_PROVIDER_FSX_LUSTRE
            ]:
                file_system_dns = self.context.config().get_string(f'shared-storage.{self.name}.dns')
                if Utils.is_empty(file_system_dns):
                    cluster_settings[f'{file_system.name}.{file_system.provider}.dns'] = file_system.file_system_dns

            # skip settings update for existing file systems
            if file_system.file_system is None:
                continue

            cluster_settings[f'{file_system.name}.{file_system.provider}.file_system_id'] = file_system.file_system_id

        self.update_cluster_settings(cluster_settings)
