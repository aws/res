#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aws_cdk as cdk
import constructs
from aws_cdk import aws_autoscaling as asg
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_kms as kms
from aws_cdk import aws_sqs as sqs
from cdk_nag import NagSuppressions
from res.constants import ENVIRONMENT_NAME_KEY, OLD_CUSTOM_TAG_KEYS  # type: ignore

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs import ec2
from idea.infrastructure.install.constructs import ec2 as res_ec2
from idea.infrastructure.install.constructs import iam, lambda_
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.constructs.secretmanager import OAuthClient
from idea.infrastructure.install.constructs.sqs import SQSQueue
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_manager_settings import (
    ClusterManagerSettings,
)
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies.cluster_manager_policy import (
    ClusterManagerPolicy,
)
from idea.infrastructure.install.policies.configure_sso_lambda_policy import (
    ConfigureSSOLambdaPolicy,
)
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.install.stacks.identity_stack import IdentityStack
from idea.infrastructure.resources.lambda_functions.custom_resource.configure_sso_lambda import (
    configure_sso_handler,
)
from idea.library.src.res.utils.bootstrap_userdata_builder import (
    BootstrapUserDataBuilder,
)


class ClusterManagerStack(ResBaseConstruct):
    """
    Setup infrastructure for Cluster Manager Module
    """

    def __init__(
        self,
        scope: constructs.Construct,
        lambda_layer: cdk.aws_lambda.LayerVersion,
        identity_stack: IdentityStack,
        cluster_stack: ClusterStack,
        params_transformer: cdk.CustomResource,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):

        self.parameters = parameters
        self.params_transformer = params_transformer
        self.cluster_stack = cluster_stack
        self.identity_stack = identity_stack
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.module_id = constants.MODULE_CLUSTER_MANAGER
        self.lambda_layer = lambda_layer
        self.log_retention_role_arn = (
            self.cluster_stack.lambda_log_retention_role.role_arn
        )
        self.deployment_id = str(uuid.uuid4())
        self.aws_region = cdk.Aws.REGION

        self._existing_vpc: Optional[cdk.aws_ec2.IVpc] = None

        self.internal_https_listener_arn = (
            self.cluster_stack.internal_alb_https_listener.attr_listener_arn  # type: ignore
        )

        self.oauth_credentials_lambda_arn = (
            self.identity_stack.oauth_credentials_lambda.function_arn
        )
        self.bastion_host_sg_id = self.cluster_stack.security_groups[
            "bastion-host"
        ].security_group_id

        self.external_alb_sg_id = self.cluster_stack.security_groups[
            "external-load-balancer"
        ].security_group_id

        super().__init__(
            scope,
            "cluster-manager",
            self.cluster_name,
            parameters=parameters,
        )

        self.PROXY_CONFIG = {
            "http_proxy": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
            "https_proxy": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
            "no_proxy": self.parameters.get_str(InternetProxyKey.NO_PROXY),
        }

        self.oauth2_client_secret: Optional[OAuthClient] = None
        self.notifications_sqs_queue: Optional[SQSQueue] = None
        self.cluster_manager_role: Optional[iam.Role] = None
        self.cluster_manager_security_group: Optional[
            ec2.ClusterManagerSecurityGroup
        ] = None
        self.auto_scaling_group: Optional[asg.AutoScalingGroup] = None
        self.web_portal_endpoint: Optional[cdk.CustomResource] = None
        self.external_endpoint: Optional[cdk.CustomResource] = None
        self.internal_endpoint: Optional[cdk.CustomResource] = None

        self.nested_stack = cdk.NestedStack(
            scope,
            "cluster-manager",
            description=f"ModuleId: {self.module_id}, Version: {self.get_res_release_version()}",
        )

        self.apply_permission_boundary(self.nested_stack)
        self.add_common_tags(self.nested_stack)

        self.cluster_settings = ClusterSettings(self.cluster_name, self.nested_stack)
        self.cluster_manager_settings = ClusterManagerSettings(
            self.cluster_name, self.nested_stack
        )
        self.arn_builder = ArnBuilder(
            self.cluster_name, self.cluster_settings, parameters=parameters
        )

        self.has_iam_prefix_condition = InfraUtils.get_iam_prefix_condition(
            self.nested_stack, parameters
        )

        self.has_iam_path_condition = InfraUtils.get_iam_path_condition(
            self.nested_stack, parameters
        )

        self.internal_alb_dns_name = self.cluster_stack.internal_alb.attr_dns_name  # type: ignore

        self.internal_alb_access_logs = (
            self.cluster_settings.internal_alb_enable_access_log
        )

        self.user_pool = cognito.UserPool.from_user_pool_id(
            self.nested_stack,
            f"{self.module_id}-get-user-pool",
            self.cluster_settings.user_pool_id,  # type: ignore
        )

        self.bastion_host_sg = cdk.aws_ec2.SecurityGroup.from_security_group_id(
            self.nested_stack, "BastionHostSG", self.bastion_host_sg_id
        )
        self.external_alb_sg = cdk.aws_ec2.SecurityGroup.from_security_group_id(
            self.nested_stack, "ExternalAlbSG", self.external_alb_sg_id
        )

        self.setup_vpc()
        self.build_oauth2_client()
        self.build_sqs_queues()
        self.build_iam_roles()
        self.build_security_groups()
        self.build_auto_scaling_group()
        self.build_endpoints()
        self.build_configure_sso_lambda()
        self.build_cluster_settings()

    @property
    def vpc(self) -> cdk.aws_ec2.IVpc:
        return self.cluster_stack.vpc

    def setup_vpc(self) -> None:
        self._existing_vpc = self.cluster_stack.vpc

    def build_oauth2_client(self) -> None:
        resource_server = self.user_pool.add_resource_server(
            id="resource-server",
            identifier=f"{self.cluster_name}-{self.module_id}",
            scopes=[
                cognito.ResourceServerScope(
                    scope_name="read", scope_description="Allow Read Access"
                ),
                cognito.ResourceServerScope(
                    scope_name="write", scope_description="Allow Write Access"
                ),
            ],
        )

        client = self.user_pool.add_client(
            id=f"{self.module_id}-client",
            access_token_validity=cdk.Duration.hours(1),
            auth_flows=cognito.AuthFlow(admin_user_password=True),
            generate_secret=True,
            id_token_validity=cdk.Duration.hours(1),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(client_credentials=True),
                scopes=[
                    cognito.OAuthScope.custom(
                        f"{self.cluster_name}-{self.module_id}/read"
                    ),
                    cognito.OAuthScope.custom(
                        f"{self.cluster_name}-{self.module_id}/write"
                    ),
                ],
            ),
            refresh_token_validity=cdk.Duration.hours(
                self.cluster_manager_settings.refresh_token_validity_hours
            ),
            user_pool_client_name=f"{self.cluster_name}-{self.module_id}",
        )
        client.node.add_dependency(resource_server)

        client_secret_cr = cdk.CustomResource(
            scope=self.nested_stack,
            id=f"{self.module_id}-creds",
            service_token=self.oauth_credentials_lambda_arn,
            properties={
                "UserPoolId": self.user_pool.user_pool_id,
                "ClientId": client.user_pool_client_id,
            },
            resource_type="Custom::GetOAuthCredentials",
        )

        self.oauth2_client_secret = OAuthClient(
            scope=self.nested_stack,
            name=self.module_id,
            parameters=self.parameters,
            module_name=constants.MODULE_CLUSTER_MANAGER,
            kms_key_id=self.cluster_settings.kms_secretsmanager_key_id,
            client_id=client.user_pool_client_id,
            client_secret=client_secret_cr.get_att_string("ClientSecret"),
        )

    def build_iam_roles(self) -> None:

        self.cluster_manager_role = iam.Role(
            scope=self.nested_stack,
            description="IAM role assigned to the cluster-manager",
            name=f"{self.module_id}-role",
            assumed_by=["ssm", "ec2"],
            parameters=self.parameters,
            arn_builder=self.arn_builder,
            inline_policies=[
                cdk.aws_iam.Policy(  # type: ignore[list-item]
                    self.nested_stack,
                    f"{self.module_id}-policy",
                    statements=ClusterManagerPolicy.create_policy_statements(
                        arn_builder=self.arn_builder
                    ),
                )
            ],
        )

        if self.cluster_stack.amazon_ssm_managed_instance_core_policy:
            self.cluster_manager_role.add_managed_policy(
                self.cluster_stack.amazon_ssm_managed_instance_core_policy
            )
        if self.cluster_stack.cloud_watch_agent_server_policy:
            self.cluster_manager_role.add_managed_policy(
                self.cluster_stack.cloud_watch_agent_server_policy
            )

        self.instance_profile = iam.InstanceProfile(
            scope=self.nested_stack,
            name=f"{self.module_id}-instance-profile",
            roles=[self.cluster_manager_role],
            parameters=self.parameters,
        )

        self.instance_profile.node.add_dependency(self.cluster_manager_role)

    def build_sqs_queues(self) -> None:

        sqs_kms_key_id = self.cluster_settings.kms_sqs_key_id

        self.notification_dlq = SQSQueue(
            id=f"{self.module_id}-notifications-dlq",
            scope=self.nested_stack,
            parameters=self.parameters,
            arn_builder=self.arn_builder,
            fifo=True,
            content_based_deduplication=True,
            encryption_master_key=sqs_kms_key_id,
        )

        self.notifications_sqs_queue = SQSQueue(
            id=f"{self.module_id}-notifications",
            scope=self.nested_stack,
            parameters=self.parameters,
            arn_builder=self.arn_builder,
            fifo=True,
            content_based_deduplication=True,
            encryption_master_key=sqs_kms_key_id,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3, queue=self.notification_dlq
            ),
        )

        cdk.Tags.of(self.notifications_sqs_queue).add("Module", self.module_id)
        cdk.Tags.of(self.notification_dlq).add("Module", self.module_id)

    def build_security_groups(self) -> None:
        self.cluster_manager_security_group = ec2.ClusterManagerSecurityGroup(
            scope=self.nested_stack,
            name=f"{self.module_id}-security-group",
            vpc=self.vpc,
            bastion_host_security_group=self.bastion_host_sg,
            loadbalancer_security_group=self.external_alb_sg,
            parameters=self.parameters,
        )

    def build_auto_scaling_group(self) -> None:

        key_pair_name = self.parameters.get_str(CommonKey.SSH_KEY_PAIR)

        base_os = self.cluster_settings.base_os()

        autoscaling_settings = self.cluster_manager_settings.autoscaling_settings
        is_public = autoscaling_settings.get("public")  # type: ignore
        instance_type = autoscaling_settings.get("instance_type")  # type: ignore
        volume_size = autoscaling_settings.get("volume_size")  # type: ignore
        enable_detailed_monitoring = autoscaling_settings.get(  # type: ignore
            "enable_detailed_monitoring"
        )
        min_capacity = autoscaling_settings.get("min_capacity")  # type: ignore
        max_capacity = autoscaling_settings.get("max_capacity")  # type: ignore
        cooldown_minutes = autoscaling_settings.get("cooldown_minutes")  # type: ignore
        default_instance_warmup = autoscaling_settings.get(  # type: ignore
            "default_instance_warmup"
        )

        new_instances_protected_from_scale_in = autoscaling_settings.get(  # type: ignore
            "new_instances_protected_from_scale_in"
        )

        elb_healthcheck_grace_time_minutes = autoscaling_settings.get(  # type: ignore
            "elb_healthcheck", {}
        ).get("grace_time_minutes")

        scaling_policy_target_utilization_percent = autoscaling_settings.get(  # type: ignore
            "cpu_utilization_scaling_policy", {}
        ).get(
            "target_utilization_percent"
        )

        scaling_policy_estimated_instance_warmup_minutes = autoscaling_settings.get(  # type: ignore
            "cpu_utilization_scaling_policy", {}
        ).get(
            "estimated_instance_warmup_minutes"
        )

        rolling_update_max_batch_size = autoscaling_settings.get(  # type: ignore
            "rolling_update_policy", {}
        ).get("max_batch_size")

        rolling_update_min_instances_in_service = autoscaling_settings.get(  # type: ignore
            "rolling_update_policy", {}
        ).get(
            "min_instances_in_service"
        )

        rolling_update_pause_time_minutes = autoscaling_settings.get(  # type: ignore
            "rolling_update_policy", {}
        ).get("pause_time_minutes")

        metadata_http_tokens = autoscaling_settings.get(  # type: ignore
            "metadata_http_tokens"
        )

        kms_key_id = self.cluster_settings.kms_ebs_key_id
        if kms_key_id:
            kms_key_arn = self.arn_builder.kms_ebs_key_arn
            self.ebs_kms_key = kms.Key.from_key_arn(
                scope=self.nested_stack, id=f"ebs-kms-key", key_arn=kms_key_arn  # type: ignore
            )
        else:
            self.ebs_kms_key = cdk.aws_kms.Alias.from_alias_name(
                scope=self.nested_stack,
                id=f"ebs-kms-key-default",
                alias_name="alias/aws/ebs",
            )

        subnets_ids: List[str] = []
        if is_public:
            subnets_ids = self.cluster_settings.load_balancer_subnets  # type: ignore
        else:
            subnets_ids = self.cluster_settings.infrastructure_host_subnets  # type: ignore

        subnets = []
        for i, subnet_id in enumerate(subnets_ids):
            subnets.append(
                cdk.aws_ec2.Subnet.from_subnet_id(
                    self.nested_stack, f"Subnet-{i}", subnet_id
                )
            )

        vpc_subnets = cdk.aws_ec2.SubnetSelection(subnets=subnets)

        block_device_name = InfraUtils.get_ec2_block_device_name(base_os)

        get_ami_cr = InfraUtils.get_cluster_setting_custom_resource(
            self.nested_stack,
            "cluster-manager.ec2.autoscaling.instance_ami",
            self.cluster_name,
        )
        custom_ami = get_ami_cr.get_response_field("Item.value.S")

        bootstrap_package_uri = self.cluster_settings.installation_scripts_uri

        cluster_manager_userdata = BootstrapUserDataBuilder(
            base_os=base_os,
            aws_region=self.aws_region,
            bootstrap_package_uri=bootstrap_package_uri,  # type: ignore
            proxy_config=self.PROXY_CONFIG,
            install_commands=[
                f"/bin/bash scripts/infrastructure-host/install.sh -p false -c {self.module_id} -m {self.module_id} -e {self.cluster_name}"
            ],
        ).build()

        launch_template = cdk.aws_ec2.LaunchTemplate(
            self.nested_stack,
            f"{self.module_id}-lt",
            instance_type=cdk.aws_ec2.InstanceType(instance_type),
            user_data=cdk.aws_ec2.UserData.custom(cluster_manager_userdata),
            machine_image=cdk.aws_ec2.MachineImage.latest_amazon_linux2(),
            security_group=self.cluster_manager_security_group,
            key_name=key_pair_name,
            block_devices=[
                cdk.aws_ec2.BlockDevice(
                    device_name=block_device_name,
                    volume=cdk.aws_ec2.BlockDeviceVolume(
                        ebs_device=cdk.aws_ec2.EbsDeviceProps(
                            encrypted=True,
                            kms_key=self.ebs_kms_key,
                            volume_size=volume_size,
                            volume_type=cdk.aws_ec2.EbsDeviceVolumeType.GP3,
                        )
                    ),
                )
            ],
            require_imdsv2=True if metadata_http_tokens == "required" else False,
            associate_public_ip_address=is_public,
            version_description=self.deployment_id,
        )

        # Add Name tag to ensure instances get proper names
        cdk.Tags.of(launch_template).add("Name", f"{self.cluster_name}-cluster-manager")

        launch_template.node.add_dependency(get_ami_cr)

        cfn_launch_template: cdk.aws_ec2.CfnLaunchTemplate = (
            launch_template.node.default_child  # type: ignore[assignment]
        )

        cfn_launch_template.add_property_override(
            "LaunchTemplateData.IamInstanceProfile",
            {
                "Arn": self.arn_builder.get_instance_profile_arn_from_ref(
                    self.instance_profile.ref
                )
            },
        )

        cfn_launch_template.add_property_override(
            "LaunchTemplateData.ImageId", custom_ami
        )

        self.auto_scaling_group = asg.AutoScalingGroup(
            self.nested_stack,
            id="cluster-manager-asg",
            vpc=self.vpc,
            vpc_subnets=vpc_subnets,
            auto_scaling_group_name=f"{self.cluster_name}-{self.module_id}-asg",
            launch_template=launch_template,
            instance_monitoring=(
                asg.Monitoring.DETAILED
                if enable_detailed_monitoring
                else asg.Monitoring.BASIC
            ),
            group_metrics=[asg.GroupMetrics.all()],
            min_capacity=min_capacity,
            max_capacity=max_capacity,
            new_instances_protected_from_scale_in=new_instances_protected_from_scale_in,
            default_instance_warmup=cdk.Duration.minutes(default_instance_warmup),
            cooldown=cdk.Duration.minutes(cooldown_minutes),
            health_check=asg.HealthCheck.elb(
                grace=cdk.Duration.minutes(elb_healthcheck_grace_time_minutes)
            ),
            update_policy=asg.UpdatePolicy.rolling_update(
                max_batch_size=rolling_update_max_batch_size,
                min_instances_in_service=rolling_update_min_instances_in_service,
                pause_time=cdk.Duration.minutes(rolling_update_pause_time_minutes),
            ),
            termination_policies=[asg.TerminationPolicy.DEFAULT],
        )

        self.auto_scaling_group.scale_on_cpu_utilization(
            "cpu-utilization-scaling-policy",
            target_utilization_percent=scaling_policy_target_utilization_percent,
            estimated_instance_warmup=cdk.Duration.minutes(
                scaling_policy_estimated_instance_warmup_minutes
            ),
        )

        cdk.Tags.of(self.auto_scaling_group).add(
            constants.RES_TAG_NAME, f"{self.cluster_name}-cluster-manager"
        )
        cdk.Tags.of(self.auto_scaling_group).add(
            constants.RES_TAG_ENVIRONMENT_NAME, self.cluster_name
        )
        cdk.Tags.of(self.auto_scaling_group).add(
            constants.RES_TAG_MODULE_ID, self.module_id
        )
        cdk.Tags.of(self.auto_scaling_group).add(
            constants.RES_TAG_MODULE_NAME, self.module_id
        )
        cdk.Tags.of(self.auto_scaling_group).add(
            constants.RES_TAG_MODULE_VERSION, self.get_res_release_version()
        )
        cdk.Tags.of(self.auto_scaling_group).add(
            constants.RES_TAG_NODE_TYPE, constants.NODE_TYPE_APP
        )

        self.auto_scaling_group.node.add_dependency(self.notifications_sqs_queue)

    def build_endpoints(self) -> None:

        external_https_listener_arn = (
            self.cluster_stack.external_alb_https_listener.attr_listener_arn  # type: ignore
        )
        cdk.CfnOutput(
            self.nested_stack,
            "ExternalHttpsListener",
            value=external_https_listener_arn,
        )

        self.default_target_group = elbv2.CfnTargetGroup(
            self.nested_stack,
            "web-portal-target-group",
            port=8443,
            protocol="HTTPS",
            target_type="instance",
            vpc_id=self.vpc.vpc_id,
            name=InfraUtils.get_target_group_name(
                self.cluster_name, self.module_id, "web-portal"
            ),
            health_check_path="/healthcheck",
        )

        self.web_portal_endpoint = cdk.CustomResource(
            self.nested_stack,
            "web-portal-endpoint",
            service_token=self.cluster_stack.cluster_endpoints_lambda.function_arn,  # type: ignore
            properties={
                "endpoint_name": f"{self.module_id}-web-portal-endpoint",
                "listener_arn": external_https_listener_arn,
                "priority": 0,
                "default_action": True,
                "actions": [
                    {"Type": "forward", "TargetGroupArn": self.default_target_group.ref}
                ],
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::WebPortalEndpoint",
        )

        external_endpoints_settings = (
            self.cluster_manager_settings.external_endpoints_settings
        )
        external_endpoint_priority = external_endpoints_settings.get("priority")
        external_endpoint_path_patterns = external_endpoints_settings.get(
            "path_patterns", []
        )

        self.external_target_group = elbv2.CfnTargetGroup(
            self.nested_stack,
            f"{self.module_id}-external-target-group",
            port=8443,
            protocol="HTTPS",
            target_type="instance",
            vpc_id=self.vpc.vpc_id,
            name=InfraUtils.get_target_group_name(
                self.cluster_name, self.module_id, "cm-ext"
            ),
            health_check_path="/healthcheck",
        )

        self.external_endpoint = cdk.CustomResource(
            self.nested_stack,
            "external-endpoint",
            service_token=self.cluster_stack.cluster_endpoints_lambda.function_arn,  # type: ignore
            properties={
                "endpoint_name": f"{self.module_id}-external-endpoint",
                "listener_arn": external_https_listener_arn,
                "priority": external_endpoint_priority,
                "conditions": [
                    {"Field": "path-pattern", "Values": external_endpoint_path_patterns}
                ],
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": self.external_target_group.ref,
                    }
                ],
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::ClusterManagerEndpointExternal",
        )

        internal_endpoints_settings = (
            self.cluster_manager_settings.internal_endpoints_settings
        )
        internal_endpoint_priority = internal_endpoints_settings.get("priority")
        internal_endpoint_path_patterns = internal_endpoints_settings.get(
            "path_patterns", []
        )

        self.internal_target_group = elbv2.CfnTargetGroup(
            self.nested_stack,
            f"{self.module_id}-internal-target-group",
            port=8443,
            protocol="HTTPS",
            target_type="instance",
            vpc_id=self.vpc.vpc_id,
            name=InfraUtils.get_target_group_name(
                self.cluster_name, self.module_id, "cm-int"
            ),
            health_check_path="/healthcheck",
        )

        self.internal_endpoint = cdk.CustomResource(
            self.nested_stack,
            "internal-endpoint",
            service_token=self.cluster_stack.cluster_endpoints_lambda.function_arn,  # type: ignore
            properties={
                "endpoint_name": f"{self.module_id}-internal-endpoint",
                "listener_arn": self.cluster_stack.internal_alb_https_listener.attr_listener_arn,  # type: ignore
                "priority": internal_endpoint_priority,
                "conditions": [
                    {"Field": "path-pattern", "Values": internal_endpoint_path_patterns}
                ],
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": self.internal_target_group.ref,
                    }
                ],
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::ClusterManagerEndpointInternal",
        )

        self.auto_scaling_group.node.default_child.target_group_arns = [  # type: ignore[union-attr]
            self.default_target_group.ref,
            self.internal_target_group.ref,
            self.external_target_group.ref,
        ]

    def host_modules(self) -> List[str]:
        pam_modules = self.cluster_settings.host_modules_pam
        nss_modules = self.cluster_settings.host_modules_nss
        return pam_modules + nss_modules  # type: ignore

    def build_host_module_s3_url(self, host_module_name: str, os_arch: str) -> str:
        return f"s3://{self.cluster_settings.staging_bucket}/host_modules/{host_module_name}/latest/{os_arch}/{host_module_name}.so"

    def build_cluster_settings(self) -> None:

        cluster_settings = {
            "deployment_id": str(uuid.uuid4()),
            "client_id": self.oauth2_client_secret.client_id.ref,  # type: ignore[union-attr]
            "client_secret_name": self.oauth2_client_secret.client_secret.name,  # type: ignore[union-attr]
            "client_secret": self.oauth2_client_secret.client_secret.ref,  # type: ignore[union-attr]
            "client_secret_id_name": self.oauth2_client_secret.client_id.name,  # type: ignore[union-attr]
            "client_secret_id_ref": self.oauth2_client_secret.client_id.ref,  # type: ignore[union-attr]
            "security_group_id": self.cluster_manager_security_group.security_group_id,  # type: ignore[union-attr]
            "iam_role_arn": self.cluster_manager_role.role_arn,  # type: ignore[union-attr]
            "notifications_queue_url": self.notifications_sqs_queue.queue_url,  # type: ignore[union-attr]
            "notifications_queue_arn": self.notifications_sqs_queue.queue_arn,  # type: ignore[union-attr]
        }

        host_modules = self.host_modules()

        for host_module_name in host_modules:
            if host_module_name:
                for os_arch in ["x86_64", "arm64"]:
                    cluster_settings[
                        f"host_modules.{host_module_name}.{os_arch}.s3_url"
                    ] = str(self.build_host_module_s3_url(host_module_name, os_arch))

        self.cluster_settings_custom_resource = cdk.CustomResource(
            self.nested_stack,
            "cluster-manager-settings",
            service_token=self.cluster_stack.cluster_settings_lambda.function_arn,
            properties={
                "cluster_name": self.cluster_name,
                "module_id": self.module_id,
                "version": self.get_res_release_version(),
                "settings": cluster_settings,
            },
            resource_type="Custom::ClusterManagerSettings",
        )
        self.auto_scaling_group.node.add_dependency(  # type: ignore
            self.cluster_settings_custom_resource
        )

    def build_configure_sso_lambda(self) -> None:
        lambda_name = "configure_sso"

        self.configure_sso_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Lambda to configure SSO",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=configure_sso_handler.handler,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=ConfigureSSOLambdaPolicy.create_policy_statements(  # type: ignore
                self.arn_builder
            ),
            parameters=self.parameters,
            log_retention_role=self.cluster_stack.lambda_log_retention_role,  # type: ignore
            environment={ENVIRONMENT_NAME_KEY: self.cluster_name},
        )
