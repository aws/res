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

import ideaadministrator
from ideadatamodel import (
    exceptions,
    errorcodes,
    constants
)

from ideasdk.utils import Utils, EnvironmentUtils
from ideasdk.user_input.framework import (
    SocaUserInputParamRegistry,
    SocaUserInputArgs
)

from ideasdk.context import SocaCliContext, SocaContextOptions
from ideasdk.config.cluster_config import ClusterConfig

from ideaadministrator.app.installer_params import SharedStoragePromptFactory
from ideaadministrator.app.deployment_helper import DeploymentHelper
from ideaadministrator.app.config_generator import ConfigGenerator

from typing import Dict, List, Optional

NEXT_STEP_UPDATE_SETTINGS = 'Update Cluster Settings and Exit'
NEXT_STEP_UPGRADE_MODULE = 'Deploy Module: Shared Storage'
NEXT_STEP_DEPLOY_MODULE = 'Upgrade Module: Shared Storage'
NEXT_STEP_EXIT = 'Exit'


class SharedStorageHelper:
    """
    Shared Storage Helper
    Utility class to manage, update and/or generate shared storage file systems cluster configurations.

    Supported File Systems:
        * Amazon EFS
        * Amazon File Cache
        * Amazon FSx for Lustre
        * Amazon FSx for NetApp ONTAP
        * Amazon FSx for OpenZFS
        * Amazon FSx for Windows File Server

    primary use-case for this class is to enable admins generate the shared storage configurations for various file systems supported by Engineering Studio.
    class can be used before or after updating cluster configuration DB.

    if the cluster configuration DB is updated with shared storage file systems, after any cluster nodes are launched,
    the existing node's fstab must be manually updated and mounted to reflect new file system config changes

    any new cluster nodes launched will mount the file systems based applicable scope and filters.

    What's supported?
    -----------------
    * Generate configurations for mounting new Amazon EFS file system
    * Generate configurations for mounting existing Amazon EFS + FSx file systems
       This works only if you have an existing file system provisioned via AWS Console or some other means and is associated to an existing VPC.
       The implementation does not perform any checks if cluster nodes can access the file system endpoints and the responsibility to check for
       network access/connectivity is delegated to the cluster administrator.

    Roadmap:
    -------
    * Generate configurations for provisioning new FSx file systems
    """

    def __init__(self, cluster_name: str, aws_region: str, aws_profile: str, kms_key_id: str):

        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.kms_key_id = kms_key_id

        self.config_initialized = False
        self.existing_cluster = False
        self.shared_storage_deployed = False
        self.context: Optional[SocaCliContext] = None

        if Utils.is_not_empty(self.cluster_name):
            try:

                self.context = SocaCliContext(options=SocaContextOptions(
                    cluster_name=cluster_name,
                    aws_region=aws_region,
                    aws_profile=aws_profile,
                    enable_aws_client_provider=True,
                    enable_aws_util=True,
                    locale=EnvironmentUtils.get_environment_variable('LC_CTYPE', default='en_US')
                ))
                self.config_initialized = True

                cluster_module_id = self.context.config().get_module_id(constants.MODULE_CLUSTER)
                cluster_module_info = self.context.get_cluster_module_info(module_id=cluster_module_id)
                self.existing_cluster = cluster_module_info['status'] == 'deployed'

                shared_storage_module_id = self.context.config().get_module_id(constants.MODULE_SHARED_STORAGE)
                shared_storage_module_info = self.context.get_cluster_module_info(module_id=shared_storage_module_id)
                self.shared_storage_deployed = shared_storage_module_info['status'] == 'deployed'

            except exceptions.SocaException as e:
                if e.error_code == errorcodes.CLUSTER_CONFIG_NOT_INITIALIZED:
                    pass
                else:
                    raise e

        if self.context is None:
            self.context = SocaCliContext(options=SocaContextOptions(
                aws_region=aws_region,
                aws_profile=aws_profile,
                enable_aws_client_provider=True,
                enable_aws_util=True
            ))

    def prompt(self, use_existing_fs: bool) -> Dict:
        # user input framework init
        param_registry = SocaUserInputParamRegistry(
            context=self.context,
            file=ideaadministrator.props.shared_storage_params_file
        )
        shared_storage_args = SocaUserInputArgs(
            context=self.context,
            param_registry=param_registry
        )
        prompt_factory = SharedStoragePromptFactory(
            context=self.context,
            args=shared_storage_args,
            param_registry=param_registry
        )

        shared_storage_args.set('use_existing_fs', use_existing_fs)

        # skip vpc selection prompt if cluster name is provided and cluster module is deployed
        if self.existing_cluster:
            vpc_id = self.context.config().get_string('cluster.network.vpc_id', required=True)
            shared_storage_args.set('vpc_id', vpc_id)

        # prompt common settings
        shared_storage_module = prompt_factory.build_module(
            user_input_module='common-settings',
            display_steps=False
        )
        shared_storage_result = shared_storage_module.safe_ask()

        provider = Utils.get_value_as_string('shared_storage_provider', shared_storage_result)

        if use_existing_fs:
            target_user_input_module = f'{provider}_existing'
        else:
            target_user_input_module = f'{provider}_new'

        # prompt provider specific settings
        provider_module = prompt_factory.build_module(
            user_input_module=target_user_input_module,
            display_info=False,
            display_steps=False
        )
        provider_result = provider_module.safe_ask()

        # merge and return result
        return {
            **shared_storage_result,
            **provider_result,
            'use_existing_fs': use_existing_fs
        }

    @staticmethod
    def get_delimited_tokens(s: str, delimiter: str = ',', default=None) -> List[str]:
        tokens = s.split(delimiter)
        result = []
        for token in tokens:
            if Utils.is_empty(token):
                continue
            token = Utils.get_as_string(token).strip().lower()
            result.append(token)
        if Utils.is_empty(result):
            return default
        return result

    def build_scope_config(self, params: Dict) -> Dict:

        scope = self.get_delimited_tokens(Utils.get_value_as_string('shared_storage_scope', params), default=['cluster'])

        scope_config = {
            'scope': scope
        }

        if 'module' in scope:
            modules = Utils.get_value_as_list('shared_storage_scope_modules', params, [])
            scope_config['modules'] = modules

        if 'project' in scope:
            projects = self.get_delimited_tokens(Utils.get_value_as_string('shared_storage_scope_projects', params), default=[constants.DEFAULT_PROJECT])
            scope_config['projects'] = projects

        if 'scheduler:queue-profile' in scope:
            queue_profiles = self.get_delimited_tokens(Utils.get_value_as_string('shared_storage_scope_queue_profiles', params), default=['compute'])
            scope_config['queue_profiles'] = queue_profiles

        return scope_config

    def build_common_config(self, params: Dict) -> Dict:
        provider = Utils.get_value_as_string('shared_storage_provider', params)
        config = {
            'title': Utils.get_value_as_string('shared_storage_title', params),
            'provider': provider,
            **self.build_scope_config(params)
        }

        if provider in (constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
                        constants.STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER):
            config['mount_drive'] = Utils.get_value_as_string('shared_storage_mount_drive', params, 'Z:')

        if provider != constants.STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER:
            config['mount_dir'] = Utils.get_value_as_string('shared_storage_mount_dir', params)
            config['mount_options'] = Utils.get_value_as_string(f'{provider}.mount_options', params)

        return config

    @staticmethod
    def use_existing_file_system(params: Dict) -> bool:
        return Utils.get_value_as_bool('use_existing_fs', params, False)

    def build_efs_config(self, params: Dict) -> Dict:

        name = Utils.get_value_as_string('shared_storage_name', params)

        if self.use_existing_file_system(params=params):

            file_system_id = Utils.get_value_as_string('efs.file_system_id', params)

            # describe efs does not return dns name. construct fs dns using below format
            # ensuring it is aws partition aware
            aws_region = self.aws_region
            aws_dns_suffix = self.context.aws().aws_dns_suffix()
            file_system_dns = f'{file_system_id}.efs.{aws_region}.{aws_dns_suffix}'

            describe_fs_result = self.context.aws().efs().describe_file_systems(
                FileSystemId=file_system_id
            )

            file_system = describe_fs_result['FileSystems'][0]
            encrypted = Utils.get_value_as_bool('Encrypted', file_system)

            config = {
                name: {
                    **self.build_common_config(params),
                    constants.STORAGE_PROVIDER_EFS: {
                        'use_existing_fs': True,
                        'file_system_id': Utils.get_value_as_string('efs.file_system_id', params),
                        'dns': file_system_dns,
                        'encrypted': encrypted
                    }
                }
            }
        else:
            transition_to_ia = Utils.get_value_as_string('efs.transition_to_ia', params)
            if transition_to_ia == 'DISABLED':
                transition_to_ia = None

            config = {
                name: {
                    **self.build_common_config(params),
                    'efs': {
                        'kms_key_id': self.kms_key_id,
                        'encrypted': True,
                        'throughput_mode': Utils.get_value_as_string('efs.throughput_mode', params),
                        'performance_mode': Utils.get_value_as_string('efs.performance_mode', params),
                        'removal_policy': Utils.get_value_as_string('efs.removal_policy', params, 'DESTROY'),
                        'cloudwatch_monitoring': Utils.get_value_as_bool('efs.cloudwatch_monitoring', params, False),
                        'transition_to_ia': transition_to_ia
                    }
                }
            }

        return config

    def build_fsx_cache_config(self, params: Dict) -> Dict:
        name = Utils.get_value_as_string('shared_storage_name', params)
        file_system_id = Utils.get_value_as_string('fsx_cache.file_system_id', params)
        describe_fs_result = self.context.aws().fsx().describe_file_caches(
            FileCacheIds=[file_system_id]
        )

        file_system = describe_fs_result['FileCaches'][0]
        file_system_dns = Utils.get_value_as_string('DNSName', file_system)
        lustre_config = Utils.get_value_as_dict('LustreConfiguration', file_system, {})
        mount_name = Utils.get_value_as_string('MountName', lustre_config)
        lustre_version = Utils.get_value_as_string('FileCacheTypeVersion', file_system)
        return {
            name: {
                **self.build_common_config(params),
                'fsx_cache': {
                    'use_existing_fs': True,
                    'file_system_id': file_system_id,
                    'dns': file_system_dns,
                    'mount_name': mount_name,
                    'version': lustre_version
                }
            }
        }

    def build_fsx_lustre_config(self, params: Dict) -> Dict:
        name = Utils.get_value_as_string('shared_storage_name', params)

        file_system_id = Utils.get_value_as_string('fsx_lustre.file_system_id', params)
        describe_fs_result = self.context.aws().fsx().describe_file_systems(
            FileSystemIds=[file_system_id]
        )

        file_system = describe_fs_result['FileSystems'][0]
        file_system_dns = Utils.get_value_as_string('DNSName', file_system)

        lustre_config = Utils.get_value_as_dict('LustreConfiguration', file_system, {})

        mount_name = Utils.get_value_as_string('MountName', lustre_config)
        lustre_version = Utils.get_value_as_string('FileSystemTypeVersion', file_system)

        return {
            name: {
                **self.build_common_config(params),
                'fsx_lustre': {
                    'use_existing_fs': True,
                    'file_system_id': file_system_id,
                    'dns': file_system_dns,
                    'mount_name': mount_name,
                    'version': lustre_version
                }
            }
        }

    def build_fsx_netapp_ontap_config(self, params: Dict) -> Dict:
        name = Utils.get_value_as_string('shared_storage_name', params)
        file_system_id = Utils.get_value_as_string('fsx_netapp_ontap.file_system_id', params)

        # fetch svm info
        svm_id = Utils.get_value_as_string('fsx_netapp_ontap.svm_id', params)
        describe_svm_result = self.context.aws().fsx().describe_storage_virtual_machines(
            StorageVirtualMachineIds=[svm_id]
        )
        svm = describe_svm_result['StorageVirtualMachines'][0]
        endpoints = Utils.get_value_as_dict('Endpoints', svm, {})

        nfs_endpoint = Utils.get_value_as_dict('Nfs', endpoints, {})
        nfs_dns = Utils.get_value_as_string('DNSName', nfs_endpoint)

        smb_endpoint = Utils.get_value_as_dict('Smb', endpoints, {})
        smb_dns = Utils.get_value_as_string('DNSName', smb_endpoint)

        management_endpoint = Utils.get_value_as_dict('Management', endpoints, {})
        management_dns = Utils.get_value_as_string('DNSName', management_endpoint)

        iscsi_endpoint = Utils.get_value_as_dict('Iscsi', endpoints, {})
        iscsi_dns = Utils.get_value_as_string('DNSName', iscsi_endpoint)

        # fetch volume info
        volume_id = Utils.get_value_as_string('fsx_netapp_ontap.volume_id', params)

        describe_volume_result = self.context.aws().fsx().describe_volumes(
            VolumeIds=[volume_id]
        )
        volume = describe_volume_result['Volumes'][0]
        volume_ontap_config = Utils.get_value_as_dict('OntapConfiguration', volume, {})

        volume_path = Utils.get_value_as_string('JunctionPath', volume_ontap_config)
        security_style = Utils.get_value_as_string('SecurityStyle', volume_ontap_config)
        cifs_share_name = Utils.get_value_as_string('fsx_netapp_ontap.cifs_share_name', params, default='')

        return {
            name: {
                **self.build_common_config(params),
                'fsx_netapp_ontap': {
                    'use_existing_fs': True,
                    'file_system_id': file_system_id,
                    'svm': {
                        'svm_id': svm_id,
                        'smb_dns': smb_dns,
                        'nfs_dns': nfs_dns,
                        'management_dns': management_dns,
                        'iscsi_dns': iscsi_dns
                    },
                    'volume': {
                        'volume_id': volume_id,
                        'volume_path': volume_path,
                        'security_style': security_style,
                        'cifs_share_name': cifs_share_name
                    }
                }
            }
        }

    def build_fsx_openzfs_config(self, params: Dict) -> Dict:
        name = Utils.get_value_as_string('shared_storage_name', params)

        file_system_id = Utils.get_value_as_string('fsx_openzfs.file_system_id', params)
        describe_fs_result = self.context.aws().fsx().describe_file_systems(
            FileSystemIds=[file_system_id]
        )

        file_system = describe_fs_result['FileSystems'][0]
        file_system_dns = Utils.get_value_as_string('DNSName', file_system)

        volume_id = Utils.get_value_as_string('fsx_openzfs.volume_id', params)

        describe_volume_result = self.context.aws().fsx().describe_volumes(
            VolumeIds=[volume_id]
        )
        volume = describe_volume_result['Volumes'][0]
        volume_ontap_config = Utils.get_value_as_dict('OpenZFSConfiguration', volume, {})
        volume_path = Utils.get_value_as_string('VolumePath', volume_ontap_config)

        return {
            name: {
                **self.build_common_config(params),
                'fsx_openzfs': {
                    'use_existing_fs': True,
                    'file_system_id': file_system_id,
                    'dns': file_system_dns,
                    'volume_id': volume_id,
                    'volume_path': volume_path
                }
            }
        }

    def build_fsx_windows_file_server_config(self, params: Dict) -> Dict:
        name = Utils.get_value_as_string('shared_storage_name', params)

        file_system_id = Utils.get_value_as_string('fsx_windows_file_server.file_system_id', params)
        describe_fs_result = self.context.aws().fsx().describe_file_systems(
            FileSystemIds=[file_system_id]
        )

        file_system = describe_fs_result['FileSystems'][0]
        file_system_dns = Utils.get_value_as_string('DNSName', file_system)

        windows_config = Utils.get_value_as_dict('WindowsConfiguration', file_system, {})
        preferred_file_server_ip = Utils.get_value_as_string('PreferredFileServerIp', windows_config)

        return {
            name: {
                **self.build_common_config(params),
                'fsx_windows_file_server': {
                    'use_existing_fs': True,
                    'file_system_id': file_system_id,
                    'dns': file_system_dns,
                    'preferred_file_server_ip': preferred_file_server_ip
                }
            }
        }

    def build_shared_storage_config(self, params: Dict) -> Dict:
        provider = Utils.get_value_as_string('shared_storage_provider', params)

        if provider == constants.STORAGE_PROVIDER_EFS:
            return self.build_efs_config(params=params)
        elif provider == constants.STORAGE_PROVIDER_FSX_CACHE:
            return self.build_fsx_cache_config(params=params)
        elif provider == constants.STORAGE_PROVIDER_FSX_LUSTRE:
            return self.build_fsx_lustre_config(params=params)
        elif provider == constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP:
            return self.build_fsx_netapp_ontap_config(params=params)
        elif provider == constants.STORAGE_PROVIDER_FSX_OPENZFS:
            return self.build_fsx_openzfs_config(params=params)
        elif provider == constants.STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER:
            return self.build_fsx_windows_file_server_config(params=params)

        raise exceptions.general_exception(f'shared storage provider: {provider} not supported')

    def print_config(self, config: Dict):
        self.context.print_rule('Shared Storage Config')
        self.context.new_line()
        config_yaml = Utils.to_yaml(config)
        config_yaml = config_yaml.replace(': null', ': ~')
        print(config_yaml)
        self.context.print_rule()

    def prompt_next_step(self, params: Dict) -> str:
        next_step_choices = [NEXT_STEP_EXIT]

        if self.config_initialized:
            next_step_choices.append(NEXT_STEP_UPDATE_SETTINGS)

        if not self.use_existing_file_system(params=params) and self.existing_cluster:
            if self.shared_storage_deployed:
                next_step_choices.append(NEXT_STEP_UPGRADE_MODULE)
            else:
                next_step_choices.append(NEXT_STEP_DEPLOY_MODULE)

        if len(next_step_choices) == 1:
            return NEXT_STEP_EXIT

        return self.context.prompt(
            message='How do you want to proceed further?',
            default=NEXT_STEP_EXIT,
            choices=next_step_choices
        )

    def update_cluster_settings(self, module_id: str, config: Dict):
        config_generator = ConfigGenerator(
            values={}
        )
        config_entries = []
        config_generator.traverse_config(
            config_entries=config_entries,
            prefix=module_id,
            config=config
        )

        cluster_config: ClusterConfig = self.context.config()
        cluster_config.db.sync_cluster_settings_in_db(
            config_entries=config_entries,
            overwrite=True
        )

    def add_file_system(self, use_existing_fs: bool):

        # ask for input
        params = self.prompt(use_existing_fs=use_existing_fs)

        # build config
        config = self.build_shared_storage_config(params=params)

        # print config
        self.print_config(config=config)

        # what to do next?
        next_step = self.prompt_next_step(params=params)

        if next_step == NEXT_STEP_EXIT:
            raise SystemExit

        if next_step == NEXT_STEP_UPDATE_SETTINGS:
            module_id = self.context.config().get_module_id(constants.MODULE_SHARED_STORAGE)
            self.update_cluster_settings(module_id=module_id, config=config)
            raise SystemExit

        if next_step in (NEXT_STEP_DEPLOY_MODULE, NEXT_STEP_UPGRADE_MODULE):
            module_id = self.context.config().get_module_id(constants.MODULE_SHARED_STORAGE)
            self.update_cluster_settings(module_id=module_id, config=config)
            DeploymentHelper(
                cluster_name=self.cluster_name,
                aws_region=self.aws_region,
                upgrade=next_step == NEXT_STEP_UPGRADE_MODULE,
                all_modules=False,
                module_ids=[module_id],
                aws_profile=self.aws_profile
            ).deploy_module(module_id)
