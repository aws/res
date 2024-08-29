#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideadatamodel import (
    SocaBaseModel, constants
)


from typing import Optional, Any, List


class FileSystem(SocaBaseModel):
    name: Optional[str]
    storage: Optional[Any]

    def get_name(self):
        return self.name

    def get_title(self):
        title = self.storage.get("title", self.get_name())
        return title

    def get_provider(self):
        return self.storage.get("provider")

    def get_filesystem_id(self):
        provider = self.get_provider()
        filesystem = self.storage.get(provider)
        # when provider is a s3_bucket, return bucket_arn as filesystem id
        if provider == constants.STORAGE_PROVIDER_S3_BUCKET:
            return filesystem.get("bucket_arn")
        return filesystem.get('file_system_id')

    def get_projects(self):
        return self.storage.get('projects')

    def get_mount_dir(self):
        return self.storage.get('mount_dir')

class EFSFileSystem(SocaBaseModel):
    efs: Optional[Any]

    def get_filesystem_id(self):
        return self.efs.get('FileSystemId')

    def get_encrypted(self):
        return self.efs.get('Encrypted')

    def get_kms_key_id(self):
        return self.efs.get('KmsKeyId')

    def get_performance_mode(self):
        return self.efs.get('PerformanceMode')

    def get_throughput_mode(self):
        return self.efs.get('ThroughputMode')


class FSxONTAPSVM(SocaBaseModel):
    storage_virtual_machine: Optional[Any]

    def get_filesystem_id(self):
        return self.storage_virtual_machine.get('FileSystemId')

    def get_svm_id(self):
        return self.storage_virtual_machine.get('StorageVirtualMachineId')

    def get_svm_endpoints(self):
        return self.storage_virtual_machine.get('Endpoints')

    def get_svm_nfs_dns(self):
        endpoints = self.get_svm_endpoints()
        return endpoints.get('Nfs').get('DNSName')

    def get_svm_iscsi_dns(self):
        endpoints = self.get_svm_endpoints()
        return endpoints.get('Iscsi').get('DNSName')

    def get_svm_mgmt_dns(self):
        endpoints = self.get_svm_endpoints()
        return endpoints.get('Management').get('DNSName')

    def get_svm_smb_dns(self):
        endpoints = self.get_svm_endpoints()
        if endpoints.get('Smb') is None:
            return None
        return endpoints.get('Smb').get('DNSName')


class FSxONTAPVolume(SocaBaseModel):
    volume: Optional[Any]

    def get_volume_id(self):
        return self.volume.get('VolumeId')

    def get_volume_path(self):
        return self.volume.get('OntapConfiguration').get('JunctionPath')

    def get_security_style(self):
        return self.volume.get('OntapConfiguration').get('SecurityStyle')


class FSxONTAPFileSystem(SocaBaseModel):
    filesystem: Optional[Any]
    svm: Optional[List[FSxONTAPSVM]]
    volume: Optional[List[FSxONTAPVolume]]

    def get_filesystem_id(self):
        return self.filesystem.get('FileSystemId')


class FSxLUSTREFileSystem(SocaBaseModel):
    filesystem: Optional[Any]

    def get_filesystem_id(self):
        return self.filesystem.get('FileSystemId')
