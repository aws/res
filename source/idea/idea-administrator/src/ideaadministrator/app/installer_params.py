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

__all__ = (
    'DefaultPrompt',
    'ClusterNamePrompt',
    'AwsProfilePrompt',
    'AwsPartitionPrompt',
    'AwsRegionPrompt',
    'ClientIPPrompt',
    'SSHKeyPairPrompt',
    'VpcCidrBlockPrompt',
    'EmailPrompt',
    'VpcIdPrompt',
    'ExistingResourcesPrompt',
    'SubnetIdsPrompt',
    'FileSystemIdPrompt',
    'DirectoryServiceIdPrompt',
    'PrefixListIdPrompt',
    'EnabledModulesPrompt',
    'MetricsProviderPrompt',
    'SharedStorageProviderPrompt',
    'SharedStorageNamePrompt',
    'SharedStorageVirtualMachineIdPrompt',
    'SharedStorageVolumeIdPrompt',
    'InstallerPromptFactory',
    'QuickSetupPromptFactory',
    'SharedStoragePromptFactory'
)

from ideasdk.utils import Utils
from ideadatamodel import exceptions, errorcodes, constants
from ideasdk.user_input.framework import (
    SocaPrompt,
    SocaUserInputSection,
    SocaUserInputModule,
    SocaUserInputDefaultType,
    SocaUserInputChoicesType,
    SocaUserInputChoice,
    SocaPromptRegistry,
    SocaUserInputParamRegistry,
    SocaUserInputArgs
)
from ideadatamodel.user_input import SocaUserInputParamMetadata
from ideasdk.context import SocaCliContext

import ideaadministrator
from ideaadministrator import app_constants
from ideaadministrator.app_utils import AdministratorUtils
from ideaadministrator.app.aws_service_availability_helper import AwsServiceAvailabilityHelper

from typing import Optional, List, TypeVar
import validators

T = TypeVar('T')
SELECT_CHOICE_OTHER = constants.SELECT_CHOICE_OTHER


class DefaultPrompt(SocaPrompt[T]):

    def __init__(self, factory: 'InstallerPromptFactory',
                 param: SocaUserInputParamMetadata,
                 default: SocaUserInputDefaultType = None,
                 choices: SocaUserInputChoicesType = None):
        if default is None:
            default = self.get_default
        self.factory = factory
        super().__init__(context=factory.context,
                         args=factory.args,
                         param=param,
                         default=default,
                         choices=choices,
                         registry=factory.install_prompts)
        self._args = factory.args
        self.context = factory.context

    @property
    def args(self) -> SocaUserInputArgs:
        return self._args

    def get_default(self, reset: bool = False) -> T:
        if reset:
            return None
        else:
            return self.args.get(self.name)

    def validate(self, value: T):
        super().validate(value)


class ClusterNamePrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('cluster_name'))

    def validate(self, value: str):

        super().validate(value)

        # validate is not called for choice. so we are good here ...
        token = AdministratorUtils.sanitize_cluster_name(value)
        if Utils.is_empty(token):
            return

        if token == f'{app_constants.CLUSTER_NAME_PREFIX}-{SELECT_CHOICE_OTHER}':
            raise self.validation_error(message=f'Invalid ClusterName: {token}. '
                                                f'"{SELECT_CHOICE_OTHER}" is a reserved keyword and cannot be used in ClusterName.')

        if 'res' in token.replace('res-', '', 1):
            raise self.validation_error(message=f'Invalid ClusterName: {token}. '
                                                f'"{token}" contains value "res" and is not allowed.')

        min_length, max_length = app_constants.CLUSTER_NAME_MIN_MAX_LENGTH
        if not min_length <= len(token) <= max_length:
            raise self.validation_error(message=f'ClusterName: ({token}) length must be between {min_length} and {max_length} characters. '
                                                f'Current: {len(token)}')

        regenerate = Utils.get_as_bool(self.args.get('_regenerate'), False)
        if regenerate:
            return

        vpcs = Utils.get_as_list(self.context.get_aws_resources().get_vpcs(), [])
        for vpc in vpcs:
            if vpc.cluster_name is None:
                continue
            if vpc.cluster_name == token:
                raise self.validation_error(message=f'Cluster: ({token}) already exists and is in use by Vpc: {vpc.vpc_id}. '
                                                    f'Please enter a different cluster name.')

        bootstrap_stack_name = f'{token}-bootstrap'
        existing_bootstrap_stack = self.context.aws_util().cloudformation_describe_stack(bootstrap_stack_name)
        if existing_bootstrap_stack is not None:
            raise self.validation_error(message=f'Cluster: ({token}) already exists and is in use by Bootstrap Stack: {bootstrap_stack_name}. '
                                                f'Please enter a different cluster name.')

    def filter(self, value: str) -> Optional[str]:
        token = AdministratorUtils.sanitize_cluster_name(value)
        cluster_name = super().filter(token)
        return cluster_name

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        installed_clusters = self.context.get_aws_resources().list_available_cluster_names()
        choices = []
        for cluster_name in installed_clusters:
            choices.append(SocaUserInputChoice(title=cluster_name, value=cluster_name))
        return choices


class AwsProfilePrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('aws_profile'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        profiles = self.context.get_aws_resources().get_aws_profiles(refresh)
        choices = []
        for profile in profiles:
            choices.append(SocaUserInputChoice(title=profile.title, value=profile.name))
        return choices


# In some situations a secondary AWS profile may be needed.
# This can include partitions (GovCloud) that do not support all
# services or functions.
class AwsProfilePrompt2(DefaultPrompt[str]):
    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('aws_profile2'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        profiles = self.context.get_aws_resources().get_aws_profiles(refresh)
        choices = []
        for profile in profiles:
            choices.append(SocaUserInputChoice(title=profile.title, value=profile.name))
        return choices


class AwsPartitionPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('aws_partition'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        partitions = self.context.aws().aws_endpoints().list_partitions()
        choices = []
        for partition in partitions:
            title = f'{partition.name} [{partition.partition}]'
            choices.append(SocaUserInputChoice(title=title, value=partition.partition))
        return choices


class AwsRegionPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('aws_region'),
                         default=self.get_default)

    def get_partition(self) -> Optional[str]:
        partition_prompt = self.factory.install_prompts.get('aws_partition')
        return partition_prompt.default()

    def get_default(self, reset: bool = False) -> Optional[str]:
        region = self.args.get('aws_region')

        partition = self.context.aws().aws_endpoints().get_partition(partition=self.get_partition())
        regions = partition.regions
        for region_ in regions:
            if region_.region == region:
                return region

        partition = self.get_partition()

        custom = self.param.custom
        defaults = Utils.get_value_as_dict('defaults', custom)

        return Utils.get_value_as_string(partition, defaults)

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        partition = self.context.aws().aws_endpoints().get_partition(partition=self.get_partition())
        regions = partition.regions
        choices = []
        for region in regions:
            title = f'{region.name} [{region.region}]'
            choices.append(SocaUserInputChoice(title=title, value=region.region))
        return choices


class ClientIPPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory,
                         param=factory.args.get_meta('client_ip'),
                         default=self.get_default)

    def get_default(self, reset: bool = False) -> Optional[str]:
        if not reset:
            client_ip = self.args.get('client_ip')
            if client_ip:
                return client_ip
        return AdministratorUtils.detect_client_ip()

    def filter(self, value: str) -> List[str]:
        tokens = value.split(',')
        result = []
        for token in tokens:
            if Utils.is_empty(token):
                continue
            if '/' not in token:
                token = f'{token}/32'
            result.append(token.strip())
        super().filter(result)
        return result


class SSHKeyPairPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory', param: SocaUserInputParamMetadata):
        super().__init__(factory=factory, param=param)

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        result = []

        key_pairs = self.context.get_aws_resources().get_ec2_key_pairs(refresh)
        if key_pairs is None:
            key_pairs = []

        if len(key_pairs) == 0:
            raise exceptions.soca_exception(error_code=errorcodes.USER_INPUT_FLOW_INTERRUPT,
                                            message='Unable to find any existing EC2 SSH Key Pairs in this region.'
                                                    'Create a new EC2 Key Pair from the AWS Console and re-run res-admin.')

        for key_pair in key_pairs:
            result.append(SocaUserInputChoice(
                title=key_pair.key_name,
                value=key_pair.key_name
            ))

        return result


class VpcCidrBlockPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('vpc_cidr_block'),
                         default=self.get_default)

    def get_default(self, reset: bool = False) -> Optional[str]:
        vpcs = self.context.get_aws_resources().get_vpcs()
        if len(vpcs) == 0:
            return self.param.get_default()

        cidr_blocks = {}
        for vpc in vpcs:
            cidr_blocks[vpc.cidr_block] = True

        for i in range(0, 255):
            candidate = f'10.{i}.0.0/16'
            if candidate in cidr_blocks:
                continue
            return candidate

    def validate(self, value: str):

        super().validate(value)

        vpcs = self.context.get_aws_resources().get_vpcs()
        if len(vpcs) == 0:
            return

        regenerate = Utils.get_as_bool(self.args.get('_regenerate'), False)
        if regenerate:
            return

        for vpc in vpcs:
            if value == vpc.cidr_block:
                raise self.validation_error(
                    message=f'VPC CIDR Block: {value} is already used by VPC: {vpc.vpc_id}. Please enter a different CIDR block '
                            f'to avoid IP Address conflicts between VPCs.'
                )


class EmailPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory', param: SocaUserInputParamMetadata):
        super().__init__(factory=factory,
                         param=param)

    def validate(self, value: str):
        super().validate(value)
        if not validators.email(value):
            raise self.validation_error('Invalid Email Address')


class VpcIdPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('vpc_id'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        vpcs = self.context.get_aws_resources().get_vpcs(refresh)

        if len(vpcs) == 0:
            raise exceptions.general_exception('Unable to find any existing VPC in this region.')

        choices = []

        for vpc in vpcs:
            choices.append(SocaUserInputChoice(
                title=f'{vpc.title}',
                value=vpc.vpc_id
            ))

        return choices

    def filter(self, value) -> Optional[T]:
        self.args.set('use_existing_vpc', True)
        return super().filter(value)


class ExistingResourcesPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('existing_resources'),
                         default=self.get_default)
        self.existing_file_systems = False
        self.existing_subnets = False
        self.existing_directories = False

        self.vpc_id = None

    def get_default(self, reset: bool = False) -> Optional[List[str]]:
        result = []
        if self.existing_subnets:
            result.append('subnets:public')
            result.append('subnets:private')
        if self.existing_file_systems:
            result.append('shared-storage:internal')
            result.append('shared-storage:home')
        if self.existing_directories:
            result.append('directoryservice:aws_managed_activedirectory')
        return result

    def validate(self, value: List[str]):
        if Utils.is_empty(value):
            raise self.validation_error(
                message='Existing resource selection is required'
            )
        if 'subnets:public' not in value and 'subnets:private' not in value:
            raise self.validation_error(
                message='Either one of [Subnets: Public, Subnets: Private] is required'
            )

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:

        vpc_id = self.args.get('vpc_id')
        if Utils.is_empty(vpc_id):
            raise exceptions.general_exception('vpc_id is required to find existing resources')

        alb_public = Utils.get_as_bool(self.args.get('alb_public'), default=True)

        if Utils.is_not_empty(self.vpc_id):
            if self.vpc_id != vpc_id:
                refresh = True

        self.vpc_id = vpc_id

        with self.context.spinner('search for existing subnets ...'):
            subnets = self.context.get_aws_resources().get_subnets(vpc_id=vpc_id, refresh=refresh)
            self.existing_subnets = len(subnets) > 0
        with self.context.spinner('search for existing file systems ...'):
            file_systems = self.context.get_aws_resources().get_file_systems(vpc_id=vpc_id, refresh=refresh)
            self.existing_file_systems = len(file_systems) > 0
        with self.context.spinner('search for existing directories ...'):
            directories = self.context.get_aws_resources().get_directories(vpc_id=vpc_id, refresh=refresh)
            directory_service_provider = self.args.get('directory_service_provider')
            self.existing_directories = len(directories) > 0 and directory_service_provider == constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY

        choices = []
        if self.existing_subnets:
            if alb_public:
                choices.append(SocaUserInputChoice(
                    title='Subnets: Public',
                    value='subnets:public'
                ))
            choices.append(SocaUserInputChoice(
                title='Subnets: Private',
                value='subnets:private'
            ))
        if self.existing_file_systems:
            choices.append(SocaUserInputChoice(
                title='Shared Storage: Internal',
                value='shared-storage:internal'
            ))
            choices.append(SocaUserInputChoice(
                title='Shared Storage: Home',
                value='shared-storage:home'
            ))
        if self.existing_directories:
            choices.append(SocaUserInputChoice(
                title='Directory: AWS Managed Microsoft AD',
                value='directoryservice:aws_managed_activedirectory'
            ))
        return choices


class SubnetIdsPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory', param: SocaUserInputParamMetadata):
        super().__init__(factory=factory,
                         param=param)

    def validate(self, value: List[str]):

        vpc_id = self.args.get('vpc_id')
        if Utils.is_empty(vpc_id):
            raise exceptions.general_exception('vpc_id is required to find existing resources')
        subnets = self.context.get_aws_resources().get_subnets(vpc_id=vpc_id)
        selected_subnets = []
        for subnet in subnets:
            if subnet.subnet_id in value:
                selected_subnets.append(subnet)

        if self.param.name == 'private_subnet_ids':
            subnet_ids_alt = self.args.get('public_subnet_ids')
            subnet_ids_alt_title = 'public subnets'
        else:
            subnet_ids_alt = self.args.get('private_subnet_ids')
            subnet_ids_alt_title = 'private subnets'

        selected_azs = []
        for subnet in selected_subnets:
            if subnet.availability_zone in selected_azs:
                raise self.validation_error(
                    message='Multiple subnet selection from the same Availability Zone is not supported.'
                )
            selected_azs.append(subnet.availability_zone)

            if Utils.is_not_empty(subnet_ids_alt):
                if subnet.subnet_id in subnet_ids_alt:
                    raise self.validation_error(
                        message=f'SubnetId: {subnet.subnet_id} is already selected as part of {subnet_ids_alt_title} selection.'
                    )

        if self.param.name == 'private_subnet_ids' and len(selected_subnets) < 2:
            raise self.validation_error(
                message='Minimum 2 subnet selections are required to ensure high availability.'
            )

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:

        vpc_id = self.args.get('vpc_id')
        if Utils.is_empty(vpc_id):
            raise exceptions.general_exception('vpc_id is required to find existing resources')

        subnets = self.context.get_aws_resources().get_subnets(vpc_id=vpc_id, refresh=refresh)

        if len(subnets) == 0:
            raise exceptions.general_exception(f'Unable to find any existing subnets for vpc: {vpc_id}')

        choices = []

        for subnet in subnets:
            choices.append(SocaUserInputChoice(
                title=subnet.title,
                value=subnet.subnet_id
            ))

        return choices


class FileSystemIdPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory', param: SocaUserInputParamMetadata, storage_provider_key: str, existing_storage_flag_key: Optional[str] = None):
        super().__init__(factory=factory,
                         param=param)
        self.existing_storage_flag_key = existing_storage_flag_key
        self.storage_provider_key = storage_provider_key

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:

        vpc_id = self.args.get('vpc_id')
        if Utils.is_empty(vpc_id):
            raise exceptions.general_exception('vpc_id is required to find existing resources')

        with self.context.spinner(f'checking available file systems in Vpc: {vpc_id} ...'):
            file_systems = self.context.get_aws_resources().get_file_systems(vpc_id=vpc_id, refresh=refresh)

        storage_provider = self.args.get(self.storage_provider_key)
        if Utils.is_empty(storage_provider):
            raise exceptions.general_exception(f'{self.storage_provider_key} is required to find existing file systems')

        filtered_file_systems = []
        for file_system in file_systems:
            if file_system.provider == storage_provider:
                filtered_file_systems.append(file_system)

        if len(filtered_file_systems) == 0:
            raise exceptions.soca_exception(
                error_code=errorcodes.USER_INPUT_FLOW_INTERRUPT,
                message=f'Unable to find any existing file systems for provider: {storage_provider}'
            )

        choices = []

        for file_system in filtered_file_systems:
            choices.append(SocaUserInputChoice(
                title=file_system.title,
                value=file_system.file_system_id
            ))

        return choices

    def filter(self, value) -> Optional[T]:
        if self.existing_storage_flag_key is not None:
            self.args.set(self.existing_storage_flag_key, True)
        return super().filter(value)


class SharedStorageVirtualMachineIdPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory', param: SocaUserInputParamMetadata, file_system_id_key: str):
        super().__init__(factory=factory,
                         param=param)
        self.file_system_id_key = file_system_id_key

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:

        vpc_id = self.args.get('vpc_id')
        if Utils.is_empty(vpc_id):
            raise exceptions.general_exception('vpc_id is required to find existing resources')

        file_system_id = self.args.get(self.file_system_id_key)
        if Utils.is_empty(file_system_id):
            raise exceptions.general_exception('file_system_id is required to find storage virtual machines')

        file_systems = self.context.get_aws_resources().get_file_systems(vpc_id=vpc_id, refresh=refresh)

        target_file_system = None

        for file_system in file_systems:
            if file_system.file_system_id == file_system_id:
                target_file_system = file_system
                break

        if target_file_system is None:
            raise exceptions.general_exception(f'Unable to find any existing file systems for file_system_id: {file_system_id}')

        choices = []

        storage_virtual_machines = target_file_system.get_storage_virtual_machines()
        for svm_entry in storage_virtual_machines:
            svm_id = target_file_system.get_svm_id(svm_entry)
            title = target_file_system.get_storage_virtual_machine_title(svm_entry)
            choices.append(SocaUserInputChoice(
                title=title,
                value=svm_id
            ))

        return choices


class SharedStorageVolumeIdPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory', param: SocaUserInputParamMetadata, file_system_id_key: str, svm_id_key: str = None):
        super().__init__(factory=factory,
                         param=param)
        self.file_system_id_key = file_system_id_key
        self.svm_id_key = svm_id_key

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:

        vpc_id = self.args.get('vpc_id')
        if Utils.is_empty(vpc_id):
            raise exceptions.general_exception('vpc_id is required to find existing resources')

        file_system_id = self.args.get(self.file_system_id_key)
        if Utils.is_empty(file_system_id):
            raise exceptions.general_exception('file_system_id is required to find storage volumes')

        svm_id = None
        if Utils.is_not_empty(self.svm_id_key):
            svm_id = self.args.get(self.svm_id_key)
            if Utils.is_empty(svm_id):
                raise exceptions.general_exception('svm_id is required to find storage volumes')

        file_systems = self.context.get_aws_resources().get_file_systems(vpc_id=vpc_id, refresh=refresh)

        target_file_system = None

        for file_system in file_systems:
            if file_system.file_system_id == file_system_id:
                target_file_system = file_system
                break

        if target_file_system is None:
            raise exceptions.general_exception(f'Unable to find any existing file systems for file_system_id: {file_system_id}')

        choices = []

        volumes = target_file_system.get_volumes()
        for volume_entry in volumes:
            volume_id = target_file_system.get_volume_id(volume_entry)
            title = target_file_system.get_volume_title(volume_entry)
            if Utils.is_not_empty(svm_id):
                volume_svm_id = target_file_system.get_volume_svm_id(volume_entry)
                if Utils.is_empty(volume_svm_id):
                    continue
                if volume_svm_id != svm_id:
                    continue
            choices.append(SocaUserInputChoice(
                title=title,
                value=volume_id
            ))

        return choices

class DirectoryServiceIdPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('directory_id'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:

        vpc_id = self.args.get('vpc_id')
        if Utils.is_empty(vpc_id):
            raise exceptions.general_exception('vpc_id is required to find existing resources')

        directories = self.context.get_aws_resources().get_directories(vpc_id=vpc_id, refresh=refresh)

        if len(directories) == 0:
            raise exceptions.general_exception('Unable to find any existing directories')

        choices = []

        for directory in directories:
            choices.append(SocaUserInputChoice(
                title=directory.title,
                value=directory.directory_id
            ))

        return choices

    def filter(self, value) -> Optional[T]:
        self.args.set('use_existing_directory_service', True)
        return super().filter(value)


class PrefixListIdPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('prefix_list_ids'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        prefix_lists = self.context.get_aws_resources().get_ec2_prefix_lists(refresh)

        choices = []

        for prefix_list in prefix_lists:
            choices.append(SocaUserInputChoice(
                title=prefix_list.title,
                value=prefix_list.prefix_list_id
            ))

        return choices

    def filter(self, value: str) -> Optional[List[str]]:
        tokens = value.split(',')
        result = []
        for token in tokens:
            if Utils.is_empty(token):
                continue
            result.append(token.strip())
        return super().filter(result)


class EnabledModulesPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('enabled_modules'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        result = [
            SocaUserInputChoice(
                title='Global Settings (required)',
                value=constants.MODULE_GLOBAL_SETTINGS,
                checked=True,
                disabled=True
            ),
            SocaUserInputChoice(
                title='Cluster (required)',
                value=constants.MODULE_CLUSTER,
                checked=True,
                disabled=True
            ),
            SocaUserInputChoice(
                title='Identity Provider (required)',
                value=constants.MODULE_IDENTITY_PROVIDER,
                checked=True,
                disabled=True
            ),
            SocaUserInputChoice(
                title='Directory Service (required)',
                value=constants.MODULE_DIRECTORYSERVICE,
                checked=True,
                disabled=True
            ),
            SocaUserInputChoice(
                title='Shared Storage (required)',
                value=constants.MODULE_SHARED_STORAGE,
                checked=True,
                disabled=True
            ),
            SocaUserInputChoice(
                title='Cluster Manager (required)',
                value=constants.MODULE_CLUSTER_MANAGER,
                checked=True,
                disabled=True
            ),
            SocaUserInputChoice(
                title='Enterprise Virtual Desktop Infrastructure (eVDI)',
                value=constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER
            ),
            SocaUserInputChoice(
                title='Bastion Host',
                value=constants.MODULE_BASTION_HOST
            )
        ]
        return result


class MetricsProviderPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('metrics_provider'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        aws_region = self.args.get('aws_region')
        if Utils.is_empty(aws_region):
            raise exceptions.general_exception('aws_region is required to identify available metrics providers.')

        aws_profile = self.args.get('aws_profile')
        aws_secondary_profile = self.args.get('aws_profile2')

        profile_string = f" {aws_profile}"
        if aws_secondary_profile:
            profile_string = f"s (primary:  {aws_profile}, secondary: {aws_secondary_profile})"

        with self.context.spinner(f'checking available services in region: {aws_region} using AWS Profile{profile_string} ...'):
            availability_helper = AwsServiceAvailabilityHelper(aws_region=aws_region, aws_profile=aws_profile, aws_secondary_profile=aws_secondary_profile)
            available_services = availability_helper.get_available_services(aws_region)

        result = [
            SocaUserInputChoice(
                title='AWS CloudWatch',
                value=constants.METRICS_PROVIDER_CLOUDWATCH,
                disabled='cloudwatch' not in available_services
            ),
            SocaUserInputChoice(
                title='Amazon Managed Service for Prometheus',
                value=constants.METRICS_PROVIDER_AMAZON_MANAGED_PROMETHEUS,
                disabled='aps' not in available_services
            ),
            SocaUserInputChoice(
                title='Custom Prometheus Server',
                value=constants.METRICS_PROVIDER_PROMETHEUS
            )
        ]

        return result


class SharedStorageNamePrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('shared_storage_name'))

    def validate(self, value: str):
        is_upgrade = Utils.get_as_bool(self.args.get('_upgrade'), default=False)
        if is_upgrade:
            existing_config = self.context.config().get_config(f'shared-storage.{value}', default=None)
            if existing_config is not None:
                raise self.validation_error(f'A file system named: {value} already exists in shared storage settings')

        super().validate(value)


class SharedStorageProviderPrompt(DefaultPrompt[str]):

    def __init__(self, factory: 'InstallerPromptFactory'):
        super().__init__(factory=factory,
                         param=factory.args.get_meta('shared_storage_provider'))

    def get_choices(self, refresh: bool = False) -> List[SocaUserInputChoice]:
        use_existing_fs = Utils.get_as_bool(self.args.get('use_existing_fs'), False)

        if use_existing_fs:

            vpc_id = self.args.get('vpc_id')
            if Utils.is_empty(vpc_id):
                raise exceptions.general_exception('vpc_id is required to find existing resources')

            with self.context.spinner(f'checking available file systems in Vpc: {vpc_id} ...'):
                file_systems = self.context.get_aws_resources().get_file_systems(vpc_id=vpc_id, refresh=refresh)

            if len(file_systems) == 0:
                raise exceptions.soca_exception(
                    error_code=errorcodes.USER_INPUT_FLOW_INTERRUPT,
                    message=f'Unable to find any existing file systems in VPC: {vpc_id}'
                )

            providers = set()
            for file_system in file_systems:
                providers.add(file_system.provider)

            return [
                SocaUserInputChoice(
                    title='Amazon EFS',
                    value=constants.STORAGE_PROVIDER_EFS,
                    disabled=constants.STORAGE_PROVIDER_EFS not in providers
                ),
                SocaUserInputChoice(
                    title='Amazon File Cache',
                    value=constants.STORAGE_PROVIDER_FSX_CACHE,
                    disabled=constants.STORAGE_PROVIDER_FSX_CACHE not in providers
                ),
                SocaUserInputChoice(
                    title='Amazon FSx for Lustre',
                    value=constants.STORAGE_PROVIDER_FSX_LUSTRE,
                    disabled=constants.STORAGE_PROVIDER_FSX_LUSTRE not in providers
                ),
                SocaUserInputChoice(
                    title='Amazon FSx for NetApp ONTAP',
                    value=constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
                    disabled=constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP not in providers
                ),
                SocaUserInputChoice(
                    title='Amazon FSx for OpenZFS',
                    value=constants.STORAGE_PROVIDER_FSX_OPENZFS,
                    disabled=constants.STORAGE_PROVIDER_FSX_OPENZFS not in providers
                ),
                SocaUserInputChoice(
                    title='Amazon FSx for Windows File Server',
                    value=constants.STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER,
                    disabled=constants.STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER not in providers
                )
            ]

        else:

            return [
                SocaUserInputChoice(
                    title='Amazon EFS',
                    value=constants.STORAGE_PROVIDER_EFS
                )
            ]


class InstallerPromptFactory:
    """
    Base class for prompt initialization
    """

    def __init__(self, context: SocaCliContext,
                 param_registry: SocaUserInputParamRegistry,
                 args: SocaUserInputArgs):

        self.context = context
        self.args = args
        self.param_registry = param_registry

        self._install_prompts = SocaPromptRegistry(
            context=self.context,
            param_spec=self.param_registry
        )

    @property
    def install_prompts(self) -> SocaPromptRegistry:
        return self._install_prompts

    def register(self, prompt: SocaPrompt):
        self.install_prompts.add(prompt)

    def initialize_prompts(self, user_input_module: str):
        params = self.param_registry.get_params(module=user_input_module)
        for param_meta in params:
            self.build_prompt(param_meta)

    def build_prompt(self, param_meta: SocaUserInputParamMetadata):
        prompt = None
        try:
            prompt = self.install_prompts.get(param_meta.name)
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.INPUT_PROMPT_NOT_FOUND:
                pass
            else:
                raise e

        if prompt is None:
            prompt = DefaultPrompt(
                factory=self,
                param=param_meta
            )
        return prompt

    def build_section(self, module: str, section: str) -> SocaUserInputSection:

        section_meta = self.param_registry.get_section(module, section)
        section_params = self.param_registry.get_params(module, section)
        section_prompts = []

        for param_meta in section_params:

            if section == 'aws-account' and ideaadministrator.props.use_ec2_instance_metadata_credentials():
                # if administrator app is running inside EC2 Instance with InstanceMetadata credentials,
                # skip profile selection prompt
                if param_meta.name == 'aws_profile':
                    continue

            prompt = self.install_prompts.get(param_meta.name)
            prompt.param = param_meta
            section_prompts.append(prompt)

        return SocaUserInputSection(
            context=self.context,
            section=section_meta,
            prompts=section_prompts
        )

    @staticmethod
    def section_callback(context: ideaadministrator.Context, section: SocaUserInputSection, factory: 'InstallerPromptFactory') -> bool:
        """
        the section call back is called by SocaUserInputModule after each section is completed.

        upon completion of the aws "aws-account" section, we re-initialize the aws clients and dependencies,
        so that additional API calls to AWS will use the updated profile and region.

        :param context:
        :param section:
        :param factory:
        :return:
        """

        if section.name == 'aws-account':

            aws_region = factory.args.get('aws_region')

            if ideaadministrator.props.use_ec2_instance_metadata_credentials():
                factory.args.set('aws_profile', None)
                context.aws_init(aws_profile=None, aws_region=aws_region)
            else:
                aws_profile = factory.args.get('aws_profile')
                context.aws_init(aws_profile=aws_profile, aws_region=aws_region)

            factory.args.set('aws_partition', context.aws().aws_partition())
            factory.args.set('aws_account_id', context.aws().aws_account_id())
            factory.args.set('aws_dns_suffix', context.aws().aws_dns_suffix())

        return True

    def build_module(self, user_input_module: str, start_section: int = None, display_info: bool = True, display_steps: bool = True) -> SocaUserInputModule:

        self.initialize_prompts(user_input_module)

        module_meta = self.param_registry.get_module(user_input_module)

        sections = []
        if Utils.is_not_empty(module_meta.sections):
            for section_meta in module_meta.sections:
                section = self.build_section(user_input_module, section_meta.name)
                sections.append(section)

        return SocaUserInputModule(
            context=self.context,
            module=module_meta,
            section_callback=self.section_callback,
            section_callback_kwargs={
                'factory': self
            },
            sections=sections,
            restart_errorcodes=[errorcodes.INSTALLER_MISSING_PERMISSIONS],
            display_info=display_info,
            display_steps=display_steps,
            start_section=start_section
        )


class QuickSetupPromptFactory(InstallerPromptFactory):
    """
    Initialize Prompts for Quick Setup Installation Flows
    """

    def __init__(self, context: SocaCliContext,
                 param_registry: SocaUserInputParamRegistry,
                 args: SocaUserInputArgs):
        super().__init__(context, param_registry, args)

    def initialize_prompts(self, user_input_module: str):
        self.initialize_overrides()
        super().initialize_prompts(user_input_module)

    def initialize_overrides(self):
        self.register(ClusterNamePrompt(factory=self))
        self.register(EmailPrompt(factory=self, param=self.args.get_meta('administrator_email')))
        self.register(AwsProfilePrompt(factory=self))
        self.register(AwsPartitionPrompt(factory=self))
        self.register(AwsRegionPrompt(factory=self))
        self.register(ClientIPPrompt(factory=self))
        self.register(PrefixListIdPrompt(factory=self))
        self.register(SSHKeyPairPrompt(factory=self, param=self.args.get_meta('ssh_key_pair_name')))
        self.register(EnabledModulesPrompt(factory=self))
        self.register(MetricsProviderPrompt(factory=self))
        self.register(VpcCidrBlockPrompt(factory=self))
        self.register(VpcIdPrompt(factory=self))
        self.register(ExistingResourcesPrompt(factory=self))
        self.register(SubnetIdsPrompt(factory=self, param=self.args.get_meta('private_subnet_ids')))
        self.register(SubnetIdsPrompt(factory=self, param=self.args.get_meta('public_subnet_ids')))
        self.register(FileSystemIdPrompt(
            factory=self,
            param=self.args.get_meta('existing_internal_fs_id'),
            existing_storage_flag_key='use_existing_internal_fs',
            storage_provider_key='storage_internal_provider'
        ))
        self.register(FileSystemIdPrompt(
            factory=self,
            param=self.args.get_meta('existing_home_fs_id'),
            existing_storage_flag_key='use_existing_home_fs',
            storage_provider_key='storage_home_provider'
        ))
        self.register(DirectoryServiceIdPrompt(factory=self))


class SharedStoragePromptFactory(InstallerPromptFactory):
    """
    Initialize Prompts for Shared Storage Configuration
    """

    def __init__(self, context: SocaCliContext,
                 param_registry: SocaUserInputParamRegistry,
                 args: SocaUserInputArgs):
        super().__init__(context, param_registry, args)

    def initialize_prompts(self, user_input_module: str):
        self.initialize_overrides()
        super().initialize_prompts(user_input_module)

    def initialize_overrides(self):
        self.register(VpcIdPrompt(factory=self))
        self.register(SharedStorageNamePrompt(factory=self))
        self.register(SharedStorageProviderPrompt(factory=self))

        # efs
        self.register(FileSystemIdPrompt(
            factory=self,
            param=self.args.get_meta('efs.file_system_id'),
            storage_provider_key='shared_storage_provider'
        ))

        # Amazon File Cache
        self.register(FileSystemIdPrompt(
            factory=self,
            param=self.args.get_meta('fsx_cache.file_system_id'),
            storage_provider_key='shared_storage_provider'
        ))

        # lustre
        self.register(FileSystemIdPrompt(
            factory=self,
            param=self.args.get_meta('fsx_lustre.file_system_id'),
            storage_provider_key='shared_storage_provider'
        ))

        # ontap
        self.register(FileSystemIdPrompt(
            factory=self,
            param=self.args.get_meta('fsx_netapp_ontap.file_system_id'),
            storage_provider_key='shared_storage_provider'
        ))
        self.register(SharedStorageVirtualMachineIdPrompt(
            factory=self,
            param=self.args.get_meta('fsx_netapp_ontap.svm_id'),
            file_system_id_key='fsx_netapp_ontap.file_system_id'
        ))
        self.register(SharedStorageVolumeIdPrompt(
            factory=self,
            param=self.args.get_meta('fsx_netapp_ontap.volume_id'),
            file_system_id_key='fsx_netapp_ontap.file_system_id',
            svm_id_key='fsx_netapp_ontap.svm_id'
        ))

        # openzfs
        self.register(FileSystemIdPrompt(
            factory=self,
            param=self.args.get_meta('fsx_openzfs.file_system_id'),
            storage_provider_key='shared_storage_provider'
        ))
        self.register(SharedStorageVolumeIdPrompt(
            factory=self,
            param=self.args.get_meta('fsx_openzfs.volume_id'),
            file_system_id_key='fsx_openzfs.file_system_id'
        ))

        # Windows file server
        self.register(FileSystemIdPrompt(
            factory=self,
            param=self.args.get_meta('fsx_windows_file_server.file_system_id'),
            storage_provider_key='shared_storage_provider'
        ))
