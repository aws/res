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
import botocore.exceptions

from ideasdk.protocols import SocaContextProtocol
from ideadatamodel.cluster_resources import (
    SocaVPC,
    SocaCloudFormationStack,
    SocaDirectory,
    SocaSubnet,
    SocaFileSystem,
    SocaSecurityGroup,
    SocaIAMRole,
    SocaS3Bucket,
    SocaSSHKeyPair,
    SocaACMCertificate,
    SocaAWSProfile,
    SocaEC2PrefixList
)

from ideasdk.utils import Utils
from ideadatamodel import errorcodes, exceptions, constants
from ideasdk.shell import ShellInvoker
from ideasdk.aws import AWSUtil, AwsClientProvider

from cacheout import Cache
from typing import Optional, List, Dict
import time


class AwsResourcesInMemoryDB:

    def __init__(self, context: SocaContextProtocol):
        self._context = context
        self._db = Cache(maxsize=10000, ttl=0)

    def clear(self):
        for key in self._db.keys():
            if key == 'aws.cli.profiles':
                continue
            self._db.delete(key)

    def get_vpcs(self) -> Optional[List[SocaVPC]]:
        return self._db.get('aws.ec2.vpcs')

    def set_vpcs(self, vpcs: List[SocaVPC]):
        return self._db.set('aws.ec2.vpcs', vpcs)

    def get_subnets(self) -> Optional[List[SocaSubnet]]:
        return self._db.get('aws.ec2.subnets')

    def set_subnets(self, subnets: List[SocaSubnet]):
        return self._db.set('aws.ec2.subnets', subnets)

    def get_directories(self) -> Optional[List[SocaDirectory]]:
        return self._db.get('aws.directories')

    def set_directories(self, directories: List[SocaDirectory]):
        return self._db.set('aws.directories', directories)

    def get_file_systems(self) -> Optional[List[SocaFileSystem]]:
        return self._db.get('aws.file-system')

    def set_file_systems(self, file_systems: List[SocaFileSystem]):
        return self._db.set('aws.file-system', file_systems)

    def get_security_groups(self) -> Optional[List[SocaSecurityGroup]]:
        return self._db.get('aws.ec2.security-groups')

    def set_security_groups(self, security_groups: List[SocaSecurityGroup]):
        return self._db.set('aws.ec2.security-groups', security_groups)

    def get_iam_roles(self) -> Optional[List[SocaIAMRole]]:
        return self._db.get('aws.iam.roles')

    def set_iam_roles(self, iam_roles: List[SocaIAMRole]):
        return self._db.set('aws.iam.roles', iam_roles)

    def get_s3_buckets(self) -> Optional[List[SocaS3Bucket]]:
        return self._db.get('aws.s3.buckets')

    def set_s3_buckets(self, s3_buckets: List[SocaS3Bucket]):
        return self._db.set('aws.s3.buckets', s3_buckets)

    def get_ssh_key_pairs(self) -> Optional[List[SocaSSHKeyPair]]:
        return self._db.get('aws.ec2.ssh_key_pairs')

    def set_ssh_key_pairs(self, ssh_key_pairs: List[SocaSSHKeyPair]):
        return self._db.set('aws.ec2.ssh_key_pairs', ssh_key_pairs)

    def get_cloudformation_stacks(self) -> Optional[List[SocaCloudFormationStack]]:
        return self._db.get('aws.cloudformation.stacks')

    def set_cloudformation_stacks(self, cloudformation_stacks: List[SocaCloudFormationStack]):
        return self._db.set('aws.cloudformation.stacks', cloudformation_stacks)

    def get_acm_certificates(self) -> Optional[List[SocaACMCertificate]]:
        return self._db.get('aws.acm.certificates')

    def set_acm_certificates(self, acm_certificates: List[SocaACMCertificate]):
        return self._db.set('aws.acm.certificates', acm_certificates)

    def get_aws_profiles(self) -> Optional[List[SocaAWSProfile]]:
        return self._db.get('aws.cli.profiles')

    def set_aws_profiles(self, aws_profiles: List[SocaAWSProfile]):
        return self._db.set('aws.cli.profiles', aws_profiles)

    def get_ec2_prefix_lists(self) -> Optional[List[SocaEC2PrefixList]]:
        return self._db.get('aws.ec2.prefix_lists')

    def set_ec2_prefix_lists(self, ec2_prefix_lists: List[SocaEC2PrefixList]):
        return self._db.set('aws.ec2.prefix_lists', ec2_prefix_lists)


class AwsResources:
    def __init__(self, context: SocaContextProtocol, aws: AwsClientProvider = None, aws_util: AWSUtil = None):
        self._context = context
        self._shell = ShellInvoker()
        self._db = AwsResourcesInMemoryDB(self._context)
        self._aws = aws
        self._aws_util = aws_util

    def reset(self):
        self._db.clear()

    @property
    def aws(self) -> AwsClientProvider:
        return self._aws

    @property
    def aws_util(self) -> AWSUtil:
        return self._aws_util

    @staticmethod
    def _get_tag_value(key: str, tags: List[Dict]) -> Optional[str]:
        if tags is None:
            return None
        for tag in tags:
            tag_key = Utils.get_value_as_string('Key', tag)
            if tag_key == key:
                return Utils.get_value_as_string('Value', tag)
        return None

    def is_any_soca_cluster_installed(self) -> bool:
        stacks = self.get_cloudformation_stacks()
        for stack in stacks:
            if not stack.is_cluster():
                continue
            if stack.status != 'CREATE_COMPLETE':
                continue
            cluster_name = stack.cluster_name
            if Utils.is_empty(cluster_name):
                continue
            return True
        return False

    def list_available_cluster_names(self) -> List[str]:
        stacks = self.get_cloudformation_stacks()
        result = set()
        for stack in stacks:
            if not stack.is_cluster():
                continue
            cluster_name = stack.cluster_name
            if Utils.is_empty(cluster_name):
                continue
            result.add(cluster_name)
        return list(result)

    def get_vpcs(self, refresh: bool = False) -> List[SocaVPC]:
        try:
            if not refresh:
                vpcs = self._db.get_vpcs()
                if vpcs is not None:
                    return vpcs

            def result_cb(result) -> List[SocaVPC]:
                results = []
                listing = Utils.get_value_as_list('Vpcs', result, [])
                for entry in listing:
                    tags = Utils.get_value_as_list('Tags', entry, [])
                    vpc_id = Utils.get_value_as_string('VpcId', entry)
                    cidr_block = Utils.get_value_as_string('CidrBlock', entry)
                    title = f'{vpc_id} ({cidr_block})'
                    if tags is not None:
                        name = self._get_tag_value('Name', tags)
                        if Utils.is_not_empty(name):
                            title = f'{title} [{name}]'
                    results.append(SocaVPC(
                        type='aws.ec2.vpc',
                        title=title,
                        ref=entry
                    ))
                return results

            vpcs = self.aws_util.invoke_aws_listing(
                fn=self.aws.ec2().describe_vpcs,
                result_cb=result_cb
            )
            self._db.set_vpcs(vpcs)
            return vpcs
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_directories(self, vpc_id: str, refresh: bool = False) -> List[SocaDirectory]:
        try:
            if not refresh:
                directories = self._db.get_directories()
                if directories is not None:
                    return directories

            def result_cb(result) -> List[SocaDirectory]:
                results = []
                listing = Utils.get_value_as_list('DirectoryDescriptions', result, [])
                for entry in listing:
                    directory_type = Utils.get_value_as_string('Type', entry)
                    if directory_type != 'MicrosoftAD':
                        continue
                    vpc_settings = Utils.get_value_as_dict('VpcSettings', entry, {})
                    ds_vpc_id = Utils.get_value_as_string('VpcId', vpc_settings)
                    if ds_vpc_id != vpc_id:
                        continue
                    directory_id = Utils.get_value_as_string('DirectoryId', entry)
                    ds_subnets = Utils.get_value_as_list('SubnetIds', vpc_settings, [])
                    ds_name = Utils.get_value_as_string('Name', entry)
                    title = f'{ds_name} (DirectoryId: {directory_id}, SubnetIds: {", ".join(ds_subnets)})'
                    results.append(SocaDirectory(
                        type='aws.directory',
                        title=title,
                        ref=entry
                    ))
                return results

            directories = self.aws_util.invoke_aws_listing(
                fn=self.aws.ds().describe_directories,
                result_cb=result_cb
            )
            self._db.set_directories(directories)
            return directories
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_subnets(self, vpc_id: str, refresh: bool = False) -> List[SocaSubnet]:
        try:
            if not refresh:
                subnets = self._db.get_subnets()
                if subnets is not None:
                    return subnets

            def result_cb(result) -> List[SocaSubnet]:
                results = []
                listing = Utils.get_value_as_list('Subnets', result, [])
                for entry in listing:
                    tags = Utils.get_value_as_list('Tags', entry)
                    title = self._get_tag_value('Name', tags)
                    subnet_id = entry['SubnetId']
                    availability_zone = entry['AvailabilityZone']
                    availability_zone_id = entry['AvailabilityZoneId']
                    # CidrBlock is only present on IPv4-enable subnets (not on IPv6-only subnets)
                    cidr_block = entry['CidrBlock']
                    suffix = f'(SubnetId: {subnet_id}, CIDR Block: {cidr_block}, AZ/AZID: {availability_zone}/{availability_zone_id})'
                    if Utils.is_not_empty(title):
                        title = f'{title} {suffix}'
                    else:
                        title = suffix
                    results.append(SocaSubnet(
                        type='aws.ec2.subnet',
                        title=title,
                        ref=entry
                    ))
                return results

            subnets = self.aws_util.invoke_aws_listing(
                fn=self.aws.ec2().describe_subnets,
                fn_kwargs={
                    'Filters': [
                        {
                            'Name': 'vpc-id',
                            'Values': [vpc_id]
                        },
                        {
                            'Name': 'ipv6-native',
                            'Values': ['false']
                        }
                    ]
                },
                result_cb=result_cb
            )
            subnets.sort(key=lambda s: s.sort_order)
            self._db.set_subnets(subnets)
            return subnets
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_file_systems(self, vpc_id: str, refresh: bool = False) -> List[SocaFileSystem]:
        try:
            if not refresh:
                file_systems = self._db.get_file_systems()
                if file_systems is not None:
                    return file_systems

            def result_cb(result, fs_type: str) -> List[SocaFileSystem]:
                results = []
                # Amazon File Cache uses slightly different structures
                if fs_type == constants.STORAGE_PROVIDER_FSX_CACHE:
                    listing_key = 'FileCaches'
                    fsid_key = 'FileCacheId'
                else:
                    listing_key = 'FileSystems'
                    fsid_key = 'FileSystemId'

                allowed_lifecycle_values = ['available', 'updating']

                if fs_type == constants.STORAGE_PROVIDER_EFS:
                    lifecycle_key = 'LifeCycleState'
                else:
                    # FSx / File Cache
                    lifecycle_key = 'Lifecycle'

                listing = Utils.get_value_as_list(listing_key, result, [])
                for entry in listing:
                    # We only work on file systems that are in a healthy state
                    # normalized to .lower() for case insensitive comparison
                    if Utils.get_value_as_string(lifecycle_key, entry, default='error').lower() not in allowed_lifecycle_values:
                        continue
                    file_system_id = Utils.get_value_as_string(fsid_key, entry)
                    storage_virtual_machines = None
                    volumes = None

                    if fs_type == 'efs':
                        file_system_provider = constants.STORAGE_PROVIDER_EFS
                    elif fs_type == 'fsx_cache':
                        file_system_provider = constants.STORAGE_PROVIDER_FSX_CACHE
                        # Perform some checks - only supporting Lustre-based file caches for now
                        file_cache_type = Utils.get_value_as_string('FileCacheType', entry, default='unknown')
                        if file_cache_type != 'LUSTRE':
                            continue

                        lustre_configuration = Utils.get_value_as_dict('LustreConfiguration', entry, {})
                        if Utils.is_empty(lustre_configuration):
                            continue

                        file_cache_deployment_type = Utils.get_value_as_string('DeploymentType', lustre_configuration, default='unknown')
                        if file_cache_deployment_type != 'CACHE_1':
                            continue

                    else:
                        file_system_type = Utils.get_value_as_string('FileSystemType', entry)
                        if file_system_type == 'ONTAP':
                            file_system_provider = constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP
                        elif file_system_type == 'OPENZFS':
                            file_system_provider = constants.STORAGE_PROVIDER_FSX_OPENZFS
                        elif file_system_type == 'LUSTRE':
                            file_system_provider = constants.STORAGE_PROVIDER_FSX_LUSTRE
                        elif file_system_type == 'WINDOWS':
                            file_system_provider = constants.STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER
                        else:
                            continue

                    # File Cache doesn't return Tags in the describe_file_caches
                    if fs_type == 'fsx_cache':
                        try:
                            resource_arn = Utils.get_value_as_string('ResourceARN', entry)
                            tags = self.aws.fsx().list_tags_for_resource(ResourceARN=resource_arn)['Tags']
                        except Exception as e:
                            raise e
                    else:
                        tags = Utils.get_value_as_list('Tags', entry)

                    title = self._get_tag_value('Name', tags)
                    if Utils.is_not_empty(title):
                        title = f'{title} ({fsid_key}: {file_system_id}, Provider: {file_system_provider})'
                    else:
                        title = f'{fsid_key}: {file_system_id}, Provider: {file_system_provider}'

                    if fs_type == 'efs':
                        mount_targets_result = self.aws.efs().describe_mount_targets(FileSystemId=file_system_id)
                        # Rapid invocation of describe_mount_targets can cause RateExceeded on the account
                        time.sleep(.100)
                        mount_targets = Utils.get_value_as_list('MountTargets', mount_targets_result, [])

                        vpc_found = False
                        for mount_target in mount_targets:
                            if mount_target['VpcId'] == vpc_id:
                                vpc_found = True
                                break

                        if not vpc_found:
                            continue

                    elif fs_type == 'fsx_cache':
                        if 'VpcId' not in entry:
                            continue
                        if entry['VpcId'] != vpc_id:
                            continue

                    elif fs_type == 'fsx':

                        if 'VpcId' not in entry:
                            continue
                        if entry['VpcId'] != vpc_id:
                            continue

                        if file_system_provider in (
                            constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
                            constants.STORAGE_PROVIDER_FSX_OPENZFS
                        ):
                            describe_volumes_result = self.aws.fsx().describe_volumes(
                                Filters=[
                                    {
                                        'Name': 'file-system-id',
                                        'Values': [file_system_id]
                                    }
                                ]
                            )
                            volumes = Utils.get_value_as_list('Volumes', describe_volumes_result, [])

                        if file_system_provider == constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP:
                            describe_svm_result = self.aws.fsx().describe_storage_virtual_machines(
                                Filters=[
                                    {
                                        'Name': 'file-system-id',
                                        'Values': [file_system_id]
                                    }
                                ]
                            )
                            storage_virtual_machines = Utils.get_value_as_list('StorageVirtualMachines', describe_svm_result, [])

                    else:
                        continue

                    results.append(SocaFileSystem(
                        type=f'aws.file-system.{fs_type}',
                        title=title,
                        provider=file_system_provider,
                        ref={
                            'file_system': entry,
                            'storage_virtual_machines': storage_virtual_machines,
                            'volumes': volumes
                        }
                    ))
                return results

            file_systems = []

            efs = self.aws_util.invoke_aws_listing(
                fn=self.aws.efs().describe_file_systems,
                result_cb=result_cb,
                marker_based_paging=True,
                fs_type='efs'
            )
            file_systems += efs

            # Amazon File Cache in a discrete try/except block as it is
            # still undergoing deployment to all regions, and we don't want to
            # maintain a static listing of supported regions.
            try:
                caches = self.aws_util.invoke_aws_listing(
                    fn=self.aws.fsx().describe_file_caches,
                    result_cb=result_cb,
                    fs_type='fsx_cache'
                )
                file_systems += caches
            except botocore.exceptions.ClientError as error:
                if error.response['Error']['Code'] == 'BadRequest':
                    pass
                else:
                    raise error

            fsx = self.aws_util.invoke_aws_listing(
                fn=self.aws.fsx().describe_file_systems,
                result_cb=result_cb,
                fs_type='fsx'
            )
            file_systems += fsx

            self._db.set_file_systems(file_systems)

            return file_systems
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_security_groups(self, refresh: bool = False) -> List[SocaSecurityGroup]:
        try:

            if not refresh:
                security_groups = self._db.get_security_groups()
                if security_groups is not None:
                    return security_groups

            def result_cb(result) -> List[SocaSecurityGroup]:
                results = []
                listing = Utils.get_value_as_list('SecurityGroups', result, [])
                for entry in listing:
                    tags = Utils.get_value_as_list('Tags', entry, [])
                    title = self._get_tag_value('Name', tags)
                    group_id = entry['GroupId']
                    if Utils.is_not_empty(title):
                        title = f'{title} ({group_id})'
                    else:
                        title = group_id

                    results.append(SocaSecurityGroup(
                        type='aws.ec2.security-group',
                        title=title,
                        ref=entry
                    ))
                return results

            security_groups = self.aws_util.invoke_aws_listing(
                fn=self.aws.ec2().describe_security_groups,
                result_cb=result_cb
            )
            self._db.set_security_groups(security_groups)
            return security_groups
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_iam_roles(self, refresh: bool = False) -> List[SocaIAMRole]:
        try:
            if not refresh:
                iam_roles = self._db.get_iam_roles()
                if iam_roles is not None:
                    return iam_roles

            def result_cb(result) -> List[SocaIAMRole]:
                results = []
                listing = Utils.get_value_as_list('Roles', result, [])
                for entry in listing:
                    role_name = Utils.get_value_as_string('RoleName', entry)
                    results.append(SocaIAMRole(
                        type='aws.iam-role',
                        title=role_name,
                        ref=entry
                    ))
                return results

            iam_roles = self.aws_util.invoke_aws_listing(
                fn=self.aws.ec2().list_roles,
                result_cb=result_cb,
                marker_based_paging=True
            )
            self._db.set_iam_roles(iam_roles)
            return iam_roles
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_s3_buckets(self, refresh: bool = False) -> List[SocaS3Bucket]:
        try:

            if not refresh:
                s3_buckets = self._db.get_s3_buckets()
                if s3_buckets is not None:
                    return s3_buckets

            list_buckets_result = self.aws.s3().list_buckets()
            buckets = Utils.get_value_as_list('Buckets', list_buckets_result, [])

            s3_buckets = []
            for bucket in buckets:
                name = Utils.get_value_as_string('Name', bucket)
                s3_buckets.append(SocaS3Bucket(
                    type='s3.bucket',
                    title=f'{name}',
                    ref=bucket
                ))

            self._db.set_s3_buckets(s3_buckets)
            return s3_buckets
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_ec2_key_pairs(self, refresh: bool = False) -> List[SocaSSHKeyPair]:
        try:

            if not refresh:
                ssh_key_pairs = self._db.get_ssh_key_pairs()
                if ssh_key_pairs is not None:
                    return ssh_key_pairs

            key_pairs_result = self.aws.ec2().describe_key_pairs()
            key_pairs = Utils.get_value_as_list('KeyPairs', key_pairs_result, [])

            ssh_key_pairs = []
            for key_pair in key_pairs:
                key_name = Utils.get_value_as_string('KeyName', key_pair)
                ssh_key_pairs.append(SocaSSHKeyPair(
                    type='aws.ec2.key_pair',
                    title=key_name,
                    ref=key_pair
                ))

            self._db.set_ssh_key_pairs(ssh_key_pairs)
            return ssh_key_pairs

        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_cloudformation_stacks(self, refresh: bool = False) -> List[SocaCloudFormationStack]:
        try:

            if not refresh:
                cloudformation_stacks = self._db.get_cloudformation_stacks()
                if cloudformation_stacks is not None:
                    return cloudformation_stacks

            def result_cb(result) -> List[SocaCloudFormationStack]:
                results = []
                listing = Utils.get_value_as_list('Stacks', result, [])
                for entry in listing:
                    stack_name = Utils.get_value_as_string('StackName', entry)
                    results.append(SocaCloudFormationStack(
                        type='aws.cloudformation-stack',
                        title=stack_name,
                        ref=entry
                    ))
                return results

            cloudformation_stacks = self.aws_util.invoke_aws_listing(
                fn=self.aws.cloudformation().describe_stacks,
                result_cb=result_cb,
                marker_based_paging=False
            )
            self._db.set_cloudformation_stacks(cloudformation_stacks)
            return cloudformation_stacks
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_acm_certificates(self, refresh: bool = False) -> List[SocaACMCertificate]:
        try:

            if not refresh:
                acm_certificates = self._db.get_acm_certificates()
                if acm_certificates is not None:
                    return acm_certificates

            def result_cb(result) -> List[SocaACMCertificate]:
                results = []
                listing = Utils.get_value_as_list('CertificateSummaryList', result, [])
                for entry in listing:
                    domain_name = Utils.get_value_as_string('DomainName', entry)
                    results.append(SocaACMCertificate(
                        type='aws.acm.certificate',
                        title=domain_name,
                        ref=entry
                    ))
                return results

            acm_certificates = self.aws_util.invoke_aws_listing(
                fn=self.aws.acm().list_certificates,
                result_cb=result_cb,
                marker_based_paging=False
            )
            self._db.set_acm_certificates(acm_certificates)
            return acm_certificates
        except Exception as e:
            self.aws_util.handle_aws_exception(e)

    def get_aws_profiles(self, refresh: bool = False) -> List[SocaAWSProfile]:

        if not refresh:
            aws_profiles = self._db.get_aws_profiles()
            if aws_profiles is not None:
                return aws_profiles

        result = self._shell.invoke(cmd='aws configure list-profiles', shell=True, skip_error_logging=True)
        if result.returncode != 0:
            error = result.stderr
            if Utils.is_empty(error):
                error = result.stdout
            raise exceptions.soca_exception(error_code=errorcodes.GENERAL_ERROR,
                                            message=error)

        profiles = str(result.stdout).splitlines(keepends=False)
        if len(profiles) == 0:
            raise exceptions.soca_exception(error_code=errorcodes.AWS_CLI_NOT_INSTALLED,
                                            message='AWS CLI is not installed or AWS config not found.')

        aws_profiles = []
        for profile in profiles:
            aws_profiles.append(SocaAWSProfile(
                title=profile,
                ref=profile
            ))

        self._db.set_aws_profiles(aws_profiles)
        return aws_profiles

    def get_ec2_prefix_lists(self, refresh: bool = False) -> List[SocaEC2PrefixList]:
        try:

            if not refresh:
                prefix_lists = self._db.get_ec2_prefix_lists()
                if prefix_lists is not None:
                    return prefix_lists

            def result_cb(result) -> List[SocaEC2PrefixList]:
                results = []
                listing = Utils.get_value_as_list('PrefixLists', result, [])
                for entry in listing:
                    prefix_list_name = Utils.get_value_as_string('PrefixListName', entry)
                    if Utils.is_not_empty(prefix_list_name) and prefix_list_name.startswith('com.amazonaws'):
                        continue
                    prefix_list_id = Utils.get_value_as_string('PrefixListId', entry)
                    results.append(SocaEC2PrefixList(
                        type='aws.ec2.prefix_list',
                        title=f'{prefix_list_name} [{prefix_list_id}]',
                        ref=entry
                    ))
                return results

            prefix_lists = self.aws_util.invoke_aws_listing(
                fn=self.aws.ec2().describe_managed_prefix_lists,
                result_cb=result_cb,
                marker_based_paging=False
            )
            self._db.set_ec2_prefix_lists(prefix_lists)
            return prefix_lists
        except Exception as e:
            self.aws_util.handle_aws_exception(e)
