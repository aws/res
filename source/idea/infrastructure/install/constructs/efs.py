#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Union

import aws_cdk as cdk
import constructs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_efs as efs

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies.shared_efs_file_storage_policy import (
    SharedEfsFileStoragePolicy,
)


class EFS(ResBaseConstruct):
    """
    Amazon EFS construct for RES infrastructure
    """

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        vpc: ec2.IVpc,
        security_group: ec2.ISecurityGroup,
        parameters: Union[RESParameters, BIParameters],
        cluster_settings: ClusterSettings,
    ):

        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        super().__init__(scope, name, self.cluster_name, parameters)

        self.scope = scope
        self.vpc = vpc
        self.security_group = security_group

        efs_config = cluster_settings.shared_storage_efs_config
        self.encrypted = efs_config.get("encrypted")
        self.throughput_mode = efs_config.get("throughput_mode")
        self.performance_mode = efs_config.get("performance_mode")
        self.kms_key_id = efs_config.get("kms_key_id")
        removal_policy = efs_config.get("removal_policy")
        self.transition_to_ia = efs_config.get("transition_to_ia")

        if removal_policy == "DESTROY":
            removal_policy = "DELETE"

        if removal_policy:
            self.deletion_policy = cdk.CfnDeletionPolicy(removal_policy)

        self.file_system = self._build_file_system()

    def _build_file_system(self) -> efs.CfnFileSystem:
        lifecycle_policies = None
        if self.transition_to_ia:
            lifecycle_policies = [
                efs.CfnFileSystem.LifecyclePolicyProperty(
                    transition_to_ia=self.transition_to_ia
                )
            ]

        file_system = efs.CfnFileSystem(
            scope=self.scope,
            id="internal-storage-efs",
            encrypted=self.encrypted,
            file_system_tags=[
                efs.CfnFileSystem.ElasticFileSystemTagProperty(
                    key="Name",
                    value=self.build_resource_name(
                        "internal-storage-efs", self.cluster_name
                    ),
                ),
                efs.CfnFileSystem.ElasticFileSystemTagProperty(
                    key="res:ModuleId", value="shared-storage"
                ),
                efs.CfnFileSystem.ElasticFileSystemTagProperty(
                    key="res:ModuleName", value="shared-storage"
                ),
                efs.CfnFileSystem.ElasticFileSystemTagProperty(
                    key="res:ModuleVersion", value=self.get_res_release_version()
                ),
                efs.CfnFileSystem.ElasticFileSystemTagProperty(
                    key="res:EnvironmentName", value=self.cluster_name
                ),
                efs.CfnFileSystem.ElasticFileSystemTagProperty(
                    key="res:BackupPlan", value=f"{self.cluster_name}-cluster"
                ),
            ],
            kms_key_id=self.kms_key_id,
            throughput_mode=self.throughput_mode,
            performance_mode=self.performance_mode,
            lifecycle_policies=lifecycle_policies,
            file_system_policy=SharedEfsFileStoragePolicy.create_policy(),
        )

        if hasattr(self, "deletion_policy"):
            file_system.cfn_options.deletion_policy = self.deletion_policy

        return file_system
