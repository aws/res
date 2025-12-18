#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import uuid
from typing import Any, List, Optional, Union

import aws_cdk as cdk
import constructs
import res.constants as res_constants  # type: ignore
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_kms as kms
from res.utils.bootstrap_userdata_builder import (  # type: ignore
    BootstrapUserDataBuilder,
)

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs import iam, lambda_
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import (
    BastionHostCleanupPolicy,
    BastionHostPolicy,
)
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.resources.lambda_functions.bastion_host_cleanup_lambda import (
    bastion_host_cleanup_handler,
)


class BastionHostStack(ResBaseConstruct):
    def __init__(
        self,
        scope: constructs.Construct,
        lambda_layer: cdk.aws_lambda.LayerVersion,
        cluster_stack: ClusterStack,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):

        self.parameters = parameters
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.module_id = res_constants.MODULE_ID_BASTION_HOST
        self.aws_region = cdk.Aws.REGION
        self.cluster_stack = cluster_stack
        self.lambda_layer = lambda_layer

        super().__init__(
            scope,
            "bastion-host",
            self.cluster_name,
            parameters=parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "bastion-host",
            description=f"ModuleId: {self.module_id}, Version: {self.get_res_release_version()}",
        )
        self.has_iam_prefix_condition = InfraUtils.get_iam_prefix_condition(
            self.nested_stack, parameters
        )
        self.has_iam_path_condition = InfraUtils.get_iam_path_condition(
            self.nested_stack, parameters
        )

        self.cluster_settings = ClusterSettings(self.cluster_name, self.nested_stack)
        self.arn_builder = ArnBuilder(
            self.cluster_name, self.cluster_settings, self.parameters
        )

        self.bastion_host_role: Optional[iam.Role] = None
        self.bastion_host_instance_profile: Optional[iam.InstanceProfile] = None

        self.build_iam_roles()
        self.build_cluster_settings()

        self.build_bastion_host_cleanup_custom_resource()

        self.nested_stack.node.add_dependency(self.lambda_layer)
        self.apply_permission_boundary(self.nested_stack)
        self.add_common_tags(self.nested_stack)

    def build_iam_roles(self) -> None:

        ec2_managed_policies = self.get_ec2_instance_managed_policies()

        self.bastion_host_role = iam.Role(
            scope=self.nested_stack,
            name=f"{self.module_id}-role",
            description="IAM role assigned to the bastion-host",
            assumed_by=["ssm", "ec2"],
            managed_policies=ec2_managed_policies,
            inline_policies=[
                BastionHostPolicy(
                    self.nested_stack,
                    name="bastion-host-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                ),
            ],
            parameters=self.parameters,
            arn_builder=self.arn_builder,
        )

        self.bastion_host_instance_profile = iam.InstanceProfile(
            scope=self.nested_stack,
            name=f"{self.module_id}-instance-profile",
            parameters=self.parameters,
            roles=[self.bastion_host_role],
        )
        # Make sure the role exists before trying to create the instance profile
        self.bastion_host_instance_profile.node.add_dependency(self.bastion_host_role)

    def build_cluster_settings(self) -> None:

        cluster_settings = {}  # noqa
        cluster_settings["deployment_id"] = str(uuid.uuid4())
        cluster_settings["iam_role_arn"] = self.bastion_host_role.role_arn  # type: ignore
        cluster_settings["instance_profile_arn"] = (
            self.bastion_host_instance_profile.ref  # type: ignore
        )

        kms_key_id = self.cluster_settings.kms_ebs_key_id
        if kms_key_id:
            kms_key_arn = self.arn_builder.kms_ebs_key_arn
            ebs_kms_key = kms.Key.from_key_arn(
                scope=self.nested_stack, id=f"ebs-kms-key", key_arn=kms_key_arn  # type: ignore
            )
        else:
            ebs_kms_key = cdk.aws_kms.Alias.from_alias_name(
                scope=self.nested_stack,
                id=f"ebs-kms-key-default",
                alias_name="alias/aws/ebs",
            )
        cluster_settings["kms_key_id"] = ebs_kms_key.key_id

        proxy_config = {
            "http_proxy": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
            "https_proxy": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
            "no_proxy": self.parameters.get_str(InternetProxyKey.NO_PROXY),
        }

        userdata = BootstrapUserDataBuilder(
            aws_region=self.aws_region,
            bootstrap_package_uri=self.cluster_settings.installation_scripts_uri,
            install_commands=[
                f"/bin/bash scripts/infrastructure-host/install.sh -p false -c {self.module_id} -m {self.module_id} -e {self.cluster_name}"
            ],
            proxy_config=proxy_config,
            base_os=self.cluster_settings.base_os(),
        ).build()
        user_data_formatted = ec2.UserData.custom(userdata)
        user_data_base64 = cdk.Fn.base64(user_data_formatted.render())
        cluster_settings["user_data"] = user_data_base64

        cdk.CustomResource(
            self.nested_stack,
            f"{self.module_id}-cluster-settings",
            service_token=self.cluster_stack.cluster_settings_lambda.function_arn,
            properties={
                "cluster_name": self.cluster_name,
                "module_id": self.module_id,
                "version": self.get_res_release_version(),
                "settings": cluster_settings,
            },
            resource_type="Custom::ClusterSettings",
        )

    def get_ec2_instance_managed_policies(self) -> List[Any]:
        ec2_managed_policies = [
            self.cluster_stack.amazon_ssm_managed_instance_core_policy,
            self.cluster_stack.cloud_watch_agent_server_policy,
        ]

        ec2_managed_policies += self.cluster_settings.ec2_managed_policy_arns
        return ec2_managed_policies

    def build_bastion_host_cleanup_custom_resource(self) -> None:
        cleanup_function = lambda_.Function(
            self.nested_stack,
            "cleanup-bastion-host-and-route53",
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Lambda to remove the bastion host instance and Route53 record.",  # type: ignore
            timeout=cdk.Duration.seconds(600),  # type: ignore
            handler=bastion_host_cleanup_handler.handle_bastion_host_delete,
            initial_policy=BastionHostCleanupPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.cluster_stack.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
            layers=[self.lambda_layer],  # type: ignore
        )
        cdk.CustomResource(
            self,
            "cleanup-bastion-host-and-route53",
            service_token=cleanup_function.function_arn,
            properties={
                "cluster_name": self.cluster_name,
            },
            resource_type="Custom::BastionHostAndRoute53Cleanup",
        )
