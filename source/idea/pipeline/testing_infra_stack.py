#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
TestingInfraStack: provisions storage systems (EFS, FSx Lustre, FSx ONTAP, S3)
for RES integration tests using nested CloudFormation templates from HPC recipes.

Resource identifiers are written to SSM parameters so integration tests can
discover them at runtime.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import aws_cdk as cdk
import yaml
from aws_cdk import CfnParameter, CfnStack, Fn, Stack
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.parameters.parameters import RESParameters

# SSM parameter prefix for testing infra resources
SSM_PREFIX = "/res/testing-infra"

# Default storage config relative to this file
_DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "resources", "storage-config.yaml"
)


@dataclass
class StorageTemplateUrls:
    """Template URLs for each storage type (resolved from CDK context)."""

    efs: str = ""
    fsx_lustre: str = ""
    fsx_ontap: str = ""
    s3: str = ""


@dataclass
class StorageConfig:
    """A single storage entry from storage-config.yaml."""

    Name: str
    StorageType: str
    EfsSettings: Optional[Dict[str, Any]] = None
    FsxLustreSettings: Optional[Dict[str, Any]] = None
    FsxOntapSettings: Optional[Dict[str, Any]] = None
    S3Settings: Optional[Dict[str, Any]] = None


class TestingInfraStack(Stack):
    """
    Provisions storage systems for integration testing.

    Reads storage-config.yaml and creates a nested CloudFormation stack
    for each filesystem (EFS, FSx Lustre, FSx ONTAP) using HPC recipe
    templates, plus S3 buckets directly via CDK. Writes resource
    identifiers to SSM parameters for test consumption.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        parameters: Union[RESParameters, BIParameters],
        template_urls: StorageTemplateUrls,
        config_file: Optional[str] = None,
        ad_params: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.template_urls = template_urls
        self.parameters = parameters
        self._ad_params = ad_params

        # Resolve VPC and subnet values.
        # With batteries_included, values are SSM paths — use CfnParameter
        # to let CloudFormation resolve them at deploy time.
        # Without batteries_included, values are direct — use as-is.
        if isinstance(parameters, BIParameters):
            vpc_param = CfnParameter(
                self,
                "VpcIdParam",
                type="AWS::SSM::Parameter::Value<AWS::EC2::VPC::Id>",
                default=str(parameters.vpc_id),
            )
            self._vpc_id = vpc_param.value_as_string

            subnet_param = CfnParameter(
                self,
                "InfraSubnetsParam",
                type="AWS::SSM::Parameter::Value<List<AWS::EC2::Subnet::Id>>",
                default=str(parameters.infrastructure_host_subnets),
            )
            self._subnet_ids = Fn.join(",", subnet_param.value_as_list)
            self._single_subnet = Fn.select(0, subnet_param.value_as_list)
        else:
            self._vpc_id = str(parameters.vpc_id)
            subnets = parameters.infrastructure_host_subnets
            self._subnet_ids = ",".join(subnets)
            self._single_subnet = subnets[0]

        config_path = config_file or _DEFAULT_CONFIG_PATH
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self._ssm_params: List[ssm.StringParameter] = []

        for storage_entry in config.get("SharedStorage", []):
            storage_config = StorageConfig(**storage_entry)
            self._create_storage(storage_config)

    def _create_storage(self, config: StorageConfig) -> None:
        """Route to the appropriate builder based on storage type."""
        if config.StorageType == "Efs":
            self._create_efs(config)
        elif config.StorageType == "FsxLustre":
            self._create_fsx_lustre(config)
        elif config.StorageType == "FsxOntap":
            self._create_fsx_ontap(config)
        elif config.StorageType == "S3":
            self._create_s3(config)
        else:
            raise ValueError(f"Unknown StorageType: {config.StorageType}")

    def _create_efs(self, config: StorageConfig) -> None:
        """Create an EFS filesystem via nested HPC recipe template."""
        settings = config.EfsSettings or {}
        subnet_count = (
            "2"
            if isinstance(self.parameters, BIParameters)
            else str(len(self.parameters.infrastructure_host_subnets))
        )
        nested = CfnStack(
            self,
            f"EFS-{config.Name}",
            template_url=self.template_urls.efs,
            parameters={
                "VpcId": self._vpc_id,
                "SubnetIds": self._subnet_ids,
                "SubnetCount": subnet_count,
                "SecurityGroupName": self._get_shared_storage_sg(),
                "ThroughputMode": settings.get("ThroughputMode", "elastic"),
                "EnforceTLS": "false",
            },
        )

        # Write filesystem ID to SSM
        self._write_ssm_param(
            config.Name,
            "FileSystemId",
            nested.get_att("Outputs.EFSFilesystemId").to_string(),
            nested,
        )

    def _create_fsx_lustre(self, config: StorageConfig) -> None:
        """Create an FSx Lustre filesystem via nested HPC recipe template."""
        settings = config.FsxLustreSettings or {}

        nested = CfnStack(
            self,
            f"FSxLustre-{config.Name}",
            template_url=self.template_urls.fsx_lustre,
            parameters={
                "VpcId": self._vpc_id,
                "SubnetId": self._single_subnet,
                "SecurityGroupName": self._get_shared_storage_sg(),
                "Capacity": str(settings.get("StorageCapacity", 1200)),
            },
        )

        self._write_ssm_param(
            config.Name,
            "FileSystemId",
            nested.get_att("Outputs.FSxLustreFilesystemId").to_string(),
            nested,
        )

    def _create_fsx_ontap(self, config: StorageConfig) -> None:
        """Create an FSx ONTAP filesystem via nested HPC recipe template."""
        settings = config.FsxOntapSettings or {}

        cfn_params: Dict[str, str] = {
            "VpcId": self._vpc_id,
            "SubnetId": self._single_subnet,
            # Use the shared-storage SG which allows NFS from VDIs.
            # When AD join is enabled (future), additional SMB/AD rules will
            # need to be added to this SG or a separate SG used.
            "SecurityGroupName": self._get_shared_storage_sg(),
            "OntapStorageCapacity": str(settings.get("StorageCapacity", 1024)),
            "OntapThroughputCapacity": str(settings.get("ThroughputCapacity", 384)),
        }

        # Pass AD parameters if available and AD join is requested
        if settings.get("JoinAD") and self._ad_params:
            cfn_params["EnableActiveDirectory"] = "true"
            cfn_params["ActiveDirectoryName"] = self._ad_params.get(
                "ActiveDirectoryName", ""
            )
            cfn_params["DNSServerIPs"] = self._ad_params.get("DNSServerIPs", "")
            cfn_params["ServiceAccountCredentialsSecretArn"] = self._ad_params.get(
                "ServiceAccountCredentialsSecretArn", ""
            )
            cfn_params["ComputersOU"] = self._ad_params.get("ComputersOU", "")
            # Use "Domain Admins" — RESAdministrators may not exist at stack creation time.
            cfn_params["SudoersGroupName"] = "Domain Admins"

            # Add SMB/AD ports to the shared-storage SG so ONTAP can
            # communicate with the domain controller for AD join.
            # (Rules are defined in SharedStorageSecurityGroup.setup_ingress)

        nested = CfnStack(
            self,
            f"FSxONTAP-{config.Name}",
            template_url=self.template_urls.fsx_ontap,
            parameters=cfn_params,
        )

        self._write_ssm_param(
            config.Name,
            "FileSystemId",
            nested.get_att("Outputs.FileSystemId").to_string(),
            nested,
        )
        self._write_ssm_param(
            config.Name,
            "StorageVirtualMachineId",
            nested.get_att("Outputs.StorageVirtualMachineId").to_string(),
            nested,
        )
        self._write_ssm_param(
            config.Name,
            "SecurityGroupId",
            nested.get_att("Outputs.SecurityGroupId").to_string(),
            nested,
        )

    def _create_s3(self, config: StorageConfig) -> None:
        """Create an S3 bucket directly via CDK."""
        settings = config.S3Settings or {}
        bucket_name = f"{self.parameters.cluster_name}-{config.Name}-{Stack.of(self).account}-{Stack.of(self).region}"

        bucket = s3.Bucket(
            self,
            f"S3-{config.Name}",
            bucket_name=bucket_name,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Write bucket name and access mode to SSM
        self._write_ssm_param(
            config.Name,
            "BucketName",
            bucket.bucket_name,
        )
        self._write_ssm_param(
            config.Name,
            "AccessMode",
            settings.get("AccessMode", "read-write"),
        )

    def _write_ssm_param(
        self,
        storage_name: str,
        key: str,
        value: str,
        dependency: Optional[CfnStack] = None,
    ) -> None:
        """Write a resource identifier to SSM for test consumption."""
        param_name = f"{SSM_PREFIX}/{self.parameters.cluster_name}/{storage_name}/{key}"
        param = ssm.StringParameter(
            self,
            f"SSM-{storage_name}-{key}",
            parameter_name=param_name,
            string_value=value,
            description=f"Testing infra: {storage_name} {key}",
        )
        if dependency:
            param.node.add_dependency(dependency)
        self._ssm_params.append(param)

    def _get_shared_storage_sg(self) -> str:
        """Get the RES shared storage security group name/ID.

        The BI stack creates a security group named
        <EnvironmentName>-shared-storage-security-group that allows
        NFS/Lustre traffic from VDI instances.
        """
        return f"{self.parameters.cluster_name}-shared-storage-security-group"
