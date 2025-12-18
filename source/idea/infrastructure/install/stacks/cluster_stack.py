#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import uuid
from typing import Any, Dict, List, Optional, Union

import aws_cdk as cdk
import constructs
from aws_cdk import CfnCondition, Fn
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_s3 as s3
from res.constants import ENVIRONMENT_NAME_KEY, OLD_CUSTOM_TAG_KEYS  # type: ignore

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs import ec2, iam, lambda_, sns
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.customdomain import CustomDomainKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import (
    AddNatEipsToAlbSecurityGroupPolicy,
    AmazonSsmManagedInstanceCorePolicy,
    CloudWatchAgentServerPolicy,
    ClusterEndpointsPolicy,
    Ec2StateEventTransformerPolicy,
    GetAlbListenerDefaultActionsPolicy,
    LambdaBasicExecutionPolicy,
    LogRetentionPolicy,
    SelfSignedCertificatePolicy,
    UpdateClusterSettingsPolicy,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.add_ingress_rules_for_nat_eips_lambda import (
    add_ingress_rules_for_nat_eips_handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.cluster_endpoints_lambda import (
    cluster_endpoints_handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.get_alb_listener_default_actions_lambda import (
    get_alb_listener_default_actions_handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.self_signed_certificate_lambda import (
    self_signed_certificate_handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.update_cluster_settings_lambda import (
    update_cluster_settings_handler,
)
from idea.infrastructure.resources.lambda_functions.ec2_state_event_transformation_lambda import (
    ec2_state_event_transformation_handler,
)
from idea.infrastructure.resources.lambda_functions.solution_metrics_lambda import (
    solution_metrics_handler,
)


class ClusterStack(ResBaseConstruct):
    """
    Cluster Stack

    Provisions base infrastructure components for RES Environment:
    * Internal and External Load Balancers
    * Common IAM Roles and Security Groups
    * Self-signed Certificates (if applicable)
    * Route53 Private Hosted Zone
    * Common custom resource Lambda Functions
    * Cluster Prefix List
    * Cluster Settings
    """

    def __init__(
        self,
        scope: constructs.Construct,
        lambda_layer: cdk.aws_lambda.LayerVersion,
        params_transformer: cdk.CustomResource,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):

        self.parameters = parameters
        self.params_transformer = params_transformer
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.module_id = constants.MODULE_CLUSTER
        self.aws_region = cdk.Aws.REGION
        self.lambda_layer = lambda_layer

        super().__init__(
            scope,
            "cluster",
            self.cluster_name,
            parameters=parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "cluster",
            description=f"ModuleId: {self.module_id}, Version: {self.get_res_release_version()}",
        )
        self.add_common_tags(self.nested_stack)
        cdk.Tags.of(self.nested_stack).add(
            constants.RES_TAG_MODULE_NAME,
            constants.MODULE_CLUSTER,
            exclude_resource_types=["AWS::Events::Rule"],
        )
        cdk.Tags.of(self.nested_stack).add(
            constants.RES_TAG_MODULE_ID,
            constants.MODULE_CLUSTER,
            exclude_resource_types=["AWS::Events::Rule"],
        )

        self.has_iam_prefix_condition = InfraUtils.get_iam_prefix_condition(
            self.nested_stack, parameters
        )
        self.has_iam_path_condition = InfraUtils.get_iam_path_condition(
            self.nested_stack, parameters
        )

        self.cluster_settings = ClusterSettings(self.cluster_name, self.nested_stack)
        self.arn_builder = ArnBuilder(self.cluster_name, self.cluster_settings)

        self._existing_vpc: Optional[ec2.ExistingVpc] = None

        self.self_signed_certificate_lambda: Optional[lambda_.Function] = None
        self.external_certificate: Optional[cdk.CustomResource] = None
        self.internal_certificate: Optional[cdk.CustomResource] = None
        self.external_certificate_is_not_provided: Optional[CfnCondition] = None

        self.cluster_endpoints_lambda: Optional[lambda_.Function] = None
        self.get_alb_listener_default_actions_lambda: Optional[lambda_.Function] = None
        self.external_alb: Optional[elbv2.CfnLoadBalancer] = None
        self.external_alb_https_listener: Optional[elbv2.CfnListener] = None
        self.internal_alb: Optional[elbv2.CfnLoadBalancer] = None
        self.internal_alb_https_listener: Optional[elbv2.CfnListener] = None
        self.internal_alb_dcv_broker_client_listener: Optional[elbv2.CfnListener] = None
        self.internal_alb_dcv_broker_agent_listener: Optional[elbv2.CfnListener] = None
        self.internal_alb_dcv_broker_gateway_listener: Optional[elbv2.CfnListener] = (
            None
        )

        self.private_hosted_zone: Optional[route53.PrivateHostedZone] = None
        self.cluster_prefix_list: Optional[ec2.PrefixList] = None
        self.security_groups: Dict[str, ec2.SecurityGroup] = {}
        self.roles: Dict[str, iam.Role] = {}
        self.amazon_ssm_managed_instance_core_policy: Optional[iam.ManagedPolicy] = None
        self.cloud_watch_agent_server_policy: Optional[iam.ManagedPolicy] = None
        self.solution_metrics_lambda: Optional[lambda_.Function] = None
        self.ec2_events_sns_topic: Optional[sns.SNSTopic] = None

        # build common policies
        self.build_policies()

        # build roles
        self.build_roles()

        # build self-signed certificates lambda function
        self.build_self_signed_certificates_lambda()

        # self-signed certificates
        self.build_self_signed_certificates()

        # cluster settings lambda function
        self.build_cluster_settings_lambda()

        self.build_get_alb_listener_default_actions_lambda()

        # vpc
        self.build_vpc()

        # cluster prefix list
        self.build_cluster_prefix_list()

        # security groups
        self.build_security_groups()

        # setup private hosted zone
        self.build_private_hosted_zone()

        # ec2-notification module
        self.build_ec2_notification_module()

        # cluster endpoints
        self.build_cluster_endpoints()

        # solution metrics lambda function
        self.build_solution_metrics_lambda()

        # build outputs
        self.build_cluster_settings()

        self.nested_stack.node.add_dependency(self.lambda_layer)

        self.apply_permission_boundary(self.nested_stack)

    @property
    def vpc(self) -> cdk.aws_ec2.IVpc:
        return self._existing_vpc.vpc  # type: ignore

    def build_policies(self) -> None:
        self.amazon_ssm_managed_instance_core_policy = AmazonSsmManagedInstanceCorePolicy(
            self.nested_stack,
            description="The policy for Amazon EC2 Role to enable AWS Systems Manager service core functionality",
            name="amazon-ssm-managed-instance-core",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
        )

        self.cloud_watch_agent_server_policy = CloudWatchAgentServerPolicy(
            self.nested_stack,
            description="Permissions required to use AmazonCloudWatchAgent on servers",
            name="cloud-watch-agent-server-policy",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
        )

    def build_roles(self) -> None:
        self.lambda_log_retention_role = iam.Role(
            scope=self.nested_stack,
            name=constants.LOG_RETENTION_ROLE_NAME,
            description="log retention role for CDK custom resources",
            assumed_by=["lambda"],
            inline_policies=[
                LogRetentionPolicy(
                    self.nested_stack,
                    name="log-retention-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                )
            ],
            parameters=self.parameters,
            arn_builder=self.arn_builder,
        )
        self.roles[constants.LOG_RETENTION_ROLE_NAME] = self.lambda_log_retention_role

    def build_vpc(self) -> None:
        self._existing_vpc = ec2.ExistingVpc(
            name="existing-vpc",
            scope=self.nested_stack,
            lambda_layer=self.lambda_layer,
            arn_builder=self.arn_builder,
            parameters=self.parameters,
        )

    def build_private_hosted_zone(self) -> None:
        self.private_hosted_zone = route53.PrivateHostedZone(
            self.nested_stack,
            "private-hosted-zone",
            vpc=self._existing_vpc.vpc,  # type: ignore
            comment=f"Private Hosted Zone for IDEA Cluster: {self.cluster_name}",
            zone_name=self.cluster_settings.private_hosted_zone_name,  # type: ignore
        )

    def build_cluster_prefix_list(self) -> None:
        """
        cluster admins need an easy way to allow or deny additional IP addresses.

        instead of managing individual IP addresses in ec2.BastionHostec2.SecurityGroup, ExternalALBec2.SecurityGroup and DCVConnectionGatewayec2.SecurityGroup, the `cluster` prefix list provides
        a central place to manage access to cluster from the external world.

        for mature infrastructure deployments, where prefix lists already exist - cluster admins will provide prefix lists to access the cluster.  config key: `cluster.network.prefix_list_ids`

        for cluster deployments that provide IP address to access the cluster, the IP addresses will be automatically added to the new cluster prefix list. config key: `cluster.network.cluster_prefix_list_id`

        All applicable security groups will allow access from `cluster.network.prefix_list_ids[] + cluster.network.cluster_prefix_list_id`

        Note for existing resources:
        `cluster.network.cluster_prefix_list_id` will NOT be reused across clusters and each RES cluster will create a new cluster prefix list.
        cluster admins can provide their custom prefix lists as part of `cluster.network.prefix_list_ids` to be reused across clusters
        """
        self.cluster_prefix_list = ec2.PrefixList(
            scope=self.nested_stack,
            name="prefix-list",
            address_family="IPv4",
            max_entries=self.cluster_settings.cluster_prefix_list_max_entries,
            parameters=self.parameters,
        )

        custom_resource_update_cluster_prefix_list = ec2.UpdateClusterPrefixList(
            self.nested_stack,
            "update-cluster-prefix-list",
            self.cluster_prefix_list,  # type: ignore
            self.arn_builder,
            self.lambda_layer,
            self.parameters,
        )
        # do not create the custom resource if client_ip is not provided.
        custom_resource_update_cluster_prefix_list.apply_condition_aspect(
            CfnCondition(
                self.nested_stack,
                "has-client-ip",
                expression=Fn.condition_not(
                    Fn.condition_equals(
                        self.parameters.get_str(CommonKey.CLIENT_IP), ""
                    ),
                ),
            )
        )

    def build_security_groups(self) -> None:
        # default cluster security group
        cluster_security_group = ec2.SecurityGroup(
            scope=self.nested_stack,
            vpc=self.vpc,
            description="Default Cluster Security",
            name="default-security-group",
            parameters=self.parameters,
        )
        self.security_groups["cluster"] = cluster_security_group

        # bastion host
        bastion_host_security_group = ec2.BastionHostSecurityGroup(
            scope=self.nested_stack,
            vpc=self.vpc,
            cluster_prefix_list_id=self.cluster_prefix_list.attr_prefix_list_id,  # type: ignore
            name="bastion-host-security-group",
            parameters=self.parameters,
        )
        self.security_groups["bastion-host"] = bastion_host_security_group

        # external load balancer
        external_loadbalancer_security_group = ec2.ExternalLoadBalancerSecurityGroup(
            scope=self.nested_stack,
            name="external-load-balancer-security-group",
            vpc=self.vpc,
            bastion_host_security_group=bastion_host_security_group,
            cluster_prefix_list_id=self.cluster_prefix_list.attr_prefix_list_id,  # type: ignore
            parameters=self.parameters,
        )
        self.security_groups["external-load-balancer"] = (
            external_loadbalancer_security_group
        )

        add_prefix_list_peer_ingress_rule = ec2.AddPrefixListPeerIngressRule(
            self.nested_stack,
            "add-prefix-list-peer-ingress-rule",
            external_loadbalancer_security_group.security_group_id,
            bastion_host_security_group.security_group_id,
            self.arn_builder,
            self.lambda_layer,
            self.parameters,
        )
        add_prefix_list_peer_ingress_rule.apply_condition_aspect(
            CfnCondition(
                self.nested_stack,
                "has-prefix-list",
                expression=Fn.condition_not(
                    Fn.condition_equals(
                        self.parameters.get_str(CommonKey.CLIENT_PREFIX_LIST), ""
                    ),
                ),
            )
        )

        # internal load balancer
        internal_loadbalancer_security_group = ec2.InternalLoadBalancerSecurityGroup(
            name="internal-load-balancer-security-group",
            scope=self.nested_stack,
            vpc=self.vpc,
            parameters=self.parameters,
        )
        self.security_groups["internal-load-balancer"] = (
            internal_loadbalancer_security_group
        )

        lambda_name = "add-nat-eips-to-alb-sg"
        add_nat_eips_to_alb_sg_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Add NAT EIP to load balancer security group",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=add_ingress_rules_for_nat_eips_handler.handler,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=AddNatEipsToAlbSecurityGroupPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
        )

        add_nat_eips_to_alb_sg = cdk.CustomResource(
            self.nested_stack,
            "add-nat-eips-to-alb-sg",
            service_token=add_nat_eips_to_alb_sg_lambda.function_arn,
            properties={
                "subnet_ids": self.cluster_settings.load_balancer_subnets,
                "security_group_id": external_loadbalancer_security_group.security_group_id,
            },
            resource_type="Custom::AddNatEipsToAlbSecurityGroup",
        )
        add_nat_eips_to_alb_sg.node.add_dependency(add_nat_eips_to_alb_sg_lambda)

    def build_cluster_settings_lambda(self) -> None:
        lambda_name = "cluster-settings-lambda"
        self.cluster_settings_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Update cluster settings during cluster module deployment",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=update_cluster_settings_handler.handler,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=UpdateClusterSettingsPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
        )

    def build_solution_metrics_lambda(self) -> None:
        lambda_name = "solution-metrics"
        self.solution_metrics_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Send anonymous Metrics to AWS",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=solution_metrics_handler.handler,
            initial_policy=LambdaBasicExecutionPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
        )

    def build_self_signed_certificates_lambda(self) -> None:
        """
        build self-signed certificates lambda function to be used as a custom resource in downstream modules
        """
        lambda_name = "self-signed-certificate"
        self.self_signed_certificate_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Manage self-signed certificates for RES environment infrastructure",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=self_signed_certificate_handler.handler,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=SelfSignedCertificatePolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
            environment={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
            },
        )

    def build_self_signed_certificates(self) -> None:
        self.external_certificate_is_not_provided = CfnCondition(
            self.nested_stack,
            "external-cert-is-not-provided",
            expression=Fn.condition_equals(
                self.parameters.get_str(
                    CustomDomainKey.ACM_CERTIFICATE_ARN_FOR_WEB_APP
                ),
                "",
            ),
        )
        # create self-signed certificate for external ALB and NLB
        # all virtual desktop streaming traffic is routed via NLB
        # all API and Web Portal traffic is routed via ALB
        self.external_certificate = cdk.CustomResource(
            self.nested_stack,
            "external-cert",
            service_token=self.self_signed_certificate_lambda.function_arn,  # type: ignore
            properties={
                "domain_name": f"{self.cluster_name}.idea.default",
                "certificate_name": f"{self.cluster_name}-external",
                "create_acm_certificate": True,
                "kms_key_id": self.cluster_settings.kms_secretsmanager_key_id,
                "tags": {
                    "Name": f"{self.cluster_name} external alb certs",
                    "res:EnvironmentName": self.cluster_name,
                },
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::SelfSignedCertificateExternal",
        )
        self.external_certificate.node.add_dependency(
            self.self_signed_certificate_lambda
        )
        raw_external_certificate = self.external_certificate.node.default_child
        raw_external_certificate.cfn_options.condition = self.external_certificate_is_not_provided  # type: ignore

        # create self-signed certificate for internal ALB
        self.internal_certificate = cdk.CustomResource(
            self.nested_stack,
            "internal-cert",
            service_token=self.self_signed_certificate_lambda.function_arn,  # type: ignore
            properties={
                "domain_name": f"*.{self.cluster_settings.private_hosted_zone_name}",
                "certificate_name": f"{self.cluster_name}-internal",
                "create_acm_certificate": True,
                "kms_key_id": self.cluster_settings.kms_secretsmanager_key_id,
                "tags": {
                    "Name": f"{self.cluster_name} internal alb certs",
                    "res:EnvironmentName": self.cluster_name,
                },
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::SelfSignedCertificateInternal",
        )
        self.internal_certificate.node.add_dependency(
            self.self_signed_certificate_lambda
        )

    def build_get_alb_listener_default_actions_lambda(self) -> None:
        lambda_name = "get-default-actions"
        self.get_alb_listener_default_actions_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Get default actions of the listener",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=get_alb_listener_default_actions_handler.handler,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=GetAlbListenerDefaultActionsPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
        )

    def get_alb_listener_default_actions(
        self,
        listener_arn: str,
        listener_id: str,
    ) -> List[Any]:
        """
        ALB listener must be created with a default action.
        """
        get_alb_listener_default_actions = cdk.CustomResource(
            self.nested_stack,
            f"get-alb-listener-default-actions-{listener_id}",
            service_token=self.get_alb_listener_default_actions_lambda.function_arn,  # type: ignore
            properties={
                "listener_arn": listener_arn,
            },
            resource_type="Custom::GetDefaultActions",
        )
        get_alb_listener_default_actions.node.add_dependency(
            self.get_alb_listener_default_actions_lambda
        )

        return get_alb_listener_default_actions.get_att("default_actions")  # type: ignore

    def build_ec2_notification_module(self) -> None:
        self.ec2_events_sns_topic = sns.SNSTopic(
            scope=self.nested_stack,
            id_="ec2-state-change-sns-topic",
            display_name=f"{self.cluster_name}-{self.module_id}-ec2-state-change-sns-topic",
            topic_name=f"{self.module_id}-ec2-state-change-sns-topic",
            master_key=self.cluster_settings.kms_sns_key_id,
            parameters=self.parameters,
        )

        lambda_name = f"ec2-event-xformer"
        ec2_state_event_transformation_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Manage self-signed certificates for RES environment infrastructure",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=ec2_state_event_transformation_handler.handler,
            environment={
                "IDEA_EC2_STATE_SNS_TOPIC_ARN": self.ec2_events_sns_topic.topic_arn,
                "IDEA_CLUSTER_NAME_TAG_KEY": constants.RES_TAG_ENVIRONMENT_NAME,
                "IDEA_CLUSTER_NAME_TAG_VALUE": self.cluster_name,
                "IDEA_TAG_PREFIX": constants.RES_TAG_PREFIX,
            },
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=Ec2StateEventTransformerPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
        )

        ec2_monitoring_rule = events.Rule(
            scope=self.nested_stack,
            id="ec2-state-monitoring-rule",
            enabled=True,
            rule_name=f"{self.cluster_name}-{self.module_id}-ec2-state-monitoring-rule",
            description="Event Rule to monitor state changes on EC2 Instances",
            event_pattern=events.EventPattern(
                source=["aws.ec2"],
                detail_type=["EC2 Instance State-change Notification"],
                region=[cdk.Aws.REGION],
            ),
        )
        ec2_monitoring_rule.add_target(
            events_targets.LambdaFunction(ec2_state_event_transformation_lambda)
        )

    def build_cluster_endpoints(self) -> None:
        lambda_name = "cluster-endpoints"
        self.cluster_endpoints_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Manage cluster endpoints exposed via internal and external ALB",  # type: ignore
            timeout=cdk.Duration.seconds(600),  # type: ignore
            handler=cluster_endpoints_handler.handler,
            initial_policy=ClusterEndpointsPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            layers=[self.lambda_layer],  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
            environment={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
            },
        )

        # external ALB - can be deployed in public or private subnets
        is_external_alb_public = CfnCondition(
            self.nested_stack,
            "is-external-alb-public",
            expression=Fn.condition_equals(
                self.parameters.get_str(CommonKey.IS_LOAD_BALANCER_INTERNET_FACING),
                "true",
            ),
        )

        logging_s3_bucket = s3.Bucket.from_bucket_name(
            scope=self.nested_stack,
            id="logging-s3-bucket",
            bucket_name=self.cluster_settings.logging_bucket,  # type: ignore
        )

        external_load_balancer_attributes = (
            [
                {"key": "access_logs.s3.enabled", "value": "true"},
                # Manage Access Logs for external Application Load Balancer
                # https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html
                {
                    "key": "access_logs.s3.bucket",
                    "value": logging_s3_bucket.bucket_name,
                },
                {
                    "key": "access_logs.s3.prefix",
                    "value": f"logs/{self.module_id}/alb-access-logs/external-alb",
                },
                {"key": "routing.http2.enabled", "value": "true"},
                # Drop invalid headers from requests to the ALB as a security measure
                {
                    "key": "routing.http.drop_invalid_header_fields.enabled",
                    "value": "true",
                },
            ]
            if self.cluster_settings.external_alb_enable_access_log
            else [
                {"key": "access_logs.s3.enabled", "value": "false"},
                {"key": "routing.http2.enabled", "value": "true"},
                {
                    "key": "routing.http.drop_invalid_header_fields.enabled",
                    "value": "true",
                },
            ]
        )
        self.external_alb = elbv2.CfnLoadBalancer(
            self.nested_stack,
            "external-alb",
            name=f"{self.cluster_name}-external-alb",
            security_groups=[
                self.security_groups["external-load-balancer"].security_group_id
            ],
            load_balancer_attributes=external_load_balancer_attributes,
            subnets=self.cluster_settings.load_balancer_subnets,  # type: ignore
            scheme=Fn.condition_if(
                is_external_alb_public.logical_id,
                "internet-facing",
                "internal",
            ).to_string(),
            type="application",
        )

        # internal ALB - will always be deployed in private subnets
        # Manage Access Logs for internal Application Load Balancer
        internal_load_balancer_attributes = (
            [
                {"key": "access_logs.s3.enabled", "value": "true"},
                {
                    "key": "access_logs.s3.bucket",
                    "value": logging_s3_bucket.bucket_name,
                },
                {
                    "key": "access_logs.s3.prefix",
                    "value": f"logs/{self.module_id}/alb-access-logs/internal-alb",
                },
                {"key": "routing.http2.enabled", "value": "true"},
                {
                    "key": "routing.http.drop_invalid_header_fields.enabled",
                    "value": "true",
                },
            ]
            if self.cluster_settings.internal_alb_enable_access_log
            else [
                {"key": "access_logs.s3.enabled", "value": "false"},
                {"key": "routing.http2.enabled", "value": "true"},
                {
                    "key": "routing.http.drop_invalid_header_fields.enabled",
                    "value": "true",
                },
            ]
        )
        self.internal_alb = elbv2.CfnLoadBalancer(
            self.nested_stack,
            "internal-alb",
            name=f"{self.cluster_name}-internal-alb",
            security_groups=[
                self.security_groups["internal-load-balancer"].security_group_id
            ],
            load_balancer_attributes=internal_load_balancer_attributes,
            subnets=self.cluster_settings.infrastructure_host_subnets,  # type: ignore
            scheme="internal",
            type="application",
        )
        self.internal_alb.node.add_dependency(self.internal_certificate)

        elbv2.CfnListener(
            self.external_alb,
            "external-alb-http-listener",
            port=80,
            load_balancer_arn=self.external_alb.attr_load_balancer_arn,
            protocol="HTTP",
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type="redirect",
                    redirect_config=elbv2.CfnListener.RedirectConfigProperty(
                        host="#{host}",
                        path="/#{path}",
                        port="443",
                        protocol="HTTPS",
                        query="#{query}",
                        status_code="HTTP_301",
                    ),
                )
            ],
        )

        # ALB listener must be created with a default action.
        # after the cluster stack is deployed, the cluster manager stack can update the default action to point to web portal
        # to avoid replacing the default action set for web-portal, fetch the default actions if the listener exists
        external_acm_certificate_arn = Fn.condition_if(
            self.external_certificate_is_not_provided.logical_id,  # type: ignore
            self.external_certificate.get_att_string("acm_certificate_arn"),  # type: ignore
            self.parameters.get_str(CustomDomainKey.ACM_CERTIFICATE_ARN_FOR_WEB_APP),
        )

        self.external_alb_https_listener = elbv2.CfnListener(
            self.external_alb,
            "external-alb-https-listener",
            port=443,
            ssl_policy=self.cluster_settings.external_alb_ssl_policy,  # type: ignore
            load_balancer_arn=self.external_alb.attr_load_balancer_arn,
            protocol="HTTPS",
            certificates=[
                elbv2.CfnListener.CertificateProperty(
                    certificate_arn=external_acm_certificate_arn.to_string()
                )
            ],
            default_actions=self.get_alb_listener_default_actions(
                self.cluster_settings.external_alb_listener_arn,  # type: ignore
                "external-alb-https-listener",
            ),
        )

        internal_acm_certificate_arn = self.internal_certificate.get_att_string(  # type: ignore
            "acm_certificate_arn"
        )
        self.internal_alb_https_listener = elbv2.CfnListener(
            self.internal_alb,
            "internal-alb-https-listener",
            port=443,
            ssl_policy=self.cluster_settings.internal_alb_ssl_policy,  # type: ignore
            load_balancer_arn=self.internal_alb.attr_load_balancer_arn,
            protocol="HTTPS",
            certificates=[
                elbv2.CfnListener.CertificateProperty(
                    certificate_arn=internal_acm_certificate_arn
                )
            ],
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type="fixed-response",
                    fixed_response_config=elbv2.CfnListener.FixedResponseConfigProperty(
                        status_code="200",
                        content_type="application/json",
                        message_body=json.dumps(
                            {"success": True, "message": "OK"},
                            default=str,
                            separators=(",", ":"),
                        ),
                    ),
                )
            ],
        )
        self.internal_alb_https_listener.node.add_dependency(self.internal_certificate)

        cname_record = route53.CnameRecord(
            self.nested_stack,
            "internal-alb-dns-cname-record",
            record_name=f"internal-alb.{self.private_hosted_zone.zone_name}",  # type: ignore
            zone=self.private_hosted_zone,  # type: ignore
            domain_name=self.internal_alb.attr_dns_name,
            ttl=cdk.Duration.minutes(5),
        )
        raw_cname_record = cname_record.node.default_child
        raw_cname_record.cfn_options.condition = CfnCondition(  # type: ignore
            self.nested_stack,
            "region-in-route53-cross-zone-alias-restricted-region-list",
            expression=Fn.condition_or(
                *[
                    Fn.condition_equals(self.aws_region, region)
                    for region in constants.CAVEATS.get(
                        "ROUTE53_CROSS_ZONE_ALIAS_RESTRICTED_REGION_LIST", []
                    )
                ]
            ),
        )

        record_set = route53.CfnRecordSet(
            self.nested_stack,
            "internal-alb-dns-record-set",
            type="A",
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name=self.internal_alb.attr_dns_name,
                hosted_zone_id=self.internal_alb.attr_canonical_hosted_zone_id,
            ),
            name=f"internal-alb.{self.private_hosted_zone.zone_name}",  # type: ignore
            hosted_zone_id=self.private_hosted_zone.hosted_zone_id,  # type: ignore
        )
        record_set.cfn_options.condition = CfnCondition(
            self.nested_stack,
            "region-not-in-route53-cross-zone-alias-restricted-region-list",
            expression=Fn.condition_not(
                Fn.condition_or(
                    *[
                        Fn.condition_equals(self.aws_region, region)
                        for region in constants.CAVEATS.get(
                            "ROUTE53_CROSS_ZONE_ALIAS_RESTRICTED_REGION_LIST", []
                        )
                    ]
                ),
            ),
        )

        self.internal_alb_dcv_broker_client_listener = elbv2.CfnListener(
            self.internal_alb,
            "dcv-broker-client-listener",
            port=self.cluster_settings.dcv_broker_client_communication_port,
            ssl_policy=self.cluster_settings.dcv_broker_ssl_policy,  # type: ignore
            load_balancer_arn=self.internal_alb.attr_load_balancer_arn,
            protocol="HTTPS",
            certificates=[
                elbv2.CfnListener.CertificateProperty(
                    certificate_arn=internal_acm_certificate_arn
                )
            ],
            default_actions=self.get_alb_listener_default_actions(
                self.cluster_settings.dcv_broker_client_listener_arn,  # type: ignore
                "dcv-broker-client-listener",
            ),
        )
        self.internal_alb_dcv_broker_client_listener.node.add_dependency(
            self.internal_certificate
        )
        self.security_groups["internal-load-balancer"].add_ingress_rule(
            cdk.aws_ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            cdk.aws_ec2.Port.tcp(
                self.cluster_settings.dcv_broker_client_communication_port
            ),
            description="Allow HTTPS traffic from DCV Clients to DCV Broker",
        )

        self.internal_alb_dcv_broker_agent_listener = elbv2.CfnListener(
            self.internal_alb,
            "dcv-broker-agent-listener",
            port=self.cluster_settings.dcv_broker_agent_communication_port,
            ssl_policy=self.cluster_settings.dcv_broker_ssl_policy,  # type: ignore
            load_balancer_arn=self.internal_alb.attr_load_balancer_arn,
            protocol="HTTPS",
            certificates=[
                elbv2.CfnListener.CertificateProperty(
                    certificate_arn=internal_acm_certificate_arn
                )
            ],
            default_actions=self.get_alb_listener_default_actions(
                self.cluster_settings.dcv_broker_agent_listener_arn,  # type: ignore
                "dcv-broker-agent-listener",
            ),
        )
        self.internal_alb_dcv_broker_agent_listener.node.add_dependency(
            self.internal_certificate
        )
        self.security_groups["internal-load-balancer"].add_ingress_rule(
            cdk.aws_ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            cdk.aws_ec2.Port.tcp(
                self.cluster_settings.dcv_broker_agent_communication_port
            ),
            description="Allow HTTPS traffic from DCV Agents to DCV Broker",
        )

        self.internal_alb_dcv_broker_gateway_listener = elbv2.CfnListener(
            self.internal_alb,
            "dcv-broker-gateway-listener",
            port=self.cluster_settings.dcv_broker_gateway_communication_port,
            ssl_policy=self.cluster_settings.dcv_broker_ssl_policy,  # type: ignore
            load_balancer_arn=self.internal_alb.attr_load_balancer_arn,
            protocol="HTTPS",
            certificates=[
                elbv2.CfnListener.CertificateProperty(
                    certificate_arn=internal_acm_certificate_arn
                )
            ],
            default_actions=self.get_alb_listener_default_actions(
                self.cluster_settings.dcv_broker_gateway_listener_arn,  # type: ignore
                "dcv-broker-gateway-listener",
            ),
        )
        self.internal_alb_dcv_broker_gateway_listener.node.add_dependency(
            self.internal_certificate
        )
        self.security_groups["internal-load-balancer"].add_ingress_rule(
            cdk.aws_ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            cdk.aws_ec2.Port.tcp(
                self.cluster_settings.dcv_broker_gateway_communication_port
            ),
            description="Allow HTTPS traffic from DCV Connection Gateway to DCV Broker",
        )

    def build_cluster_settings(self) -> None:
        # cluster settings are applied in the current module_id scope. module_id should not be provided in the key for settings.
        cluster_settings = {
            "deployment_id": str(uuid.uuid4()),
            "network.vpc_id": self.vpc.vpc_id,
            "network.cluster_prefix_list_id": self.cluster_prefix_list.attr_prefix_list_id,  # type: ignore
        }

        # ec2.SecurityGroupIds
        for name, security_group in self.security_groups.items():
            cluster_settings[f"network.security_groups.{name}"] = (
                security_group.security_group_id
            )

        # RoleArns
        for name, role in self.roles.items():
            cluster_settings[f"iam.roles.{name}"] = role.role_arn

        # Policy Arns
        cluster_settings["iam.policies.amazon_ssm_managed_instance_core_arn"] = (
            self.amazon_ssm_managed_instance_core_policy.managed_policy_arn  # type: ignore
        )
        cluster_settings["iam.policies.cloud_watch_agent_server_arn"] = (
            self.cloud_watch_agent_server_policy.managed_policy_arn  # type: ignore
        )

        cluster_settings["solution.solution_metrics_lambda_arn"] = (
            self.solution_metrics_lambda.function_arn  # type: ignore
        )
        cluster_settings["cluster_settings_lambda_arn"] = (
            self.cluster_settings_lambda.function_arn
        )
        cluster_settings["self_signed_certificate_lambda_arn"] = (
            self.self_signed_certificate_lambda.function_arn  # type: ignore
        )

        # route53 - private hosted zone settings
        cluster_settings["route53.private_hosted_zone_id"] = (
            self.private_hosted_zone.hosted_zone_id  # type: ignore
        )
        cluster_settings["route53.private_hosted_zone_arn"] = (
            self.private_hosted_zone.hosted_zone_arn  # type: ignore
        )

        # certificates
        cluster_settings[
            "load_balancers.external_alb.certificates.certificate_secret_arn"
        ] = Fn.condition_if(
            self.external_certificate_is_not_provided.logical_id,  # type: ignore
            self.external_certificate.get_att_string(  # type: ignore
                "certificate_secret_arn"
            ),
            self.parameters.get_str(CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI),
        )
        cluster_settings[
            "load_balancers.external_alb.certificates.private_key_secret_arn"
        ] = Fn.condition_if(
            self.external_certificate_is_not_provided.logical_id,  # type: ignore
            self.external_certificate.get_att_string(  # type: ignore
                "private_key_secret_arn"
            ),
            self.parameters.get_str(CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI),
        )
        cluster_settings[
            "load_balancers.external_alb.certificates.acm_certificate_arn"
        ] = Fn.condition_if(
            self.external_certificate_is_not_provided.logical_id,  # type: ignore
            self.external_certificate.get_att_string(  # type: ignore
                "acm_certificate_arn"
            ),
            self.parameters.get_str(CustomDomainKey.ACM_CERTIFICATE_ARN_FOR_WEB_APP),
        )
        cluster_settings["load_balancers.external_alb.certificates.provided"] = (
            Fn.condition_if(
                self.external_certificate_is_not_provided.logical_id,  # type: ignore
                False,
                True,
            )
        )

        cluster_settings[
            "load_balancers.internal_alb.certificates.certificate_secret_arn"
        ] = self.internal_certificate.get_att_string(  # type: ignore
            "certificate_secret_arn"
        )
        cluster_settings[
            "load_balancers.internal_alb.certificates.private_key_secret_arn"
        ] = self.internal_certificate.get_att_string(  # type: ignore
            "private_key_secret_arn"
        )
        cluster_settings[
            "load_balancers.internal_alb.certificates.acm_certificate_arn"
        ] = self.internal_certificate.get_att_string(  # type: ignore
            "acm_certificate_arn"
        )
        cluster_settings["load_balancers.internal_alb.certificates.custom_dns_name"] = (
            f"internal-alb.{self.private_hosted_zone.zone_name}"  # type: ignore
        )

        # cluster endpoints
        cluster_settings["cluster_endpoints_lambda_arn"] = (
            self.cluster_endpoints_lambda.function_arn  # type: ignore
        )
        cluster_settings["load_balancers.external_alb.load_balancer_arn"] = (
            self.external_alb.attr_load_balancer_arn  # type: ignore
        )
        cluster_settings["load_balancers.external_alb.load_balancer_dns_name"] = (
            self.external_alb.attr_dns_name  # type: ignore
        )
        cluster_settings["load_balancers.external_alb.https_listener_arn"] = (
            self.external_alb_https_listener.attr_listener_arn  # type: ignore
        )

        cluster_settings["load_balancers.internal_alb.load_balancer_arn"] = (
            self.internal_alb.attr_load_balancer_arn  # type: ignore
        )
        cluster_settings["load_balancers.internal_alb.load_balancer_dns_name"] = (
            self.internal_alb.attr_dns_name  # type: ignore
        )
        cluster_settings["load_balancers.internal_alb.https_listener_arn"] = (
            self.internal_alb_https_listener.attr_listener_arn  # type: ignore
        )

        cluster_settings["ec2.state_change_notifications_sns_topic_arn"] = (
            self.ec2_events_sns_topic.topic_arn  # type: ignore
        )
        cluster_settings["ec2.state_change_notifications_sns_topic_name"] = (
            self.ec2_events_sns_topic.topic_name  # type: ignore
        )

        cluster_settings[
            "load_balancers.internal_alb.dcv_broker_client_listener_arn"
        ] = self.internal_alb_dcv_broker_client_listener.attr_listener_arn  # type: ignore
        cluster_settings[
            "load_balancers.internal_alb.dcv_broker_agent_listener_arn"
        ] = self.internal_alb_dcv_broker_agent_listener.attr_listener_arn  # type: ignore
        cluster_settings[
            "load_balancers.internal_alb.dcv_broker_gateway_listener_arn"
        ] = self.internal_alb_dcv_broker_gateway_listener.attr_listener_arn  # type: ignore

        cdk.CustomResource(
            self.nested_stack,
            "cluster-settings",
            service_token=self.cluster_settings_lambda.function_arn,
            properties={
                "cluster_name": self.cluster_name,
                "module_id": self.module_id,
                "version": self.get_res_release_version(),
                "settings": cluster_settings,
            },
            resource_type="Custom::ClusterSettings",
        )
