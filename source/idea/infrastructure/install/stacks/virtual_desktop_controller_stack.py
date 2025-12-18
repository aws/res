#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import uuid
from typing import Any, List, Optional, Union

import aws_cdk as cdk
import constructs
from aws_cdk import CfnCondition, Fn, RemovalPolicy
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_autoscaling as asg
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as sns_subscription
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_events import Schedule
from res.constants import OLD_CUSTOM_TAG_KEYS  # type: ignore
from res.utils.bootstrap_userdata_builder import (  # type: ignore
    BootstrapUserDataBuilder,
)

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs import ec2, iam, lambda_, secretmanager
from idea.infrastructure.install.constructs import sns as sns_
from idea.infrastructure.install.constructs import sqs as sqs_
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.infra_utils.vdc_settings import VdcSettings
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.customdomain import CustomDomainKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import (
    AddToUserpoolClientScopesPolicy,
    ControllerScheduledEventTransformerLambdaPolicy,
    ControllerSSMCommandPassRolePolicy,
    CustomCredentialBrokerPolicy,
    S3MountBaseBucketReadOnlyPolicy,
    S3MountBaseBucketReadWritePolicy,
    VdcControllerSqsKmsKeyPolicy,
    VdiHelperPolicy,
    VirtualDesktopBrokerPolicy,
    VirtualDesktopConnectionGatewayPolicy,
    VirtualDesktopControllerPolicy,
    VirtualDesktopDcvHostScopedDownPolicy,
    VirtualDesktopDcvPolicy,
)
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.install.stacks.identity_stack import IdentityStack
from idea.infrastructure.resources.lambda_functions.custom_resource.add_to_user_pool_client_scopes_lambda import (
    add_to_user_pool_client_scopes_handler,
)
from idea.infrastructure.resources.lambda_functions.scheduled_event_transformer_lambda import (
    scheduled_event_transformer_handler,
)
from idea.infrastructure.resources.lambda_functions_with_utils.custom_credential_broker_lambda import (
    custom_credential_broker_handler,
)
from idea.infrastructure.resources.lambda_functions_with_utils.vdi_helper_lambda import (
    handler as vdi_helper_handler,
)


class VirtualDesktopControllerStack(ResBaseConstruct):
    """
    Virtual Desktop Controller (eVDI) Stack

    Provisions infrastructure for eVDI Module:
    * ASG for Controller, NICE DCV Broker, NICE DCV Connection Gateway
    * Network Load Balancer
    * Security Groups
    * AWS Backups for eVDI Hosts
    * Additional components for eVDI functionality.
    """

    def __init__(
        self,
        scope: constructs.Construct,
        lambda_layer: cdk.aws_lambda.LayerVersion,
        cluster_stack: ClusterStack,
        identity_stack: IdentityStack,
        params_transformer: cdk.CustomResource,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):

        self.parameters = parameters
        self.params_transformer = params_transformer
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.module_id = constants.MODULE_ID_VDC_CONTROLLER
        self.aws_region = cdk.Aws.REGION
        self.lambda_layer = lambda_layer
        self.cluster_stack = cluster_stack
        self.identity_stack = identity_stack
        self.deployment_id = str(uuid.uuid4())

        super().__init__(
            scope,
            "vdc",
            self.cluster_name,
            parameters=parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "vdc",
            description=f"ModuleId: {self.module_id}, Version: {self.get_res_release_version()}",
        )
        self.add_common_tags(self.nested_stack)
        cdk.Tags.of(self.nested_stack).add(
            constants.RES_TAG_MODULE_NAME,
            constants.MODULE_NAME_VDC_CONTROLLER,
            exclude_resource_types=["AWS::Events::Rule"],
        )
        cdk.Tags.of(self.nested_stack).add(
            constants.RES_TAG_MODULE_ID,
            constants.MODULE_ID_VDC_CONTROLLER,
            exclude_resource_types=["AWS::Events::Rule"],
        )

        self.has_iam_prefix_condition = InfraUtils.get_iam_prefix_condition(
            self.nested_stack, parameters
        )
        self.has_iam_path_condition = InfraUtils.get_iam_path_condition(
            self.nested_stack, parameters
        )

        self.certificate_arn_provided = CfnCondition(
            self.nested_stack,
            "vdi-cert-provided",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    self.parameters.get_str(
                        CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI
                    ),
                    "",
                )
            ),
        )

        self.private_key_arn_provided = CfnCondition(
            self.nested_stack,
            "vdi-private-key-provided",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    self.parameters.get_str(
                        CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI
                    ),
                    "",
                )
            ),
        )

        self.prefix_list_provided = CfnCondition(
            self.nested_stack,
            "client-prefix-list-provided",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    self.parameters.get_str(CommonKey.CLIENT_PREFIX_LIST),
                    "",
                )
            ),
        )

        self.certificate_all_provided = CfnCondition(
            self.nested_stack,
            "vdi-cert-all-provided",
            expression=Fn.condition_and(
                self.certificate_arn_provided.expression,  # type: ignore
                self.private_key_arn_provided.expression,  # type: ignore
            ),
        )

        self.bastion_host_security_group = self.cluster_stack.security_groups[
            "bastion-host"
        ]
        self.external_loadbalancer_security_group = self.cluster_stack.security_groups[
            "external-load-balancer"
        ]
        self.cluster_settings = ClusterSettings(self.cluster_name, self.nested_stack)
        self.vdc_settings = VdcSettings(self.cluster_name, self.nested_stack)
        self.arn_builder = ArnBuilder(
            self.cluster_name, self.cluster_settings, self.parameters
        )

        self.COMPONENT_DCV_BROKER = "broker"
        self.COMPONENT_DCV_CONNECTION_GATEWAY = "gateway"
        self.COMPONENT_CONTROLLER = "controller"
        self.CONFIG_MAPPING = {
            self.COMPONENT_CONTROLLER: "controller",
            self.COMPONENT_DCV_CONNECTION_GATEWAY: "dcv_connection_gateway",
            self.COMPONENT_DCV_BROKER: "dcv_broker",
        }
        self.COMPONENT_DCV_HOST = "host"

        self.PROXY_CONFIG = {
            "http_proxy": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
            "https_proxy": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
            "no_proxy": self.parameters.get_str(InternetProxyKey.NO_PROXY),
        }

        self.BROKER_CLIENT_COMMUNICATION_PORT = (
            self.cluster_settings.dcv_broker_client_communication_port
        )
        self.BROKER_AGENT_COMMUNICATION_PORT = (
            self.cluster_settings.dcv_broker_agent_communication_port
        )
        self.BROKER_GATEWAY_COMMUNICATION_PORT = (
            self.cluster_settings.dcv_broker_gateway_communication_port
        )

        self.CLUSTER_ENDPOINTS_LAMBDA_ARN = (
            self.cluster_stack.cluster_endpoints_lambda.function_arn  # type: ignore
        )

        self._existing_vpc: Optional[ec2.ExistingVpc] = None

        self.oauth2_client_secret: Optional[secretmanager.OAuthClient] = None
        self.custom_broker_secret: Optional[aws_secretsmanager.Secret] = None

        self.custom_credential_broker_lambda_function: Optional[lambda_.Function] = None
        self.custom_credential_broker_api_gateway_rest_api: Optional[
            apigateway.RestApi
        ] = None
        self.custom_credential_broker_lambda_role: Optional[iam.Role] = None
        self.s3_mount_base_bucket_read_only_role: Optional[iam.Role] = None
        self.s3_mount_base_bucket_read_write_role: Optional[iam.Role] = None

        self.api_gateway_vpc_endpoint: Optional[ec2.VpcInterfaceEndpoint] = None
        self.vdi_helper_api_gateway_rest_api: Optional[apigateway.RestApi] = None
        self.vdi_helper_lambda_function: Optional[lambda_.Function] = None

        self.dcv_host_role: Optional[iam.Role] = None
        self.dcv_host_role_scoped_down_managed_policy: Optional[iam.ManagedPolicy] = (
            None
        )
        self.dcv_host_role_scoped_down: Optional[iam.Role] = None

        self.controller_role: Optional[iam.Role] = None
        self.dcv_broker_role: Optional[iam.Role] = None
        self.scheduled_event_transformer_lambda_role: Optional[iam.Role] = None

        self.dcv_host_instance_profile: Optional[iam.InstanceProfile] = None
        self.dcv_host_scoped_down_instance_profile: Optional[iam.InstanceProfile] = None

        self.dcv_host_security_group: Optional[
            ec2.VirtualDesktopBastionAccessSecurityGroup
        ] = None
        self.controller_security_group: Optional[
            ec2.VirtualDesktopPublicLoadBalancerAccessSecurityGroup
        ] = None
        self.dcv_connection_gateway_security_group: Optional[
            ec2.VirtualDesktopPublicLoadBalancerAccessSecurityGroup
        ] = None
        self.dcv_broker_security_group: Optional[
            ec2.VirtualDesktopBastionAccessSecurityGroup
        ] = None
        self.dcv_broker_alb_security_group: Optional[
            ec2.VirtualDesktopBastionAccessSecurityGroup
        ] = None

        self.dcv_connection_gateway_self_signed_cert: Optional[cdk.CustomResource] = (
            None
        )
        self.external_nlb: Optional[elbv2.CfnLoadBalancer] = None

        self.event_sqs_queue: Optional[sqs_.SQSQueue] = None
        self.controller_sqs_queue: Optional[sqs_.SQSQueue] = None
        self.ssm_commands_sns_topic: Optional[sns_.SNSTopic] = None
        self.ssm_command_pass_role: Optional[iam.Role] = None

        self.controller_auto_scaling_group: Optional[asg.AutoScalingGroup] = None
        self.dcv_broker_autoscaling_group: Optional[asg.AutoScalingGroup] = None
        self.dcv_connection_gateway_autoscaling_group: Optional[
            asg.AutoScalingGroup
        ] = None
        self.client_target_group: Optional[elbv2.ApplicationTargetGroup] = None

        self.user_pool = cognito.UserPool.from_user_pool_id(
            self.nested_stack,
            f"{self.module_id}-get-user-pool",
            self.cluster_settings.user_pool_id,  # type: ignore
        )

        self.resource_server = None

        self.build_vpc()

        self.build_oauth2_client()
        self.build_custom_broker_bootstrap_token_secret()
        self.update_cluster_manager_client_scopes()

        self.build_api_gateway_vpc_endpoint()
        self.build_custom_credential_broker_infra()
        self.build_vdi_helper_infra()

        self.build_sqs_queues()
        self.build_scheduled_event_notification_infra()
        self.subscribe_to_ec2_notification_events()

        self.build_virtual_desktop_controller()
        self.build_dcv_broker()
        self.build_dcv_connection_gateway()
        self.build_dcv_host_infra_scoped_down()
        self.build_dcv_host_infra()

        self.build_controller_ssm_commands_notification_infra()

        self.setup_egress_rules_for_quic()
        self.build_cluster_settings()

        self.nested_stack.node.add_dependency(self.lambda_layer)
        self.apply_permission_boundary(self.nested_stack)

    @property
    def vpc(self) -> cdk.aws_ec2.IVpc:
        return self._existing_vpc.vpc  # type: ignore

    @property
    def vdi_subnet_cidr_blocks(self) -> List[str]:
        return self._existing_vpc.vdi_subnet_cidr_blocks  # type: ignore

    def build_vpc(self) -> None:
        self._existing_vpc = ec2.ExistingVpc(
            name=f"{self.module_id}-existing-vpc",
            scope=self.nested_stack,
            lambda_layer=self.lambda_layer,
            arn_builder=self.arn_builder,
            parameters=self.parameters,
        )

    def build_custom_broker_bootstrap_token_secret(self) -> None:
        generate_secret_string = aws_secretsmanager.SecretStringGenerator(
            exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\@",
            include_space=False,
            password_length=32,
        )

        self.custom_broker_secret = aws_secretsmanager.Secret(
            self.nested_stack,
            id=f"{self.module_id}-custom-credential-broker-secret",
            description="Custom credential broker secret used for generating JWT bootstrap token",
            secret_name=f"{self.cluster_name}-custom-credential-broker-secret",
            generate_secret_string=generate_secret_string,
        )

    def setup_egress_rules_for_quic(self) -> None:
        quic_supported = self.vdc_settings.quic_support
        if not quic_supported:
            return

        self.dcv_host_security_group.add_egress_rule(  # type: ignore
            aws_ec2.Peer.ipv4("0.0.0.0/0"),
            aws_ec2.Port.udp_range(0, 65535),
            description="Allow all egress for UDP for QUIC Support on DCV Host",
        )

        self.dcv_connection_gateway_security_group.add_egress_rule(  # type: ignore
            aws_ec2.Peer.ipv4("0.0.0.0/0"),
            aws_ec2.Port.udp_range(0, 65535),
            description="Allow all egress for UDP for QUIC Support on DCV Connection Gateway",
        )

    def build_sqs_queues(self) -> None:
        # a custom kms key is required for sqs so that sns can be given permissions as an event source for the vdc controller queue
        sqs_kms_key_policy = aws_iam.PolicyDocument(
            statements=VdcControllerSqsKmsKeyPolicy.create_policy_statements(
                self.arn_builder
            )
        )

        self.sqs_kms_key = kms.Key(
            self.nested_stack,
            "res-sqs-kms",
            enable_key_rotation=True,
            policy=sqs_kms_key_policy,
        )
        self.sqs_kms_key.add_alias(f"alias/{self.cluster_name}/sqs")
        sqs_kms_key_id = self.cluster_settings.kms_sqs_key_id

        self.event_sqs_queue = sqs_.SQSQueue(
            f"{self.module_id}-events",
            self.nested_stack,
            self.arn_builder,
            self.parameters,
            fifo_throughput_limit=sqs.FifoThroughputLimit.PER_MESSAGE_GROUP_ID,
            fifo=True,
            deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
            content_based_deduplication=True,
            encryption_master_key=sqs_kms_key_id,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=60,
                queue=sqs_.SQSQueue(
                    f"{self.module_id}-events-dlq",
                    self.nested_stack,
                    self.arn_builder,
                    self.parameters,
                    fifo_throughput_limit=sqs.FifoThroughputLimit.PER_MESSAGE_GROUP_ID,
                    fifo=True,
                    deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
                    content_based_deduplication=True,
                    encryption_master_key=sqs_kms_key_id,
                ),
            ),
        )

        self.controller_sqs_queue = sqs_.SQSQueue(
            f"{self.module_id}-controller",
            self.nested_stack,
            self.arn_builder,
            self.parameters,
            encryption_master_key=self.sqs_kms_key.key_id,
            fifo=False,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=30,
                queue=sqs_.SQSQueue(
                    f"{self.module_id}-controller-dlq",
                    self.nested_stack,
                    self.arn_builder,
                    self.parameters,
                    encryption_master_key=self.sqs_kms_key.key_id,
                    fifo=False,
                ),
            ),
        )

    def build_controller_ssm_commands_notification_infra(self) -> None:
        self.ssm_command_pass_role = iam.Role(
            scope=self.nested_stack,
            name=f"{self.module_id}-ssm-commands-sns-topic-role",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
            assumed_by=["ssm"],
            description="IAM role for SSM Commands to send notifications via SNS",
            inline_policies=[
                ControllerSSMCommandPassRolePolicy(
                    self.nested_stack,
                    name=f"{self.module_id}-ssm-commands-sns-topic-role-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                )
            ],
        )

        self.ssm_command_pass_role.grant_pass_role(self.controller_role)  # type: ignore

        self.ssm_commands_sns_topic = sns_.SNSTopic(
            self.nested_stack,
            id_="virtual-desktop-controller-sns-topic",
            parameters=self.parameters,
            display_name=f"{self.cluster_name}-{self.module_id}-ssm-commands-topic",
            topic_name=f"{self.module_id}-ssm-commands-sns-topic",
            master_key=self.cluster_settings.kms_sns_key_id,
        )
        self.ssm_commands_sns_topic.add_subscription(
            sns_subscription.SqsSubscription(
                queue=self.controller_sqs_queue,  # type: ignore
                dead_letter_queue=self.controller_sqs_queue.dead_letter_queue.queue,  # type: ignore
            )
        )

    def subscribe_to_ec2_notification_events(self) -> None:
        ec2_event_sns_topic = self.cluster_stack.ec2_events_sns_topic
        ec2_event_sns_topic.add_subscription(  # type: ignore
            sns_subscription.SqsSubscription(
                queue=self.controller_sqs_queue,  # type: ignore
                dead_letter_queue=self.controller_sqs_queue.dead_letter_queue.queue,  # type: ignore
                filter_policy={
                    constants.RES_TAG_MODULE_ID.replace(
                        ":", "_"
                    ): sns.SubscriptionFilter.string_filter(allowlist=[self.module_id])
                },
            )
        )

    def build_scheduled_event_notification_infra(self) -> None:
        lambda_name = f"{self.module_id}-scheduled-event-transformer"
        self.scheduled_event_transformer_lambda_role = iam.Role(
            scope=self.nested_stack,
            name=f"{lambda_name}-role",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
            assumed_by=["lambda"],
            description=f"{lambda_name}-role",
            inline_policies=[
                ControllerScheduledEventTransformerLambdaPolicy(
                    self.nested_stack,
                    name=f"{lambda_name}-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                )
            ],
        )

        scheduled_event_transformer_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            handler=scheduled_event_transformer_handler.handler,
            parameters=self.parameters,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description=f"{self.module_id} lambda to intercept all scheduled events and transform to the required event object.",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            layers=[self.lambda_layer],  # type: ignore
            environment={
                "IDEA_CONTROLLER_EVENTS_QUEUE_URL": self.event_sqs_queue.queue_url  # type: ignore
            },
            role=self.scheduled_event_transformer_lambda_role,  # type: ignore
        )

        schedule_trigger_rule = events.Rule(
            scope=self.nested_stack,
            id=f"{self.module_id}-schedule-rule",
            enabled=True,
            rule_name=f"{self.cluster_name}-{self.module_id}-schedule-rule",
            description="Event Rule to Trigger schedule check EVERY 30 minutes on VDC Controller",
            schedule=Schedule.cron(minute="0/30"),
        )

        schedule_trigger_rule.add_target(
            events_targets.LambdaFunction(scheduled_event_transformer_lambda)
        )

    def build_oauth2_client(self) -> None:

        # add resource server
        self.resource_server = self.user_pool.add_resource_server(  # type: ignore
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

        # dcv session manager / external auth
        # refer: https://docs.aws.amazon.com/dcv/latest/sm-admin/ext-auth.html
        # todo - make an api call to check if "dcv-session-manager" resource server already exists in user pool
        #  this is to cover cases for blue/green deployments when an additional instance of eVDI module is deployed
        session_manager_resource_server = self.user_pool.add_resource_server(
            id="dcv-session-manager-resource-server",
            identifier=f"{self.cluster_name}-dcv-session-manager",
            scopes=[
                cognito.ResourceServerScope(
                    scope_name="sm_scope", scope_description="sm_scope"
                )
            ],
        )

        # add new client to user pool
        client = self.user_pool.add_client(
            id=f"{self.module_id}-client",
            access_token_validity=cdk.Duration.hours(1),
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
                    cognito.OAuthScope.custom(
                        f"{self.cluster_name}-{constants.MODULE_CLUSTER_MANAGER}/read"
                    ),
                    cognito.OAuthScope.custom(
                        f"{self.cluster_name}-dcv-session-manager/sm_scope"
                    ),
                ],
            ),
            refresh_token_validity=cdk.Duration.days(30),
            user_pool_client_name=f"{self.cluster_name}-{self.module_id}",
        )
        client.node.add_dependency(session_manager_resource_server)
        client.node.add_dependency(self.resource_server)

        # read secret value by invoking custom resource
        oauth_credentials_lambda_arn = (
            self.identity_stack.oauth_credentials_lambda.function_arn
        )
        client_secret = cdk.CustomResource(
            scope=self.nested_stack,
            id=f"{self.module_id}-creds",
            service_token=oauth_credentials_lambda_arn,
            properties={
                "UserPoolId": self.user_pool.user_pool_id,
                "ClientId": client.user_pool_client_id,
            },
            resource_type="Custom::GetOAuthCredentials",
        )

        # save client id and client secret to AWS Secrets Manager
        self.oauth2_client_secret = secretmanager.OAuthClient(
            scope=self.nested_stack,
            name=self.module_id,
            parameters=self.parameters,
            module_name=constants.MODULE_NAME_VDC_CONTROLLER,
            kms_key_id=self.cluster_settings.kms_secretsmanager_key_id,
            client_id=client.user_pool_client_id,
            client_secret=client_secret.get_att_string("ClientSecret"),
        )

    def update_cluster_manager_client_scopes(self) -> None:
        """
        Allow the cluster manager client to access VDC APIs via the VDC scopes
        :return:
        """
        lambda_name = f"{self.module_id}-update-cm-client-scope"
        update_cluster_manager_client_scope_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            handler=add_to_user_pool_client_scopes_handler.handler,
            parameters=self.parameters,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Update cluster manager client scope for accessing vdc",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=AddToUserpoolClientScopesPolicy.create_policy_statements(self.arn_builder),  # type: ignore
        )
        update_cluster_manager_client_scope_lambda.node.add_dependency(
            self.resource_server
        )

        cdk.CustomResource(
            self.nested_stack,
            lambda_name,
            service_token=update_cluster_manager_client_scope_lambda.function_arn,
            properties={
                "cluster_name": self.cluster_name,
                "module_id": constants.MODULE_CLUSTER_MANAGER,
                "user_pool_id": self.user_pool.user_pool_id,
                "o_auth_scopes_to_add": [
                    f"{self.cluster_name}-{constants.MODULE_ID_VDC_CONTROLLER}/read",
                    f"{self.cluster_name}-{constants.MODULE_ID_VDC_CONTROLLER}/write",
                ],
            },
            resource_type="Custom::UpdateClusterManagerClient",
        )

    def build_api_gateway_vpc_endpoint(self) -> None:
        api_gateway_vpc_endpoint_security_group = ec2.VpcEndpointSecurityGroup(
            scope=self.nested_stack,
            vpc=self.vpc,
            name="API Gateway VPC Endpoint Security Group",
            parameters=self.parameters,
        )

        self.api_gateway_vpc_endpoint = ec2.VpcInterfaceEndpoint(
            scope=self.nested_stack,
            name="execute-api",
            vpc=self.vpc,
            arn_builder=self.arn_builder,
            parameters=self.parameters,
            vpc_endpoint_security_group=api_gateway_vpc_endpoint_security_group,
            lookup_supported_azs=False,
            private_dns_enabled=False,
        )

    def build_custom_credential_broker_infra(self) -> None:
        lambda_name = f"{self.module_id}-custom-credential-broker-lambda"
        api_gateway_name = f"{self.module_id}-custom-credential-broker-api-gateway"

        self.custom_credential_broker_lambda_role = iam.Role(
            scope=self.nested_stack,
            name=f"{lambda_name}-role",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
            assumed_by=["lambda"],
            description=f"{lambda_name}-role",
        )

        secret_access_policy = aws_iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[self.custom_broker_secret.secret_arn],  # type: ignore
        )

        self.custom_credential_broker_lambda_role.add_to_policy(secret_access_policy)

        self.s3_mount_base_bucket_read_only_role = iam.Role(
            scope=self.nested_stack,
            name="s3-mount-bucket-read-only",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
            description="Base bucket role for read only access to S3 buckets onboarded to RES.",
            assumed_by=["lambda"],
            inline_policies=[
                S3MountBaseBucketReadOnlyPolicy(
                    self.nested_stack,
                    name="s3-mount-read-only-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                )
            ],
        )
        self.s3_mount_base_bucket_read_write_role = iam.Role(
            scope=self.nested_stack,
            name="s3-mount-bucket-read-write",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
            description="Base bucket role for read and write access to S3 buckets onboarded to RES.",
            assumed_by=["lambda"],
            inline_policies=[
                S3MountBaseBucketReadWritePolicy(
                    self.nested_stack,
                    name="s3-mount-read-write-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                )
            ],
        )
        self.s3_mount_base_bucket_read_only_role.assume_role_policy.add_statements(  # type: ignore
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["sts:AssumeRole"],
                principals=[
                    aws_iam.ArnPrincipal(
                        self.custom_credential_broker_lambda_role.role_arn
                    )
                ],
            )
        )
        self.s3_mount_base_bucket_read_write_role.assume_role_policy.add_statements(  # type: ignore
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["sts:AssumeRole"],
                principals=[
                    aws_iam.ArnPrincipal(
                        self.custom_credential_broker_lambda_role.role_arn
                    )
                ],
            )
        )
        custom_credential_broker_lambda_role_policy = CustomCredentialBrokerPolicy(
            self.nested_stack,
            description="Required policy for RES Custom Credential Broker Lambda.",
            name=f"{lambda_name}-policy",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
        )
        self.custom_credential_broker_lambda_role.add_managed_policy(
            custom_credential_broker_lambda_role_policy
        )

        custom_credential_broker_security_group = (
            ec2.VirtualDesktopCustomCredentialBrokerSecurityGroup(
                name=f"{lambda_name}-security-group",
                scope=self.nested_stack,
                vpc=self.vpc,
                component_name="Custom Credential Broker",
                parameters=self.parameters,
            )
        )

        self.custom_credential_broker_lambda_function = lambda_.Function(
            self.nested_stack,
            lambda_name,
            handler="custom_credential_broker_lambda.custom_credential_broker_handler.handler",
            code_directory_string=os.path.join(
                InfraUtils.lambda_functions_with_utils_dir()
            ),
            parameters=self.parameters,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description=f"{self.module_id} lambda to provide temporary credentials for mounting object storage to virtual desktop infrastructure (VDI) instances.",  # type: ignore
            timeout=cdk.Duration.seconds(60),  # type: ignore
            layers=[self.lambda_layer],  # type: ignore
            environment={
                "CLUSTER_NAME": f"{self.cluster_name}",
                "CLUSTER_SETTINGS_TABLE_NAME": f"{self.cluster_name}.cluster-settings",
                "DCV_HOST_DB_HASH_KEY": "instance_id",
                "DCV_HOST_DB_IDEA_SESSION_ID_KEY": "idea_session_id",
                "DCV_HOST_DB_IDEA_SESSION_OWNER_KEY": "idea_session_owner",
                "MODULE_ID": f"{self.module_id}",
                "OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX": constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX,
                "OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX": constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX,
                "OBJECT_STORAGE_NO_CUSTOM_PREFIX": constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX,
                "READ_AND_WRITE_ROLE_NAME_ARN": self.arn_builder.get_iam_arn(
                    "s3-mount-bucket-read-write"
                ),
                "READ_ONLY_ROLE_NAME_ARN": self.arn_builder.get_iam_arn(
                    "s3-mount-bucket-read-only"
                ),
                "SHARED_STORAGE_PREFIX": f"{constants.MODULE_SHARED_STORAGE}",
                "STORAGE_PROVIDER_S3_BUCKET": constants.STORAGE_PROVIDER_S3_BUCKET,
                "USER_SESSION_OWNER_KEY": "owner",
                "USER_SESSION_SESSION_ID_KEY": "idea_session_id",
                "HTTP_PROXY": self.parameters.get_str(InternetProxyKey.HTTP_PROXY),
                "HTTPS_PROXY": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
                "NO_PROXY": self.parameters.get_str(InternetProxyKey.NO_PROXY),
            },
            role=self.custom_credential_broker_lambda_role,  # type: ignore
            vpc=self.vpc,  # type: ignore
            security_groups=[custom_credential_broker_security_group],  # type: ignore
        )
        cfn_custom_credential_broker_lambda: aws_lambda.CfnFunction = (
            self.custom_credential_broker_lambda_function.node.default_child  # type: ignore
        )
        cfn_custom_credential_broker_lambda.add_property_override(
            "VpcConfig.SubnetIds",
            self.cluster_settings.infrastructure_host_subnets,
        )

        self.custom_credential_broker_api_gateway_rest_api = self._build_private_api_for_lambda(
            lambda_function=self.custom_credential_broker_lambda_function,
            api_name=api_gateway_name,
            resource_name=constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE,
            stage_name=constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_STAGE,
            api_description=f"{self.module_id} API Gateway for custom credential broker",
            http_method="GET",
            cidr_blocks=self.vdi_subnet_cidr_blocks,
        )

        self.custom_credential_broker_api_gateway_rest_api.node.add_dependency(
            self.custom_credential_broker_lambda_function
        )

    def build_vdi_helper_infra(self) -> None:
        lambda_name = f"{self.module_id}-vdi-helper-lambda"
        api_gateway_name = f"{self.module_id}-vdi-helper-api-gateway"

        vdi_helper_lambda_role_policy = VdiHelperPolicy(
            self.nested_stack,
            description="Required policy for RES VDI Helper Lambda.",
            name=f"{lambda_name}-policy",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
        )

        vdi_helper_lambda_role = iam.Role(
            scope=self.nested_stack,
            name=f"{lambda_name}-role",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
            assumed_by=["lambda"],
            description=f"{lambda_name}-role",
            managed_policies=[vdi_helper_lambda_role_policy],
        )
        self.vdi_helper_lambda_role_role_id = vdi_helper_lambda_role.role_id

        self.vdi_helper_lambda_function = lambda_.Function(
            self.nested_stack,
            lambda_name,
            handler="vdi_helper_lambda.handler.handler",
            code_directory_string=os.path.join(
                InfraUtils.lambda_functions_with_utils_dir()
            ),
            parameters=self.parameters,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description=f"{self.module_id} general purpose lambda for VDI operations.",  # type: ignore
            timeout=cdk.Duration.seconds(60),  # type: ignore
            layers=[self.lambda_layer],  # type: ignore
            role=vdi_helper_lambda_role,  # type: ignore
            vpc=self.vpc,  # type: ignore
            environment={
                # Required by shared library
                "environment_name": self.cluster_name,
                "HTTPS_PROXY": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
                "HTTP_PROXY": self.parameters.get_str(InternetProxyKey.HTTP_PROXY),
                "NO_PROXY": self.parameters.get_str(InternetProxyKey.NO_PROXY),
            },
        )
        cfn_vdi_helper_lambda: aws_lambda.CfnFunction = (
            self.vdi_helper_lambda_function.node.default_child  # type: ignore
        )
        cfn_vdi_helper_lambda.add_property_override(
            "VpcConfig.SubnetIds", self.cluster_settings.vdi_subnets
        )

        self.vdi_helper_api_gateway_rest_api = self._build_private_api_for_lambda(
            lambda_function=self.vdi_helper_lambda_function,
            api_name=api_gateway_name,
            resource_name=constants.API_GATEWAY_VDI_HELPER_RESOURCE,
            stage_name=constants.API_GATEWAY_VDI_HELPER_STAGE,
            api_description=f"{self.module_id} API Gateway for VDI Helper",
            http_method="POST",
            cidr_blocks=self.vdi_subnet_cidr_blocks,
        )

        self.vdi_helper_api_gateway_rest_api.node.add_dependency(
            self.vdi_helper_lambda_function
        )

    def _build_private_api_gateway_url(self, rest_api_id: str, stage_name: str) -> str:
        return f"https://{rest_api_id}-{self.api_gateway_vpc_endpoint.get_endpoint().vpc_endpoint_id}.execute-api.{self.aws_region}.amazonaws.com/{stage_name}/"  # type: ignore

    def _build_private_api_for_lambda(
        self,
        lambda_function: aws_lambda.Function,
        api_name: str,
        resource_name: str,
        stage_name: str,
        api_description: str,
        http_method: str,
        cidr_blocks: List[str],
    ) -> apigateway.RestApi:
        # cidr_blocks = Token.as_list(Fn.import_value("vdi-subnet-cidr-blocks"))
        api_gateway_rest_api_resource_policy = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    actions=["execute-api:Invoke"],
                    principals=[aws_iam.ServicePrincipal("ec2.amazonaws.com")],
                    resources=[
                        self.arn_builder.api_gateway_execute_api_arn(
                            "*", stage_name, http_method, resource_name
                        )
                    ],
                    conditions={"IpAddress": {"aws:SourceIp": cidr_blocks}},
                ),
            ]
        )

        api_gateway_log_group = logs.LogGroup(
            scope=self.nested_stack,
            id=f"{self.module_id}-{api_name}-access-logs",
            retention=logs.RetentionDays.TEN_YEARS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        api_gateway_rest_api = apigateway.RestApi(
            scope=self.nested_stack,
            id=api_name,
            description=api_description,
            cloud_watch_role=True,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
            policy=api_gateway_rest_api_resource_policy,
            deploy_options=apigateway.StageOptions(
                stage_name=stage_name,
                access_log_destination=apigateway.LogGroupLogDestination(
                    api_gateway_log_group
                ),
                access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    user=True,
                    status=True,
                ),
            ),
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.PRIVATE],
                vpc_endpoints=[self.api_gateway_vpc_endpoint.get_endpoint()],  # type: ignore
            ),
            default_method_options=apigateway.MethodOptions(
                authorization_type=apigateway.AuthorizationType.IAM
            ),
            rest_api_name=api_name,
        )

        resource = api_gateway_rest_api.root.add_resource(path_part=resource_name)

        resource.add_method(
            http_method=http_method,
            integration=apigateway.LambdaIntegration(handler=lambda_function),
            authorization_type=apigateway.AuthorizationType.IAM,
        )

        apigateway.RequestValidator(
            scope=self.nested_stack,
            id=f"{self.module_id}-{api_name}-request-validator",
            rest_api=api_gateway_rest_api,
            validate_request_body=True,
            validate_request_parameters=True,
        )

        return api_gateway_rest_api

    def build_dcv_host_infra_scoped_down(self) -> None:
        self.dcv_host_role_scoped_down_managed_policy = VirtualDesktopDcvHostScopedDownPolicy(
            self.nested_stack,
            description="Required policy for custom VDI scoped down instance profile",
            name="vdi-host-scoped-down-managed-policy",
            arn_builder=self.arn_builder,
            parameters=self.parameters,
        )
        self.dcv_host_role_scoped_down = self._build_iam_role(
            name=f"{self.module_id}-{self.COMPONENT_DCV_HOST}-scoped-down-role",
            description=f"IAM role assigned to virtual-desktop-{self.COMPONENT_DCV_HOST}-scoped-down",
            managed_policies=[self.dcv_host_role_scoped_down_managed_policy],
        )

        self.dcv_host_role_scoped_down.grant_pass_role(self.controller_role)  # type: ignore

        self.dcv_host_scoped_down_instance_profile = iam.InstanceProfile(
            scope=self.nested_stack,
            name=f"{self.module_id}-{self.COMPONENT_DCV_HOST}-scoped-down-instance-profile",
            parameters=self.parameters,
            roles=[self.dcv_host_role_scoped_down],
        )

    def build_dcv_host_infra(self) -> None:

        self.dcv_host_role = self._build_iam_role(
            name=f"{self.module_id}-{self.COMPONENT_DCV_HOST}-role",
            description=f"IAM role assigned to virtual-desktop-{self.COMPONENT_DCV_HOST}",
            inline_policies=[
                VirtualDesktopDcvPolicy(
                    self.nested_stack,
                    f"{self.module_id}-{self.COMPONENT_DCV_HOST}-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                )
            ],
        )
        self.dcv_host_role.grant_pass_role(self.controller_role)  # type: ignore

        custom_credential_broker_principal = aws_iam.ArnPrincipal(
            self.custom_credential_broker_lambda_role.role_arn  # type: ignore
        )

        self.dcv_host_role.assume_role_policy.add_statements(  # type: ignore
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=["sts:AssumeRole"],
                principals=[custom_credential_broker_principal],
            )
        )

        self.dcv_host_instance_profile = iam.InstanceProfile(
            scope=self.nested_stack,
            name=f"{self.module_id}-{self.COMPONENT_DCV_HOST}-instance-profile",
            parameters=self.parameters,
            roles=[self.dcv_host_role],
        )
        self.dcv_host_security_group = ec2.VirtualDesktopBastionAccessSecurityGroup(
            name=f"{self.module_id}-dcv-host-security-group",
            scope=self.nested_stack,
            vpc=self.vpc,
            parameters=self.parameters,
            bastion_host_security_group=self.bastion_host_security_group,
            description="Security Group for DCV Host",
            directory_service_access=True,
            component_name="DCV Host",
        )

    def build_dcv_broker(self) -> None:
        # client target group and registration
        self.client_target_group = elbv2.ApplicationTargetGroup(
            self.nested_stack,
            f"{self.COMPONENT_DCV_BROKER}-client-target-group",
            port=self.BROKER_CLIENT_COMMUNICATION_PORT,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            vpc=self.vpc,
            target_group_name=InfraUtils.get_target_group_name(
                self.cluster_name, self.module_id, f"{self.COMPONENT_DCV_BROKER}-c"
            ),
        )
        self.client_target_group.configure_health_check(enabled=True, path="/health")

        cdk.CustomResource(
            self.nested_stack,
            "dcv-broker-client-endpoint",
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                "endpoint_name": "broker-client-endpoint",
                "listener_arn": self.cluster_stack.internal_alb_dcv_broker_client_listener.attr_listener_arn,  # type: ignore
                "priority": 0,
                "default_action": True,
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": self.client_target_group.target_group_arn,
                    }
                ],
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::DcvBrokerClientEndpointInternal",
        )

        # agent target group and registration
        agent_target_group = elbv2.ApplicationTargetGroup(
            self.nested_stack,
            f"{self.COMPONENT_DCV_BROKER}-agent-target-group",
            port=self.BROKER_AGENT_COMMUNICATION_PORT,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            vpc=self.vpc,
            target_group_name=InfraUtils.get_target_group_name(
                self.cluster_name, self.module_id, f"{self.COMPONENT_DCV_BROKER}-a"
            ),
        )
        agent_target_group.configure_health_check(enabled=True, path="/health")

        cdk.CustomResource(
            self.nested_stack,
            "dcv-broker-agent-endpoint",
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                "endpoint_name": "broker-client-endpoint",
                "listener_arn": self.cluster_stack.internal_alb_dcv_broker_agent_listener.attr_listener_arn,  # type: ignore
                "priority": 0,
                "default_action": True,
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": agent_target_group.target_group_arn,
                    }
                ],
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::DcvBrokerAgentEndpointInternal",
        )

        # gateway target group and registration
        gateway_target_group = elbv2.ApplicationTargetGroup(
            self.nested_stack,
            f"{self.COMPONENT_DCV_BROKER}-gateway-target-group",
            port=self.BROKER_GATEWAY_COMMUNICATION_PORT,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            vpc=self.vpc,
            target_group_name=InfraUtils.get_target_group_name(
                self.cluster_name, self.module_id, f"{self.COMPONENT_DCV_BROKER}-g"
            ),
        )
        gateway_target_group.configure_health_check(enabled=True, path="/health")

        cdk.CustomResource(
            self.nested_stack,
            "dcv-broker-gateway-endpoint",
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                "endpoint_name": "broker-gateway-endpoint",
                "listener_arn": self.cluster_stack.internal_alb_dcv_broker_gateway_listener.attr_listener_arn,  # type: ignore
                "priority": 0,
                "default_action": True,
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": gateway_target_group.target_group_arn,
                    }
                ],
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::DcvBrokerGatewayEndpointInternal",
        )

        # security group
        self.dcv_broker_security_group = ec2.VirtualDesktopBastionAccessSecurityGroup(
            name=f"{self.module_id}-{self.COMPONENT_DCV_BROKER}-security-group",
            scope=self.nested_stack,
            vpc=self.vpc,
            parameters=self.parameters,
            bastion_host_security_group=self.bastion_host_security_group,
            description="Security Group for Virtual Desktop DCV Broker",
            directory_service_access=False,
            component_name="DCV Broker",
        )

        # autoscaling group
        broker_userdata = BootstrapUserDataBuilder(
            aws_region=self.aws_region,
            bootstrap_package_uri=self.cluster_settings.installation_scripts_uri,
            install_commands=[
                f"/bin/bash scripts/infrastructure-host/install.sh -p false -c dcv-broker -m {self.module_id} -e {self.cluster_name}"
            ],
            infra_config={
                "BROKER_CLIENT_TARGET_GROUP_ARN": self.client_target_group.target_group_arn,
                "CONTROLLER_EVENTS_QUEUE_URL": self.event_sqs_queue.queue_url,  # type: ignore
            },
            proxy_config=self.PROXY_CONFIG,
            base_os=self.cluster_settings.base_os(),
        ).build()

        self.dcv_broker_role = self._build_iam_role(
            name=f"{self.module_id}-{self.COMPONENT_DCV_BROKER}-role",
            description=f"IAM role assigned to virtual-desktop-{self.COMPONENT_DCV_BROKER}",
            inline_policies=[
                VirtualDesktopBrokerPolicy(
                    self.nested_stack,
                    f"{self.module_id}-{self.COMPONENT_DCV_BROKER}-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                )
            ],
        )

        self.dcv_broker_autoscaling_group = self._build_auto_scaling_group(
            instance_name_suffix=self.COMPONENT_DCV_BROKER,
            security_group=self.dcv_broker_security_group,
            iam_role=self.dcv_broker_role,
            userdata=broker_userdata,
            node_type=constants.NODE_TYPE_INFRA,
        )
        self.dcv_broker_autoscaling_group.node.add_dependency(self.event_sqs_queue)

        # receiving error jsii.errors.JSIIError: Cannot add AutoScalingGroup to 2nd Target Group
        # if same ASG is added to both internal and external target groups.
        # workaround below - reference to https://github.com/aws/aws-cdk/issues/5667#issuecomment-827549394
        self.dcv_broker_autoscaling_group.node.default_child.target_group_arns = [  # type: ignore
            agent_target_group.target_group_arn,
            self.client_target_group.target_group_arn,
            gateway_target_group.target_group_arn,
        ]

    def build_virtual_desktop_controller(self) -> None:
        self.controller_security_group = ec2.VirtualDesktopPublicLoadBalancerAccessSecurityGroup(
            name=f"{self.module_id}-{self.COMPONENT_CONTROLLER}-security-group",
            scope=self.nested_stack,
            vpc=self.vpc,
            parameters=self.parameters,
            bastion_host_security_group=self.bastion_host_security_group,
            public_loadbalancer_security_group=self.external_loadbalancer_security_group,
            description="Security Group for Virtual Desktop Controller",
            directory_service_access=True,
            component_name="Virtual Desktop Controller",
        )

        self.controller_role = self._build_iam_role(
            name=f"{self.module_id}-{self.COMPONENT_CONTROLLER}-role",
            description=f"IAM role assigned to virtual-desktop-{self.COMPONENT_CONTROLLER}",
            inline_policies=[
                VirtualDesktopControllerPolicy(
                    self.nested_stack,
                    f"{self.module_id}-{self.COMPONENT_CONTROLLER}-policy",
                    arn_builder=self.arn_builder,
                    parameters=self.parameters,
                )
            ],
        )

        self.controller_auto_scaling_group = self._build_auto_scaling_group(
            # component_name=self.COMPONENT_CONTROLLER,
            instance_name_suffix=self.COMPONENT_CONTROLLER,
            security_group=self.controller_security_group,
            iam_role=self.controller_role,
            userdata=BootstrapUserDataBuilder(
                aws_region=self.aws_region,
                bootstrap_package_uri=self.cluster_settings.installation_scripts_uri,
                install_commands=[
                    f"/bin/bash scripts/infrastructure-host/install.sh -p false -c virtual-desktop-controller -m {self.module_id} -e {self.cluster_name}"
                ],
                proxy_config=self.PROXY_CONFIG,
                base_os=self.cluster_settings.base_os(),
            ).build(),
            node_type=constants.NODE_TYPE_APP,
        )

        self.controller_auto_scaling_group.node.add_dependency(self.event_sqs_queue)
        self.controller_auto_scaling_group.node.add_dependency(
            self.controller_sqs_queue
        )

        # external target group
        external_target_group = elbv2.ApplicationTargetGroup(
            self.nested_stack,
            "controller-target-group-ext",
            port=8443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            protocol_version=elbv2.ApplicationProtocolVersion.HTTP1,
            target_type=elbv2.TargetType.INSTANCE,
            vpc=self.vpc,
            target_group_name=InfraUtils.get_target_group_name(
                self.cluster_name, self.module_id, "vdc-ext"
            ),
        )
        external_target_group.configure_health_check(enabled=True, path="/healthcheck")

        path_patterns = self.vdc_settings.endpoints_path_patterns("external")
        priority = self.vdc_settings.endpoints_priority("external")
        cdk.CustomResource(
            self.nested_stack,
            "controller-endpoint-ext",
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                "endpoint_name": f"{self.module_id}-controller-endpoint-ext",
                "listener_arn": self.cluster_stack.external_alb_https_listener.attr_listener_arn,  # type: ignore
                "priority": priority,
                "conditions": [{"Field": "path-pattern", "Values": path_patterns}],
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": external_target_group.target_group_arn,
                    }
                ],
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::ControllerEndpointExternal",
        )

        # internal target group
        internal_target_group = elbv2.ApplicationTargetGroup(
            self.nested_stack,
            "controller-target-group-int",
            port=8443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            protocol_version=elbv2.ApplicationProtocolVersion.HTTP1,
            target_type=elbv2.TargetType.INSTANCE,
            vpc=self.vpc,
            target_group_name=InfraUtils.get_target_group_name(
                self.cluster_name, self.module_id, "vdc-int"
            ),
        )
        internal_target_group.configure_health_check(enabled=True, path="/healthcheck")

        path_patterns = self.vdc_settings.endpoints_path_patterns("internal")
        priority = self.vdc_settings.endpoints_priority("internal")
        cdk.CustomResource(
            self.nested_stack,
            "controller-endpoint-int",
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                "endpoint_name": f"{self.module_id}-controller-endpoint-int",
                "listener_arn": self.cluster_stack.internal_alb_https_listener.attr_listener_arn,  # type: ignore
                "priority": priority,
                "conditions": [{"Field": "path-pattern", "Values": path_patterns}],
                "actions": [
                    {
                        "Type": "forward",
                        "TargetGroupArn": internal_target_group.target_group_arn,
                    }
                ],
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::ControllerEndpointInternal",
        )

        # receiving error jsii.errors.JSIIError: Cannot add AutoScalingGroup to 2nd Target Group
        # if same ASG is added to both internal and external target groups.
        # workaround below - reference to https://github.com/aws/aws-cdk/issues/5667#issuecomment-827549394
        self.controller_auto_scaling_group.node.default_child.target_group_arns = [  # type: ignore
            internal_target_group.target_group_arn,
            external_target_group.target_group_arn,
        ]

    def build_dcv_connection_gateway(self) -> None:
        self._build_self_signed_cert_for_dcv_connection_gateway()

        self._build_dcv_connection_gateway_instance_infrastructure()
        self._build_dcv_connection_gateway_network_infrastructure()

    def build_cluster_settings(self) -> None:
        cluster_settings = {
            "deployment_id": self.deployment_id,
            "client_id": self.oauth2_client_secret.client_id.ref,  # type: ignore
            "client_secret": self.oauth2_client_secret.client_secret.ref,  # type: ignore
            "dcv_host_security_group_id": self.dcv_host_security_group.security_group_id,  # type: ignore
            "dcv_host_role_arn": self.dcv_host_role.role_arn,  # type: ignore
            "dcv_host_role_name": self.dcv_host_role.role_name,  # type: ignore
            "dcv_host_role_id": self.dcv_host_role.role_id,  # type: ignore
            "dcv_host_role_managed_policy_arn": self.dcv_host_role_scoped_down_managed_policy.managed_policy_arn,  # type: ignore
            "dcv_host_role_scoped_down_arn": self.dcv_host_role_scoped_down.role_arn,  # type: ignore
            "dcv_host_scoped_down_instance_profile_name": self.dcv_host_scoped_down_instance_profile.ref,  # type: ignore
            "dcv_host_scoped_down_instance_profile_arn": self.arn_builder.get_instance_profile_arn_from_ref(
                self.dcv_host_scoped_down_instance_profile.ref  # type: ignore
            ),
            "dcv_host_role_scoped_down_name": self.dcv_host_role_scoped_down.role_name,  # type: ignore
            "dcv_host_role_scoped_down_id": self.dcv_host_role_scoped_down.role_id,  # type: ignore
            "dcv_broker_role_arn": self.dcv_broker_role.role_arn,  # type: ignore
            "dcv_broker_role_name": self.dcv_broker_role.role_name,  # type: ignore
            "dcv_broker_role_id": self.dcv_broker_role.role_id,  # type: ignore
            "scheduled_event_transformer_lambda_role_arn": self.scheduled_event_transformer_lambda_role.role_arn,  # type: ignore
            "scheduled_event_transformer_lambda_role_name": self.scheduled_event_transformer_lambda_role.role_name,  # type: ignore
            "scheduled_event_transformer_lambda_role_id": self.scheduled_event_transformer_lambda_role.role_id,  # type: ignore
            "custom_credential_broker_lambda_function_arn": self.custom_credential_broker_lambda_function.function_arn,  # type: ignore
            "custom_credential_broker_api_gateway_url": self._build_private_api_gateway_url(
                self.custom_credential_broker_api_gateway_rest_api.rest_api_id,  # type: ignore
                constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_STAGE,
            )
            + constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE,
            "vdi_helper_api_gateway_url": self._build_private_api_gateway_url(
                self.vdi_helper_api_gateway_rest_api.rest_api_id,  # type: ignore
                constants.API_GATEWAY_VDI_HELPER_STAGE,
            )
            + constants.API_GATEWAY_VDI_HELPER_RESOURCE,
            "custom_credential_broker_secret_name": self.custom_broker_secret.secret_name,  # type: ignore
            "custom_credential_broker_secret_arn": self.custom_broker_secret.secret_arn,  # type: ignore
            "custom_credential_broker_api_gateway_id": self.custom_credential_broker_api_gateway_rest_api.rest_api_id,  # type: ignore
            "custom_credential_broker_lambda_role_arn": self.custom_credential_broker_lambda_role.role_arn,  # type: ignore
            "s3_mount_base_bucket_read_only_role_arn": self.s3_mount_base_bucket_read_only_role.role_arn,  # type: ignore
            "s3_mount_base_bucket_read_write_role_arn": self.s3_mount_base_bucket_read_write_role.role_arn,  # type: ignore
            "dcv_host_instance_profile_name": self.dcv_host_scoped_down_instance_profile.ref,  # type: ignore
            "dcv_host_instance_profile_arn": self.arn_builder.get_instance_profile_arn_from_ref(
                self.dcv_host_scoped_down_instance_profile.ref  # type: ignore
            ),
            "ssm_commands_sns_topic_arn": self.ssm_commands_sns_topic.topic_arn,  # type: ignore
            "ssm_commands_sns_topic_name": self.ssm_commands_sns_topic.topic_name,  # type: ignore
            "ssm_commands_pass_role_arn": self.ssm_command_pass_role.role_arn,  # type: ignore
            "ssm_commands_pass_role_id": self.ssm_command_pass_role.role_id,  # type: ignore
            "ssm_commands_pass_role_name": self.ssm_command_pass_role.role_name,  # type: ignore
            "controller_iam_role_arn": self.controller_role.role_arn,  # type: ignore
            "controller_iam_role_name": self.controller_role.role_name,  # type: ignore
            "controller_iam_role_id": self.controller_role.role_id,  # type: ignore
            "events_sqs_queue_url": self.event_sqs_queue.queue_url,  # type: ignore
            "events_sqs_queue_arn": self.event_sqs_queue.queue_arn,  # type: ignore
            "controller_sqs_queue_url": self.controller_sqs_queue.queue_url,  # type: ignore
            "controller_sqs_queue_arn": self.controller_sqs_queue.queue_arn,  # type: ignore
            "external_nlb.load_balancer_dns_name": self.external_nlb.attr_dns_name,  # type: ignore
            "external_nlb_arn": self.external_nlb.attr_load_balancer_arn,  # type: ignore
            "dcv_broker.client_target_group_arn": self.client_target_group.target_group_arn,  # type: ignore
            "gateway_security_group_id": self.dcv_connection_gateway_security_group.security_group_id,  # type: ignore
            "vdi-helper-id": self.vdi_helper_lambda_role_role_id,
        }

        cluster_settings[
            "dcv_connection_gateway.certificate.certificate_secret_arn"
        ] = Fn.condition_if(
            self.certificate_all_provided.logical_id,
            self.parameters.get_str(CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI),
            self.dcv_connection_gateway_self_signed_cert.get_att_string(  # type: ignore
                "certificate_secret_arn"
            ),
        )
        cluster_settings[
            "dcv_connection_gateway.certificate.private_key_secret_arn"
        ] = Fn.condition_if(
            self.certificate_all_provided.logical_id,
            self.parameters.get_str(CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI),
            self.dcv_connection_gateway_self_signed_cert.get_att_string(  # type: ignore
                "private_key_secret_arn"
            ),
        )
        cluster_settings["dcv_connection_gateway.certificate.provided"] = (
            Fn.condition_if(self.certificate_all_provided.logical_id, "true", "false")
        )
        cluster_settings["dcv_connection_gateway.certificate.custom_dns_name"] = (
            Fn.condition_if(
                self.certificate_all_provided.logical_id,
                self.parameters.get_str(CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_VDI),
                "",
            )
        )

        self.cluster_settings_custom_resource = cdk.CustomResource(
            self.nested_stack,
            "cluster-settings",
            service_token=self.cluster_stack.cluster_settings_lambda.function_arn,
            properties={
                "cluster_name": self.cluster_name,
                "module_id": self.module_id,
                "version": self.get_res_release_version(),
                "settings": cluster_settings,
            },
            resource_type="Custom::ClusterSettings",
        )
        self.controller_auto_scaling_group.node.add_dependency(  # type: ignore
            self.cluster_settings_custom_resource
        )
        self.dcv_broker_autoscaling_group.node.add_dependency(  # type: ignore
            self.cluster_settings_custom_resource
        )
        self.dcv_connection_gateway_autoscaling_group.node.add_dependency(  # type: ignore
            self.cluster_settings_custom_resource
        )

        asg_cluster_settings = {
            "controller.asg_arn": self.controller_auto_scaling_group.auto_scaling_group_arn,  # type: ignore
            "dcv_broker.asg_arn": self.dcv_broker_autoscaling_group.auto_scaling_group_arn,  # type: ignore
            "dcv_connection_gateway.asg_arn": self.dcv_connection_gateway_autoscaling_group.auto_scaling_group_arn,  # type: ignore
        }

        self.asg_cluster_settings_custom_resource = cdk.CustomResource(
            self.nested_stack,
            "asg-cluster-settings",
            service_token=self.cluster_stack.cluster_settings_lambda.function_arn,
            properties={
                "cluster_name": self.cluster_name,
                "module_id": self.module_id,
                "version": self.get_res_release_version(),
                "settings": asg_cluster_settings,
            },
            resource_type="Custom::ClusterSettings",
        )

    def get_ec2_instance_managed_policies(self) -> List[Optional[Any]]:
        ec2_managed_policies = [
            self.cluster_stack.amazon_ssm_managed_instance_core_policy,
            self.cluster_stack.cloud_watch_agent_server_policy,
        ]

        ec2_managed_policies += self.cluster_settings.ec2_managed_policy_arns
        return ec2_managed_policies

    def _build_dcv_connection_gateway_instance_infrastructure(self) -> None:
        self.dcv_connection_gateway_security_group = ec2.VirtualDesktopPublicLoadBalancerAccessSecurityGroup(
            name=f"{self.module_id}-{self.COMPONENT_DCV_CONNECTION_GATEWAY}-security-group",
            scope=self.nested_stack,
            vpc=self.vpc,
            parameters=self.parameters,
            bastion_host_security_group=self.bastion_host_security_group,
            public_loadbalancer_security_group=self.external_loadbalancer_security_group,
            description="Security Group for Virtual Desktop DCV Connection Gateway",
            directory_service_access=False,
            component_name="DCV Connection Gateway",
        )

        user_data_certificate_secret_arn = Fn.condition_if(
            self.certificate_all_provided.logical_id,
            self.parameters.get_str(CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI),
            self.dcv_connection_gateway_self_signed_cert.get_att_string(  # type: ignore
                "certificate_secret_arn"
            ),
        )
        user_data_private_key_secret_arn = Fn.condition_if(
            self.certificate_all_provided.logical_id,
            self.parameters.get_str(CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI),
            self.dcv_connection_gateway_self_signed_cert.get_att_string(  # type: ignore
                "private_key_secret_arn"
            ),
        )

        connection_gateway_userdata = BootstrapUserDataBuilder(
            aws_region=self.aws_region,
            bootstrap_package_uri=self.cluster_settings.installation_scripts_uri,
            install_commands=[
                f"/bin/bash scripts/infrastructure-host/install.sh -p false -c dcv-connection-gateway -m {self.module_id} -e {self.cluster_name}"
            ],
            infra_config={
                "CERTIFICATE_SECRET_ARN": user_data_certificate_secret_arn.to_string(),
                "PRIVATE_KEY_SECRET_ARN": user_data_private_key_secret_arn.to_string(),
            },
            proxy_config=self.PROXY_CONFIG,
            base_os=self.cluster_settings.base_os(),
        ).build()

        self.dcv_connection_gateway_autoscaling_group = self._build_auto_scaling_group(
            instance_name_suffix=self.COMPONENT_DCV_CONNECTION_GATEWAY,
            security_group=self.dcv_connection_gateway_security_group,
            iam_role=self._build_iam_role(
                name=f"{self.module_id}-{self.COMPONENT_DCV_CONNECTION_GATEWAY}-role",
                description=f"IAM role assigned to virtual-desktop-{self.COMPONENT_DCV_CONNECTION_GATEWAY}",
                inline_policies=[
                    VirtualDesktopConnectionGatewayPolicy(
                        self.nested_stack,
                        f"{self.module_id}-{self.COMPONENT_DCV_CONNECTION_GATEWAY}-policy",
                        arn_builder=self.arn_builder,
                        parameters=self.parameters,
                    )
                ],
            ),
            userdata=connection_gateway_userdata,
            node_type=constants.NODE_TYPE_INFRA,
        )

    def _build_dcv_connection_gateway_network_infrastructure(self) -> None:

        is_public = CfnCondition(
            self.nested_stack,
            "is-public",
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
        load_balancer_attributes = (
            [
                {"key": "deletion_protection.enabled", "value": "false"},
                {"key": "access_logs.s3.enabled", "value": "true"},
                # Manage Access Logs for external Application Load Balancer
                # https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html
                {
                    "key": "access_logs.s3.bucket",
                    "value": logging_s3_bucket.bucket_name,
                },
                {
                    "key": "access_logs.s3.prefix",
                    "value": f"logs/{self.module_id}/external-nlb-access-logs",
                },
            ]
            if self.vdc_settings.external_nlb_enable_access_log
            else [
                {"key": "deletion_protection.enabled", "value": "false"},
                {"key": "access_logs.s3.enabled", "value": "false"},
            ]
        )

        self.external_nlb = elbv2.CfnLoadBalancer(
            self.nested_stack,
            f"{self.module_id}-external-nlb",
            load_balancer_attributes=load_balancer_attributes,
            subnets=self.cluster_settings.load_balancer_subnets,  # type: ignore
            name=f"{self.cluster_name}-{self.module_id}-external-nlb",
            scheme=Fn.condition_if(
                is_public.logical_id,
                "internet-facing",
                "internal",
            ).to_string(),
            type="network",
        )

        quic_supported = self.vdc_settings.quic_support
        protocol = elbv2.Protocol.TCP
        protocal_string = "TCP"
        tg_suffix = "TN"  # TCP Network
        if quic_supported:
            protocol = elbv2.Protocol.TCP_UDP
            protocal_string = "TCP_UDP"
            tg_suffix = "TUN"  # TCP - UDP Network

        dcv_connection_gateway_target_group = elbv2.NetworkTargetGroup(
            self.nested_stack,
            "dcv-connection-gateway-target-group-nlb",
            port=8443,
            protocol=protocol,
            target_type=elbv2.TargetType.INSTANCE,
            vpc=self.vpc,
            targets=[self.dcv_connection_gateway_autoscaling_group],  # type: ignore
            target_group_name=InfraUtils.get_target_group_name(
                self.cluster_name,
                self.module_id,
                f"{self.COMPONENT_DCV_CONNECTION_GATEWAY}-{tg_suffix}",
            ),
            health_check=elbv2.HealthCheck(port="8989", protocol=elbv2.Protocol.TCP),
            connection_termination=True,
        )
        # Can not provide stickiness attributes directly in CDK Construct. Refer - https://github.com/aws/aws-cdk/issues/17491
        # Documentation on attributes. Refer - https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-elasticloadbalancingv2-targetgroup-targetgroupattribute.html
        dcv_connection_gateway_target_group.set_attribute("stickiness.enabled", "true")
        dcv_connection_gateway_target_group.set_attribute(
            "stickiness.type", "source_ip"
        )

        elbv2.CfnListener(
            self.external_nlb,
            "dcv-connection-gateway-nlb-listener",
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type="forward",
                    target_group_arn=dcv_connection_gateway_target_group.target_group_arn,
                )
            ],
            port=443,
            load_balancer_arn=self.external_nlb.ref,
            protocol=protocal_string,
        )

        self.dcv_connection_gateway_security_group.add_ingress_rule(  # type: ignore
            aws_ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            aws_ec2.Port.tcp(8989),
            description="Allow TCP traffic access for HealthCheck to DCV Connection Gateway",
        )

        self.dcv_connection_gateway_security_group.add_ingress_rule(  # type: ignore
            aws_ec2.Peer.prefix_list(
                self.cluster_stack.cluster_prefix_list.attr_prefix_list_id  # type: ignore
            ),
            aws_ec2.Port.all_traffic(),
            description="Allow all Traffic access from Cluster Prefix List to DCV Connection Gateway",
        )

        gateway_security_group_prefix_list_ingress = aws_ec2.CfnSecurityGroupIngress(
            self.nested_stack,
            "dcv-connection-gateway-nlb-security-group-ingress-rule",
            source_prefix_list_id=self.parameters.get_str(CommonKey.CLIENT_PREFIX_LIST),
            ip_protocol="-1",
            from_port=-1,
            to_port=-1,
            group_id=self.dcv_connection_gateway_security_group.security_group_id,  # type: ignore
            description="Allow all traffic access from Prefix List to DCV Connection Gateway",
        )

        gateway_security_group_prefix_list_ingress.cfn_options.condition = (
            self.prefix_list_provided
        )

        self.dcv_connection_gateway_security_group.add_egress_rule(  # type: ignore
            aws_ec2.Peer.ipv4("0.0.0.0/0"),
            aws_ec2.Port.udp_range(0, 65535),
            description="Allow all egress for UDP on DCV Connection Gateway",
        )

    def _build_self_signed_cert_for_dcv_connection_gateway(self) -> None:
        self_signed_certificate_lambda_arn = (
            self.cluster_stack.self_signed_certificate_lambda.function_arn  # type: ignore
        )
        self.dcv_connection_gateway_self_signed_cert = cdk.CustomResource(
            self.nested_stack,
            f"{self.module_id}-external-cert-{self.COMPONENT_DCV_CONNECTION_GATEWAY}",
            service_token=self_signed_certificate_lambda_arn,
            properties={
                "domain_name": f"{self.module_id}.{self.cluster_name}.idea.default",
                "certificate_name": f"{self.cluster_name}-{self.module_id}-{self.COMPONENT_DCV_CONNECTION_GATEWAY}-certificate",
                "create_acm_certificate": False,
                "kms_key_id": self.cluster_settings.kms_secretsmanager_key_id,
                "tags": {
                    "Name": f"{self.cluster_name}-{self.module_id}-{self.COMPONENT_DCV_CONNECTION_GATEWAY} Self Signed Certificate",
                    "res:EnvironmentName": self.cluster_name,
                    "res:ModuleName": "virtual-desktop-controller",
                },
                OLD_CUSTOM_TAG_KEYS: self.params_transformer.get_att_string(
                    OLD_CUSTOM_TAG_KEYS
                ),
            },
            resource_type="Custom::SelfSignedCertificateConnectionGateway",
        )
        raw_self_signed_certificate = (
            self.dcv_connection_gateway_self_signed_cert.node.default_child
        )
        raw_self_signed_certificate.cfn_options.condition = CfnCondition(  # type: ignore
            self.nested_stack,
            "vdi-cert-not-provided",
            expression=Fn.condition_not(self.certificate_all_provided.expression),  # type: ignore
        )

    def _build_iam_role(
        self,
        description: str,
        name: str,
        inline_policies: List[iam.Policy] = [],
        managed_policies: List[Any] = [],
    ) -> iam.Role:

        all_managed_policies = (
            self.get_ec2_instance_managed_policies() + managed_policies
        )
        return iam.Role(
            self.nested_stack,
            name=name,
            arn_builder=self.arn_builder,
            parameters=self.parameters,
            description=description,
            assumed_by=["ssm", "ec2"],
            inline_policies=inline_policies,
            managed_policies=all_managed_policies,
        )

    def _build_auto_scaling_group(
        self,
        instance_name_suffix: str,
        security_group: ec2.SecurityGroup,
        iam_role: iam.Role,
        userdata: str,
        node_type: str,
    ) -> asg.AutoScalingGroup:

        component_name = self.CONFIG_MAPPING[instance_name_suffix]
        is_public = self.vdc_settings.autoscaling_setting(component_name, "public")
        if is_public:
            subnets = [  # type: ignore
                aws_ec2.Subnet.from_subnet_id(
                    self.nested_stack,
                    f"{component_name}-is-public-subnet-{index}",
                    subnet_id,
                )
                for index, subnet_id in enumerate(
                    self.cluster_settings.load_balancer_subnets  # type: ignore
                )
            ]
        else:
            subnets = [  # type: ignore
                aws_ec2.Subnet.from_subnet_id(
                    self.nested_stack,
                    f"{component_name}-not-public-subnet-{index}",
                    subnet_id,
                )
                for index, subnet_id in enumerate(
                    self.cluster_settings.infrastructure_host_subnets  # type: ignore
                )
            ]
        vpc_subnets = aws_ec2.SubnetSelection(subnets=subnets)

        block_device_name = self.cluster_settings.get_ec2_block_device_name()
        enable_detailed_monitoring = self.vdc_settings.autoscaling_setting(
            component_name, "enable_detailed_monitoring"
        )
        metadata_http_tokens = self.vdc_settings.autoscaling_setting(
            component_name, "metadata_http_tokens"
        )

        kms_key_id = self.cluster_settings.kms_ebs_key_id
        if kms_key_id:
            kms_key_arn = self.arn_builder.kms_ebs_key_arn
            ebs_kms_key = kms.Key.from_key_arn(
                scope=self.nested_stack,
                id=f"{component_name}-ebs-kms-key",
                key_arn=kms_key_arn,  # type: ignore
            )
        else:
            ebs_kms_key = kms.Alias.from_alias_name(
                scope=self.nested_stack,
                id=f"{component_name}-ebs-kms-key-default",
                alias_name="alias/aws/ebs",
            )

        instance_profile = iam.InstanceProfile(
            scope=self.nested_stack,
            name=f"{component_name}-profile",
            parameters=self.parameters,
            roles=[iam_role],
        )

        launch_template = aws_ec2.LaunchTemplate(
            self.nested_stack,
            f"{component_name}-lt",
            instance_type=aws_ec2.InstanceType(
                self.vdc_settings.autoscaling_instance_type(component_name)
            ),
            machine_image=aws_ec2.MachineImage.latest_amazon_linux2023(),
            security_group=security_group,
            user_data=aws_ec2.UserData.custom(userdata),
            key_name=self.parameters.get_str(CommonKey.SSH_KEY_PAIR),
            block_devices=[
                aws_ec2.BlockDevice(
                    device_name=block_device_name,
                    volume=aws_ec2.BlockDeviceVolume(
                        ebs_device=aws_ec2.EbsDeviceProps(
                            encrypted=True,
                            kms_key=ebs_kms_key,
                            volume_size=self.vdc_settings.autoscaling_setting(
                                component_name, "volume_size"
                            ),
                            volume_type=aws_ec2.EbsDeviceVolumeType.GP3,
                        )
                    ),
                )
            ],
            require_imdsv2=True if metadata_http_tokens == "required" else False,
            associate_public_ip_address=is_public,
            version_description=self.deployment_id,
        )

        cfn_launch_template: aws_ec2.CfnLaunchTemplate = (
            launch_template.node.default_child  # type: ignore
        )
        cfn_launch_template.add_property_override(
            "LaunchTemplateData.IamInstanceProfile", {"Arn": instance_profile.attr_arn}
        )

        cfn_launch_template.add_property_override(
            "LaunchTemplateData.ImageId",
            self.vdc_settings.autoscaling_instance_ami(component_name),
        )

        auto_scaling_group = asg.AutoScalingGroup(
            self.nested_stack,
            f"{component_name}-asg",
            vpc=self.vpc,
            vpc_subnets=vpc_subnets,
            auto_scaling_group_name=f"{self.cluster_name}-{self.module_id}-{component_name}-asg",
            launch_template=launch_template,
            instance_monitoring=(
                asg.Monitoring.DETAILED
                if enable_detailed_monitoring
                else asg.Monitoring.BASIC
            ),
            group_metrics=[asg.GroupMetrics.all()],
            min_capacity=self.vdc_settings.autoscaling_setting(
                component_name, "min_capacity"
            ),
            max_capacity=self.vdc_settings.autoscaling_setting(
                component_name, "max_capacity"
            ),
            new_instances_protected_from_scale_in=self.vdc_settings.autoscaling_setting(
                component_name, "new_instances_protected_from_scale_in"
            ),
            cooldown=cdk.Duration.minutes(
                self.vdc_settings.autoscaling_setting(
                    component_name, "cooldown_minutes"
                )
            ),
            default_instance_warmup=cdk.Duration.minutes(
                self.vdc_settings.autoscaling_setting(
                    component_name, "default_instance_warmup"
                )
            ),
            health_check=asg.HealthCheck.elb(
                grace=cdk.Duration.minutes(
                    self.vdc_settings.autoscaling_setting(
                        component_name, "grace_time_minutes"
                    )
                )
            ),
            update_policy=asg.UpdatePolicy.rolling_update(
                max_batch_size=self.vdc_settings.autoscaling_setting(
                    component_name, "max_batch_size"
                ),
                min_instances_in_service=self.vdc_settings.autoscaling_setting(
                    component_name, "min_instances_in_service"
                ),
                pause_time=cdk.Duration.minutes(
                    self.vdc_settings.autoscaling_setting(
                        component_name, "pause_time_minutes"
                    )
                ),
            ),
            termination_policies=[asg.TerminationPolicy.DEFAULT],
        )

        auto_scaling_group.scale_on_cpu_utilization(
            "cpu-utilization-scaling-policy",
            target_utilization_percent=self.vdc_settings.autoscaling_setting(
                component_name, "target_utilization_percent"
            ),
            estimated_instance_warmup=cdk.Duration.minutes(
                self.vdc_settings.autoscaling_setting(
                    component_name, "estimated_instance_warmup_minutes"
                )
            ),
        )

        cdk.Tags.of(auto_scaling_group).add(constants.RES_TAG_NODE_TYPE, node_type)
        cdk.Tags.of(auto_scaling_group).add(
            constants.RES_TAG_NAME,
            f"{self.cluster_name}-{self.module_id}-{instance_name_suffix}",
        )
        return auto_scaling_group
