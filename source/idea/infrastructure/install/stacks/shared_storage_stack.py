#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import uuid
from typing import Any, Dict, List, Optional, Union

import aws_cdk as cdk
import constructs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_efs as efs

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs import ec2 as res_ec2
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.constructs.efs import EFS
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.parameters.shared_storage import SharedStorageKey


class SharedStorageStack(ResBaseConstruct):
    """
    Shared Storage Stack
     * Internal shared storage security group and file system.
    """

    def __init__(
        self,
        scope: constructs.Construct,
        lambda_layer: cdk.aws_lambda.LayerVersion,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):

        self.parameters = parameters
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.module_id = constants.MODULE_SHARED_STORAGE
        self.aws_region = cdk.Aws.REGION
        self.lambda_layer = lambda_layer

        super().__init__(
            scope,
            "shared-storage",
            self.cluster_name,
            parameters=parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "shared-storage",
            description=f"ModuleId: {self.module_id}, Version: {self.get_res_release_version()}",
        )

        self.add_common_tags(self.nested_stack)
        cdk.Tags.of(self.nested_stack).add(
            constants.RES_TAG_MODULE_NAME,
            constants.MODULE_SHARED_STORAGE,
        )
        cdk.Tags.of(self.nested_stack).add(
            constants.RES_TAG_MODULE_ID,
            constants.MODULE_SHARED_STORAGE,
        )

        self.has_iam_prefix_condition = InfraUtils.get_iam_prefix_condition(
            self.nested_stack, parameters
        )
        self.has_iam_path_condition = InfraUtils.get_iam_path_condition(
            self.nested_stack, parameters
        )

        self.cluster_settings = ClusterSettings(self.cluster_name, self.nested_stack)

        self.apply_permission_boundary(self.nested_stack)

        self.arn_builder = ArnBuilder(self.cluster_name, self.cluster_settings)
        self._existing_vpc: Optional[res_ec2.ExistingVpc] = None

        self.security_group: Optional[res_ec2.SecurityGroup] = None
        self.internal_efs: Optional[EFS] = None

        # setup existing vpc reference
        self.setup_vpc()
        self.build_security_group()
        self.build_internal_shared_storage()
        self.build_cluster_settings()

        self.nested_stack.node.add_dependency(self.lambda_layer)

    @property
    def vpc(self) -> cdk.aws_ec2.IVpc:
        return self._existing_vpc.vpc  # type: ignore

    def setup_vpc(self) -> None:
        self._existing_vpc = res_ec2.ExistingVpc(
            scope=self.nested_stack,
            name="shared-storage-vpc",
            arn_builder=self.arn_builder,
            lambda_layer=self.lambda_layer,
            parameters=self.parameters,
        )

    def build_security_group(self) -> None:

        self.security_group = res_ec2.SharedStorageSecurityGroup(
            scope=self.nested_stack,
            name="shared-storage-security-group",
            vpc=self.vpc,
            parameters=self.parameters,
        )

        cdk.Tags.of(self.security_group).add("res:ModuleId", "shared-storage")
        cdk.Tags.of(self.security_group).add("res:ModuleName", "shared-storage")
        cdk.Tags.of(self.security_group).add(
            "res:ModuleVersion", self.get_res_release_version()
        )

    def build_internal_shared_storage(self) -> None:
        """
        provision new internal EFS
        """

        if self.security_group:
            self.internal_efs = EFS(
                scope=self.nested_stack,
                name="internal-storage-efs",
                vpc=self.vpc,
                security_group=self.security_group,
                parameters=self.parameters,
                cluster_settings=self.cluster_settings,
            )

            # Get infrastructure subnets list
            infrastructure_subnets: List[str] = self.cluster_settings.infrastructure_host_subnets  # type: ignore
            for i, subnet_id in enumerate(infrastructure_subnets):
                mount_target = efs.CfnMountTarget(
                    self.nested_stack,
                    f"mount-target-{i}",
                    file_system_id=self.internal_efs.file_system.ref,
                    security_groups=[self.security_group.security_group_id],
                    subnet_id=subnet_id,
                )
                mount_target.add_dependency(self.internal_efs.file_system)

    def build_cluster_settings(self) -> None:
        cluster_settings: Dict[str, Any] = {
            "deployment_id": str(uuid.uuid4()),
        }

        if self.security_group:
            cluster_settings["security_group_id"] = (
                self.security_group.security_group_id
            )

        home_efs_id = self.parameters.get_str(
            SharedStorageKey.SHARED_HOME_FILESYSTEM_ID
        )
        if home_efs_id:
            cluster_settings["home.efs.dns"] = (
                f"{home_efs_id}.efs.{self.aws_region}.amazonaws.com"
            )

        if self.internal_efs:
            cluster_settings["internal.efs.dns"] = (
                f"{self.internal_efs.file_system.ref}.efs.{self.aws_region}.amazonaws.com"
            )
            cluster_settings["internal.efs.file_system_id"] = (
                self.internal_efs.file_system.ref
            )
            cluster_settings["internal.efs.vpc_id"] = self.vpc.vpc_id

        cluster_settings_lambda_arn = InfraUtils.get_cluster_setting_string(
            self.nested_stack,
            "cluster.cluster_settings_lambda_arn",
            self.cluster_name,
        )

        cdk.CustomResource(
            self.nested_stack,
            "shared-storage-settings",
            service_token=cluster_settings_lambda_arn,
            properties={
                "cluster_name": self.cluster_name,
                "module_id": self.module_id,
                "version": self.get_res_release_version(),
                "settings": cluster_settings,
            },
            resource_type="Custom::ClusterSettings",
        )
