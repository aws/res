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
    'SocaClusterResource',
    'SocaVPC',
    'SocaCloudFormationStack',
    'SocaOpenSearchDomain',
    'SocaDirectory',
    'SocaSubnet',
    'SocaFileSystem',
    'SocaSecurityGroupPermission',
    'SocaSecurityGroup',
    'SocaIAMRole',
    'SocaS3Bucket',
    'SocaSSHKeyPair',
    'SocaACMCertificate',
    'SocaAWSProfile',
    'SocaEC2PrefixList'
)

from ideadatamodel import SocaBaseModel, constants, exceptions
from ideadatamodel.model_utils import ModelUtils

from typing import Optional, List, Dict, Any, Set


class SocaClusterResource(SocaBaseModel):
    type: Optional[str]
    title: Optional[str]
    props: Optional[Dict]
    ref: Optional[Any]

    def get_tag(self, key: str, ref_key: Optional[str] = None) -> Optional[str]:
        if self.ref is None:
            return None

        if ref_key is None:
            tags = ModelUtils.get_value_as_list('Tags', self.ref)
        else:
            ref = ModelUtils.get_value_as_dict(ref_key, self.ref)
            tags = ModelUtils.get_value_as_list('Tags', ref)

        if tags is None:
            return None

        for tag in tags:
            k = ModelUtils.get_value_as_string('Key', tag)
            if k == key:
                return ModelUtils.get_value_as_string('Value', tag)

        return None

    def has_tag(self, key: str, ref_key: Optional[str] = None) -> bool:
        return self.get_tag(key, ref_key) is not None

    @property
    def cluster_name(self) -> Optional[str]:
        return self.get_tag(key=constants.IDEA_TAG_ENVIRONMENT_NAME)


class SocaVPC(SocaClusterResource):

    @property
    def vpc_id(self) -> str:
        return ModelUtils.get_value_as_string('VpcId', self.ref)

    @property
    def cidr_block(self) -> str:
        return ModelUtils.get_value_as_string('CidrBlock', self.ref)

    @property
    def description(self) -> str:
        title = self.title
        if ModelUtils.is_empty(title):
            title = ''
        return f'{title} {self.vpc_id} {self.cidr_block}'


class SocaCloudFormationStack(SocaClusterResource):

    @property
    def status(self) -> str:
        return ModelUtils.get_value_as_string('StackStatus', self.ref)

    @property
    def stack_type(self) -> Optional[str]:
        return self.get_tag(key=constants.IDEA_TAG_STACK_TYPE)

    def is_cluster(self) -> bool:
        return self.stack_type == constants.STACK_TYPE_CLUSTER

    def is_app(self) -> bool:
        return self.stack_type == constants.STACK_TYPE_APP

    def is_analytics(self) -> bool:
        return self.stack_type == constants.STACK_TYPE_ANALYTICS

    def is_alb(self) -> bool:
        return self.stack_type == constants.STACK_TYPE_ALB

    def is_job(self) -> bool:
        return self.stack_type == constants.STACK_TYPE_JOB


class SocaOpenSearchDomain(SocaClusterResource):

    @property
    def _domain_status(self) -> Optional[Dict]:
        return ModelUtils.get_value_as_dict('DomainStatus', self.ref)

    @property
    def vpc_id(self) -> Optional[str]:
        vpc_options = ModelUtils.get_value_as_dict('VPCOptions', self._domain_status)
        return ModelUtils.get_value_as_string('VPCId', vpc_options)

    @property
    def endpoint(self) -> str:
        return ModelUtils.get_value_as_string('Endpoint', self.ref)

    @property
    def vpc_endpoint(self) -> Optional[str]:
        endpoints = ModelUtils.get_value_as_dict('Endpoints', self._domain_status)
        if endpoints is None:
            return None
        for key, value in endpoints.items():
            return value


class SocaDirectory(SocaClusterResource):

    @property
    def directory_id(self) -> str:
        return ModelUtils.get_value_as_string('DirectoryId', self.ref)

    @property
    def short_name(self) -> str:
        return ModelUtils.get_value_as_string('ShortName', self.ref)

    @property
    def dns(self) -> str:
        return ModelUtils.get_value_as_string('DnsIpAddrs', self.ref)

    @property
    def vpc_id(self) -> Optional[str]:
        vpc_settings = ModelUtils.get_value_as_dict('VpcSettings', self.ref)
        return ModelUtils.get_value_as_string('VpcId', vpc_settings)


class SocaSubnet(SocaClusterResource):

    @property
    def vpc_id(self) -> str:
        return ModelUtils.get_value_as_string('VpcId', self.ref)

    @property
    def cidr_block(self) -> str:
        return ModelUtils.get_value_as_string('CidrBlock', self.ref)

    @property
    def subnet_id(self) -> str:
        return ModelUtils.get_value_as_string('SubnetId', self.ref)

    @property
    def availability_zone(self) -> str:
        return ModelUtils.get_value_as_string('AvailabilityZone', self.ref)

    @property
    def sort_order(self) -> int:
        availability_zone = self.availability_zone
        return ord(availability_zone[-1])


class SocaFileSystem(SocaClusterResource):
    provider: Optional[str]

    @property
    def file_system_id(self) -> str:
        file_system = self.ref['file_system']
        # Amazon File Cache uses FileCacheId vs. FileSystemId
        if self.provider == constants.STORAGE_PROVIDER_FSX_CACHE:
            return ModelUtils.get_value_as_string('FileCacheId', file_system)
        else:
            return ModelUtils.get_value_as_string('FileSystemId', file_system)

    def get_storage_virtual_machines(self) -> Optional[List[Dict]]:
        if self.provider != constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP:
            return None

        return ModelUtils.get_value_as_list('storage_virtual_machines', self.ref, [])

    def get_volumes(self) -> Optional[List[Dict]]:
        if self.provider not in (
            constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
            constants.STORAGE_PROVIDER_FSX_OPENZFS
        ):
            return None

        return ModelUtils.get_value_as_list('volumes', self.ref, [])

    @staticmethod
    def get_svm_id(svm_entry: Dict) -> str:
        return ModelUtils.get_value_as_string('StorageVirtualMachineId', svm_entry)

    @staticmethod
    def get_svm_lifecycle(svm_entry: Dict) -> str:
        return ModelUtils.get_value_as_string('Lifecycle', svm_entry)

    def get_storage_virtual_machine_title(self, svm_entry: Dict) -> str:
        name = ModelUtils.get_value_as_string('Name', svm_entry)
        lifecycle = self.get_svm_lifecycle(svm_entry)
        svm_id = self.get_svm_id(svm_entry)
        file_system_id = ModelUtils.get_value_as_string('FileSystemId', svm_entry)
        return f'{name} (SvmId: {svm_id}, FileSystemId: {file_system_id}, Lifecycle: {lifecycle})'

    @staticmethod
    def get_volume_id(volume_entry: Dict) -> str:
        return ModelUtils.get_value_as_string('VolumeId', volume_entry)

    @staticmethod
    def get_volume_svm_id(volume_entry: Dict) -> Optional[str]:
        volume_type = ModelUtils.get_value_as_string('VolumeType', volume_entry)
        if volume_type != 'ONTAP':
            return None
        ontap_config = ModelUtils.get_value_as_dict('OntapConfiguration', volume_entry)
        return ModelUtils.get_value_as_string('StorageVirtualMachineId', ontap_config)

    @staticmethod
    def get_volume_lifecycle(svm_entry: Dict) -> str:
        return ModelUtils.get_value_as_string('Lifecycle', svm_entry)

    def get_volume_title(self, volume_entry: Dict) -> str:
        name = ModelUtils.get_value_as_string('Name', volume_entry)
        lifecycle = self.get_volume_lifecycle(volume_entry)
        volume_id = self.get_volume_id(volume_entry)
        file_system_id = ModelUtils.get_value_as_string('FileSystemId', volume_entry)
        volume_path = self.get_volume_path(volume_entry)
        if self.provider == constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP:
            svm_id = self.get_volume_svm_id(volume_entry)
            return f'{name} (VolumeId: {volume_id}, SvmId: {svm_id}, FileSystemId: {file_system_id}, Lifecycle: {lifecycle}, VolumePath: {volume_path})'
        else:
            return f'{name} (VolumeId: {volume_id}, FileSystemId: {file_system_id}, Lifecycle: {lifecycle}, VolumePath: {volume_path})'

    def get_volume_path(self, volume_entry: Dict) -> str:
        if self.provider == constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP:
            ontap_config = ModelUtils.get_value_as_dict('OntapConfiguration', volume_entry)
            return ModelUtils.get_value_as_string('JunctionPath', ontap_config)
        elif self.provider == constants.STORAGE_PROVIDER_FSX_OPENZFS:
            openzfs_config = ModelUtils.get_value_as_dict('OpenZFSConfiguration', volume_entry)
            return ModelUtils.get_value_as_string('VolumePath', openzfs_config)
        else:
            raise exceptions.invalid_params(f'volume path not supported for provider: {self.provider}')


class SocaSecurityGroupPermission(SocaBaseModel):
    from_port: Optional[int]
    to_port: Optional[int]
    approved_ips: Optional[Set[str]]
    approved_groups_ids: Optional[Set[str]]
    approved_user_ids: Optional[Set[str]]
    type: Optional[str]


class SocaSecurityGroup(SocaClusterResource):

    @property
    def group_id(self) -> str:
        return ModelUtils.get_value_as_string('GroupId', self.ref)

    def _get_permissions(self, ingress=True):
        result = []

        if ingress:
            key = 'IpPermissions'
        else:
            key = 'IpPermissionsEgress'

        ip_permissions = ModelUtils.get_value_as_list(key, self.ref)
        if ip_permissions is None:
            return result

        for permission in ip_permissions:
            from_port = ModelUtils.get_value_as_int('FromPort', permission, -1)
            to_port = ModelUtils.get_value_as_int('ToPort', permission, -1)
            if from_port == -1 and to_port == -1:
                from_port = 0
                to_port = 65535

            approved_ips = set()
            ip_ranges = ModelUtils.get_value_as_list('IpRanges', permission, [])
            if len(ip_ranges) > 0:
                for ip_range in ip_ranges:
                    cidr_ip = ModelUtils.get_value_as_string('CidrIp', ip_range)
                    approved_ips.add(cidr_ip)

            approved_groups_ids = set()
            approved_user_ids = set()
            user_id_group_pairs = ModelUtils.get_value_as_list('UserIdGroupPairs', permission, [])
            if len(user_id_group_pairs) > 0:
                for pair in user_id_group_pairs:
                    group_id = ModelUtils.get_value_as_string('GroupId', pair)
                    if group_id:
                        approved_groups_ids.add(group_id)
                    user_id = ModelUtils.get_value_as_string('UserId', pair)
                    if user_id:
                        approved_user_ids.add(user_id)

            result.append(SocaSecurityGroupPermission(
                from_port=from_port,
                to_port=to_port,
                approved_ips=approved_ips,
                approved_groups_ids=approved_groups_ids,
                approved_user_ids=approved_user_ids
            ))

        return result

    @property
    def ingress_permissions(self) -> List[SocaSecurityGroupPermission]:
        return self._get_permissions(ingress=True)

    @property
    def egress_permissions(self) -> List[SocaSecurityGroupPermission]:
        return self._get_permissions(ingress=False)


class SocaIAMRole(SocaClusterResource):

    @property
    def role_name(self) -> str:
        return ModelUtils.get_value_as_string('RoleName', self.ref)

    @property
    def arn(self) -> str:
        return ModelUtils.get_value_as_string('Arn', self.ref)

    @property
    def description(self) -> Optional[str]:
        return ModelUtils.get_value_as_string('Description', self.ref)


class SocaS3Bucket(SocaClusterResource):
    has_permission: Optional[bool]

    @property
    def name(self) -> str:
        return ModelUtils.get_value_as_string('Name', self.ref)


class SocaSSHKeyPair(SocaClusterResource):

    @property
    def key_name(self) -> str:
        return ModelUtils.get_value_as_string('KeyName', self.ref)

    @property
    def key_fingerprint(self) -> str:
        return ModelUtils.get_value_as_string('KeyFingerprint', self.ref)


class SocaACMCertificate(SocaClusterResource):

    @property
    def certificate_arn(self) -> str:
        return ModelUtils.get_value_as_string('CertificateArn', self.ref)

    @property
    def domain_name(self) -> str:
        return ModelUtils.get_value_as_string('DomainName', self.ref)


class SocaAWSProfile(SocaClusterResource):

    @property
    def name(self) -> str:
        return str(self.ref)


class SocaEC2PrefixList(SocaClusterResource):

    @property
    def prefix_list_name(self) -> str:
        return ModelUtils.get_value_as_string('PrefixListName', self.ref)

    @property
    def prefix_list_id(self) -> str:
        return ModelUtils.get_value_as_string('PrefixListId', self.ref)

    def cidrs(self) -> List[str]:
        return ModelUtils.get_value_as_list('Cidrs', self.ref, [])
