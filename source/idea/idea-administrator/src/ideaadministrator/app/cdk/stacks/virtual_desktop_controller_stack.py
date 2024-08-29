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

import ideaadministrator
from ideaadministrator.app.cdk.idea_code_asset import IdeaCodeAsset, SupportedLambdaPlatforms
from ideaadministrator.app.cdk.constructs import (
    ExistingSocaCluster,
    SubnetFilterKeys,
    OAuthClientIdAndSecret,
    Role,
    InstanceProfile,
    VirtualDesktopBastionAccessSecurityGroup,
    VirtualDesktopPublicLoadBalancerAccessSecurityGroup,
    VirtualDesktopCustomCredentialBrokerSecurityGroup,
    SQSQueue,
    SNSTopic,
    Policy,
    ManagedPolicy,
    LambdaFunction,
    SecurityGroup,
    IdeaNagSuppression,
    BackupPlan,
    APIGatewayRestApi, VpcInterfaceEndpoint, VpcEndpointSecurityGroup, CreateTagsCustomResource
)
from ideaadministrator import app_constants
from ideaadministrator.app.cdk.stacks import IdeaBaseStack
from ideadatamodel import (
    constants,
    SocaAnyPayload
)
from ideadatamodel.constants import IDEA_TAG_MODULE_ID
from ideasdk.aws import AwsClientProvider, AWSClientProviderOptions
from ideasdk.bootstrap import BootstrapUserDataBuilder
from ideasdk.context import ArnBuilder
from ideasdk.utils import Utils

import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_cognito as cognito,
    aws_sqs as sqs,
    aws_events as events,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscription,
    aws_autoscaling as asg,
    aws_elasticloadbalancingv2 as elbv2,
    aws_events_targets as events_targets,
    aws_s3 as s3,
    aws_backup as backup,
    aws_iam as iam,
    aws_kms as kms,
    aws_apigateway as apigateway,
    aws_logs as logs,
    RemovalPolicy,
)

from aws_cdk.aws_events import Schedule
from typing import Optional


class VirtualDesktopControllerStack(IdeaBaseStack):
    """
    Virtual Desktop Controller (eVDI) Stack

    Provisions infrastructure for eVDI Module:
    * ASG for Controller, NICE DCV Broker, NICE DCV Connection Gateway
    * Network Load Balancer
    * Security Groups
    * AWS Backups for eVDI Hosts
    * Additional components for eVDI functionality.
    """

    def __init__(self, scope: constructs.Construct, cluster_name: str, aws_region: str, aws_profile: str, module_id: str, deployment_id: str, termination_protection: bool = True, env: cdk.Environment = None):

        super().__init__(
            scope=scope,
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            module_id=module_id,
            deployment_id=deployment_id,
            termination_protection=termination_protection,
            description=f'ModuleId: {module_id}, Cluster: {cluster_name}, Version: {ideaadministrator.props.current_release_version}',
            tags={
                constants.IDEA_TAG_MODULE_ID: module_id,
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.COMPONENT_DCV_BROKER = 'broker'
        self.COMPONENT_DCV_CONNECTION_GATEWAY = 'gateway'
        self.COMPONENT_CONTROLLER = 'controller'
        self.CONFIG_MAPPING = {
            self.COMPONENT_CONTROLLER: 'controller',
            self.COMPONENT_DCV_CONNECTION_GATEWAY: 'dcv_connection_gateway',
            self.COMPONENT_DCV_BROKER: 'dcv_broker'
        }
        self.COMPONENT_DCV_HOST = 'host'

        self.BROKER_CLIENT_COMMUNICATION_PORT = self.context.config().get_int('virtual-desktop-controller.dcv_broker.client_communication_port', required=True)
        self.BROKER_AGENT_COMMUNICATION_PORT = self.context.config().get_int('virtual-desktop-controller.dcv_broker.agent_communication_port', required=True)
        self.BROKER_GATEWAY_COMMUNICATION_PORT = self.context.config().get_int('virtual-desktop-controller.dcv_broker.gateway_communication_port', required=True)

        self.CLUSTER_ENDPOINTS_LAMBDA_ARN = self.context.config().get_string('cluster.cluster_endpoints_lambda_arn', required=True)

        self.aws = AwsClientProvider(options=AWSClientProviderOptions(profile=aws_profile, region=aws_region))

        self.cluster = ExistingSocaCluster(self.context, self.stack)
        self.arn_builder = ArnBuilder(self.context.config())

        self.oauth2_client_secret: Optional[OAuthClientIdAndSecret] = None

        self.custom_credential_broker_lambda_function: Optional[LambdaFunction] = None

        self.custom_credential_broker_api_gateway_rest_api: Optional[APIGatewayRestApi] = None
        self.custom_credential_broker_api_gateway_rest_api_request_validator: Optional[apigateway.RequestValidator] = None
        self.object_storage_temp_credentials: Optional[apigateway.Resource] = None
        self.object_storage_temp_credentials_path_part: Optional[str] = None
        self.custom_credential_broker_api_gateway_vpc_endpoint: Optional[VpcInterfaceEndpoint] = None
        self.custom_credential_broker_api_gateway_vpc_endpoint_security_group: Optional[VpcEndpointSecurityGroup] = None
        self.custom_credential_broker_lambda_role: Optional[Role] = None
        self.s3_mount_base_bucket_read_only_role: Optional[Role] = None
        self.s3_mount_base_bucket_read_write_role: Optional[Role] = None

        self.dcv_host_role: Optional[Role] = None
        self.controller_role: Optional[Role] = None
        self.dcv_broker_role: Optional[Role] = None
        self.scheduled_event_transformer_lambda_role: Optional[Role] = None
        self.dcv_host_instance_profile: Optional[InstanceProfile] = None

        self.dcv_host_security_group: Optional[VirtualDesktopBastionAccessSecurityGroup] = None
        self.controller_security_group: Optional[VirtualDesktopPublicLoadBalancerAccessSecurityGroup] = None
        self.dcv_connection_gateway_security_group: Optional[VirtualDesktopPublicLoadBalancerAccessSecurityGroup] = None
        self.dcv_broker_security_group: Optional[VirtualDesktopBastionAccessSecurityGroup] = None
        self.dcv_broker_alb_security_group: Optional[VirtualDesktopBastionAccessSecurityGroup] = None

        self.dcv_connection_gateway_self_signed_cert: Optional[cdk.CustomResource] = None
        self.external_nlb: Optional[elbv2.NetworkLoadBalancer] = None

        self.event_sqs_queue: Optional[SQSQueue] = None
        self.controller_sqs_queue: Optional[SQSQueue] = None
        self.ssm_commands_sns_topic: Optional[SNSTopic] = None
        self.ssm_command_pass_role: Optional[Role] = None

        self.controller_auto_scaling_group: Optional[asg.AutoScalingGroup] = None
        self.dcv_broker_autoscaling_group: Optional[asg.AutoScalingGroup] = None
        self.dcv_connection_gateway_autoscaling_group: Optional[asg.AutoScalingGroup] = None

        self.backup_plan: Optional[BackupPlan] = None

        self.user_pool = self.lookup_user_pool()

        self.resource_server = None
        self.build_oauth2_client()
        self.update_cluster_manager_client_scopes()

        self.build_custom_credential_broker_infra()

        self.build_sqs_queues()
        self.build_scheduled_event_notification_infra()
        self.subscribe_to_ec2_notification_events()

        self.build_virtual_desktop_controller()
        self.build_dcv_broker()
        self.build_dcv_connection_gateway()
        self.build_dcv_host_infra()

        self.build_controller_ssm_commands_notification_infra()
        self.build_backups()

        self.setup_egress_rules_for_quic()
        self.build_cluster_settings()

    def setup_egress_rules_for_quic(self):
        quic_supported = self.context.config().get_bool('virtual-desktop-controller.dcv_session.quic_support', required=True)
        if not quic_supported:
            return

        self.dcv_host_security_group.add_egress_rule(
            ec2.Peer.ipv4('0.0.0.0/0'),
            ec2.Port.udp_range(0, 65535),
            description='Allow all egress for UDP for QUIC Support on DCV Host'
        )

        self.dcv_connection_gateway_security_group.add_egress_rule(
            ec2.Peer.ipv4('0.0.0.0/0'),
            ec2.Port.udp_range(0, 65535),
            description='Allow all egress for UDP for QUIC Support on DCV Connection Gateway'
        )

    def build_sqs_queues(self):
        # a custom kms key is required for sqs so that sns can be given permissions as an event source for the vdc controller queue
        sqs_kms_key_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["kms:*"],
                    principals=[iam.AccountRootPrincipal()],
                    resources=["*"]),
                iam.PolicyStatement(
                    actions=["kms:GenerateDataKey", "kms:Decrypt", "kms:ReEncrypt*", "kms:DescribeKey", "kms:Encrypt"],
                    principals=[iam.ServicePrincipal('sns.amazonaws.com'), iam.ServicePrincipal('sqs.amazonaws.com')],
                    resources=["*"]),
            ]
        )

        self.sqs_kms_key = kms.Key(self.stack, "res-sqs-kms",
                                   enable_key_rotation=True,
                                   policy=sqs_kms_key_policy
                                   )

        self.sqs_kms_key.add_alias(f'{self.cluster_name}/sqs')

        self.event_sqs_queue = SQSQueue(
            self.context, 'virtual-desktop-controller-events-queue', self.stack,
            queue_name=f'{self.cluster_name}-{self.module_id}-events.fifo',
            fifo=True,
            fifo_throughput_limit=sqs.FifoThroughputLimit.PER_MESSAGE_GROUP_ID,
            deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
            content_based_deduplication=True,
            encryption_master_key=self.context.config().get_string('cluster.sqs.kms_key_id'),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=60,
                queue=SQSQueue(
                    self.context, 'virtual-desktop-controller-events-queue-dlq', self.stack,
                    queue_name=f'{self.cluster_name}-{self.module_id}-events-dlq.fifo',
                    fifo=True,
                    fifo_throughput_limit=sqs.FifoThroughputLimit.PER_MESSAGE_GROUP_ID,
                    deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
                    content_based_deduplication=True,
                    encryption_master_key=self.context.config().get_string('cluster.sqs.kms_key_id'),
                    is_dead_letter_queue=True
                )
            )
        )
        self.add_common_tags(self.event_sqs_queue)
        self.add_common_tags(self.event_sqs_queue.dead_letter_queue.queue)

        self.controller_sqs_queue = SQSQueue(
            self.context, 'virtual-desktop-controller-queue', self.stack,
            queue_name=f'{self.cluster_name}-{self.module_id}-controller',
            encryption_master_key=self.sqs_kms_key.key_id,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=30,
                queue=SQSQueue(
                    self.context, 'virtual-desktop-controller-queue-dlq', self.stack,
                    queue_name=f'{self.cluster_name}-{self.module_id}-controller-dlq',
                    encryption_master_key=self.sqs_kms_key.key_id,
                    is_dead_letter_queue=True
                )
            )
        )
        self.add_common_tags(self.controller_sqs_queue)
        self.add_common_tags(self.controller_sqs_queue.dead_letter_queue.queue)

    def build_controller_ssm_commands_notification_infra(self):
        self.ssm_command_pass_role = Role(
            context=self.context,
            name=f'{self.module_id}-ssm-commands-sns-topic-role',
            scope=self.stack,
            assumed_by=['ssm'],
            description='IAM role for SSM Commands to send notifications via SNS'
        )

        self.ssm_command_pass_role.attach_inline_policy(Policy(
            context=self.context,
            name=f'{self.cluster_name}-{self.module_id}-ssm-commands-sns-topic-role-policy',
            scope=self.stack,
            policy_template_name='controller-ssm-command-pass-role.yml'
        ))
        self.ssm_command_pass_role.grant_pass_role(self.controller_role)

        self.ssm_commands_sns_topic = SNSTopic(
            self.context, 'virtual-desktop-controller-sns-topic', self.stack,
            topic_name=f'{self.cluster_name}-{self.module_id}-ssm-commands-sns-topic',
            display_name=f'{self.cluster_name}-{self.module_id}-ssm-commands-topic',
            master_key=self.context.config().get_string('cluster.sns.kms_key_id')
        )
        self.add_common_tags(self.ssm_commands_sns_topic)
        self.ssm_commands_sns_topic.add_subscription(sns_subscription.SqsSubscription(
            queue=self.controller_sqs_queue,
            dead_letter_queue=self.controller_sqs_queue.dead_letter_queue.queue
        ))

    def subscribe_to_ec2_notification_events(self):
        ec2_event_sns_topic = sns.Topic.from_topic_arn(
            self.stack, f'{self.cluster_name}-{self.module_id}-ec2-state-change-topic',
            self.context.config().get_string('cluster.ec2.state_change_notifications_sns_topic_arn', required=True)
        )

        ec2_event_sns_topic.add_subscription(sns_subscription.SqsSubscription(
            queue=self.controller_sqs_queue,
            dead_letter_queue=self.controller_sqs_queue.dead_letter_queue.queue,
            filter_policy={
                IDEA_TAG_MODULE_ID.replace(':', '_'): sns.SubscriptionFilter.string_filter(
                    allowlist=[self.module_id]
                )
            }
        ))

    def build_scheduled_event_notification_infra(self):
        lambda_name = f'{self.module_id}-scheduled-event-transformer'
        self.scheduled_event_transformer_lambda_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            assumed_by=['lambda'],
            description=f'{lambda_name}-role'
        )

        self.scheduled_event_transformer_lambda_role.attach_inline_policy(Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='controller-scheduled-event-transformer-lambda.yml'
        ))

        scheduled_event_transformer_lambda = LambdaFunction(
            context=self.context,
            name=lambda_name,
            description=f'{self.module_id} lambda to intercept all scheduled events and transform to the required event object.',
            scope=self.stack,
            environment={
                'IDEA_CONTROLLER_EVENTS_QUEUE_URL': self.event_sqs_queue.queue_url
            },
            timeout_seconds=180,
            role=self.scheduled_event_transformer_lambda_role,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_controller_scheduled_event_transformer',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            )
        )

        schedule_trigger_rule = events.Rule(
            scope=self.stack,
            id=f'{self.cluster_name}-{self.module_id}-schedule-rule',
            enabled=True,
            rule_name=f'{self.cluster_name}-{self.module_id}-schedule-rule',
            description='Event Rule to Trigger schedule check EVERY 30 minutes on VDC Controller',
            schedule=Schedule.cron(
                minute='0/30'
            )
        )

        schedule_trigger_rule.add_target(events_targets.LambdaFunction(
            scheduled_event_transformer_lambda
        ))
        self.add_common_tags(schedule_trigger_rule)

    def build_oauth2_client(self):

        # add resource server
        self.resource_server = self.user_pool.add_resource_server(
            id='resource-server',
            identifier=self.module_id,
            scopes=[
                cognito.ResourceServerScope(scope_name='read', scope_description='Allow Read Access'),
                cognito.ResourceServerScope(scope_name='write', scope_description='Allow Write Access')
            ]
        )

        # dcv session manager / external auth
        # refer: https://docs.aws.amazon.com/dcv/latest/sm-admin/ext-auth.html
        # todo - make an api call to check if "dcv-session-manager" resource server already exists in user pool
        #  this is to cover cases for blue/green deployments when an additional instance of eVDI module is deployed
        session_manager_resource_server = self.user_pool.add_resource_server(
            id='dcv-session-manager-resource-server',
            identifier='dcv-session-manager',
            scopes=[
                cognito.ResourceServerScope(scope_name='sm_scope', scope_description='sm_scope')
            ]
        )

        # add new client to user pool
        client = self.user_pool.add_client(
            id=f'{self.module_id}-client',
            access_token_validity=cdk.Duration.hours(1),
            generate_secret=True,
            id_token_validity=cdk.Duration.hours(1),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(client_credentials=True),
                scopes=[
                    cognito.OAuthScope.custom(f'{self.module_id}/read'),
                    cognito.OAuthScope.custom(f'{self.module_id}/write'),
                    cognito.OAuthScope.custom(f'{self.context.config().get_module_id(constants.MODULE_CLUSTER_MANAGER)}/read'),
                    cognito.OAuthScope.custom('dcv-session-manager/sm_scope')
                ]
            ),
            refresh_token_validity=cdk.Duration.days(30),
            user_pool_client_name=self.module_id
        )
        client.node.add_dependency(session_manager_resource_server)
        client.node.add_dependency(self.resource_server)

        # read secret value by invoking custom resource
        oauth_credentials_lambda_arn = self.context.config().get_string('identity-provider.cognito.oauth_credentials_lambda_arn', required=True)
        client_secret = cdk.CustomResource(
            scope=self.stack,
            id=f'{self.module_id}-creds',
            service_token=oauth_credentials_lambda_arn,
            properties={
                'UserPoolId': self.user_pool.user_pool_id,
                'ClientId': client.user_pool_client_id
            },
            resource_type='Custom::GetOAuthCredentials'
        )

        # save client id and client secret to AWS Secrets Manager
        self.oauth2_client_secret = OAuthClientIdAndSecret(
            context=self.context,
            secret_name_prefix=self.module_id,
            module_name=constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER,
            scope=self.stack,
            client_id=client.user_pool_client_id,
            client_secret=client_secret.get_att_string('ClientSecret')
        )

    def update_cluster_manager_client_scopes(self):
        """
        Allow the cluster manager client to access VDC APIs via the VDC scopes
        :return:
        """
        lambda_name = f'{self.module_id}-update-cluster-manager-client-scope'
        update_cluster_manager_client_scope_lambda_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            assumed_by=['lambda'],
            description=f'{lambda_name}-role'
        )

        update_cluster_manager_client_scope_lambda_role.attach_inline_policy(Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='add-to-user-pool-client-scopes.yml'
        ))
        update_cluster_manager_client_scope_lambda = LambdaFunction(
            context=self.context,
            name=lambda_name,
            scope=self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='add_to_user_pool_client_scopes',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            description='Update cluster manager client scope for accessing vdc',
            timeout_seconds=180,
            role=update_cluster_manager_client_scope_lambda_role,
        )
        update_cluster_manager_client_scope_lambda.node.add_dependency(self.resource_server)

        cdk.CustomResource(
            self.stack,
            f'{self.cluster_name}-update-client-scope',
            service_token=update_cluster_manager_client_scope_lambda.function_arn,
            properties={
                'cluster_name': self.cluster_name,
                'module_id': self.context.config().get_module_id(constants.MODULE_CLUSTER_MANAGER),
                'user_pool_id': self.user_pool.user_pool_id,
                'o_auth_scopes_to_add': [
                    f'{self.context.config().get_module_id(constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)}/read',
                    f'{self.context.config().get_module_id(constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER)}/write',
                ]
            },
            resource_type='Custom::UpdateClusterManagerClient'
        )

    def build_custom_credential_broker_infra(self):
        lambda_name = f'{self.module_id}-custom-credential-broker-lambda'
        api_gateway_name = f'{self.module_id}-custom-credential-broker-api-gateway'

        self.custom_credential_broker_lambda_role = Role(
            context=self.context,
            name=app_constants.CUSTOM_CREDENTIAL_BROKER_ROLE_NAME,
            scope=self.stack,
            assumed_by=['lambda'],
            description=f'{lambda_name}-role',
        )

        self.s3_mount_base_bucket_read_only_role = Role(
            context=self.context,
            name=app_constants.S3_MOUNT_BUCKET_READ_ONLY_ROLE_NAME,
            scope=self.stack,
            description='Base bucket role for read only access to S3 buckets onboarded to RES.',
            assumed_by=['lambda'],
            inline_policies=[
                Policy(
                    context=self.context,
                    name='S3MountReadOnlyPolicy',
                    scope=self.stack,
                    policy_template_name='s3-mount-base-bucket-read-only.yml'
                )
            ],
        )
        self.s3_mount_base_bucket_read_write_role = Role(
            context=self.context,
            name=app_constants.S3_MOUNT_BUCKET_READ_WRITE_ROLE_NAME,
            scope=self.stack,
            description='Base bucket role for read and write access to S3 buckets onboarded to RES.',
            assumed_by=['lambda'],
            inline_policies=[
                Policy(
                    context=self.context,
                    name='S3MountReadWritePolicy',
                    scope=self.stack,
                    policy_template_name='s3-mount-base-bucket-read-write.yml'
                )
            ],
        )
        self.s3_mount_base_bucket_read_only_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['sts:AssumeRole'],
                principals=[
                    iam.ArnPrincipal(self.custom_credential_broker_lambda_role.role_arn)
                ]
            )
        )
        self.s3_mount_base_bucket_read_write_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['sts:AssumeRole'],
                principals=[
                    iam.ArnPrincipal(self.custom_credential_broker_lambda_role.role_arn)
                ]
            )
        )
        variable = SocaAnyPayload()
        variable.s3_bucket_iam_role_resource_tag_value = constants.S3_BUCKET_IAM_ROLE_RESOURCE_TAG_VALUE
        custom_credential_broker_lambda_role_policy = ManagedPolicy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            managed_policy_name=f'{self.cluster_name}-{self.aws_region}-{lambda_name}-policy',
            description='Required policy for RES Custom Credential Broker Lambda.',
            policy_template_name='custom-credential-broker.yml',
            vars=variable
        )
        self.custom_credential_broker_lambda_role.add_managed_policy(custom_credential_broker_lambda_role_policy)

        # Determine if we have a specific list of subnets configured for VDI
        configured_vdi_subnets = self.context.config().get_list(
            'vdc.dcv_session.network.private_subnets',
            default=[]
        )
        # Required=True as these should always be available, and we want to error otherwise
        cluster_private_subnets = self.context.config().get_list(
            'cluster.network.private_subnets',
            required=True
        )

        if configured_vdi_subnets:
            vdi_cidr_blocks = [
                subnet['CidrBlock'] for subnet in self.aws.ec2().describe_subnets(SubnetIds=configured_vdi_subnets)['Subnets']
            ]
        else:
            vdi_cidr_blocks = [
                subnet['CidrBlock'] for subnet in self.aws.ec2().describe_subnets(SubnetIds=cluster_private_subnets)['Subnets']
            ]

        custom_credential_broker_security_group = VirtualDesktopCustomCredentialBrokerSecurityGroup(
            context=self.context,
            name=f'{lambda_name}-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc,
            component_name="Custom Credential Broker",
            vdi_cidr_blocks=vdi_cidr_blocks,
        )

        self.custom_credential_broker_lambda_function = LambdaFunction(
            context=self.context,
            name=lambda_name,
            description=f'{self.module_id} lambda to provide temporary credentials for mounting object storage to virtual desktop infrastructure (VDI) instances.',
            scope=self.stack,
            vpc=self.cluster.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=self.cluster.private_subnets),
            security_groups=[custom_credential_broker_security_group],
            environment={
                "CLUSTER_NAME": f'{self.cluster_name}',
                "CLUSTER_SETTINGS_TABLE_NAME": f'{self.cluster_name}.cluster-settings',
                "DCV_HOST_DB_HASH_KEY": app_constants.DCV_HOST_DB_HASH_KEY,
                "DCV_HOST_DB_IDEA_SESSION_ID_KEY": app_constants.DCV_HOST_DB_IDEA_SESSION_ID_KEY,
                "DCV_HOST_DB_IDEA_SESSION_OWNER_KEY": app_constants.DCV_HOST_DB_IDEA_SESSION_OWNER_KEY,
                "MODULE_ID": f'{self.module_id}',
                "OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX": constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX,
                "OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX": constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX,
                "OBJECT_STORAGE_NO_CUSTOM_PREFIX": constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX,
                "READ_AND_WRITE_ROLE_NAME_ARN": self.arn_builder.get_iam_arn("s3-mount-bucket-read-write"),
                "READ_ONLY_ROLE_NAME_ARN": self.arn_builder.get_iam_arn("s3-mount-bucket-read-only"),
                "SHARED_STORAGE_PREFIX": f'{constants.MODULE_SHARED_STORAGE}',
                "STORAGE_PROVIDER_S3_BUCKET": constants.STORAGE_PROVIDER_S3_BUCKET,
                "USER_SESSION_OWNER_KEY": app_constants.USER_SESSION_DB_HASH_KEY,
                "USER_SESSION_SESSION_ID_KEY": app_constants.USER_SESSION_DB_RANGE_KEY
            },
            role=self.custom_credential_broker_lambda_role,
            timeout_seconds=60,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='res_custom_credential_broker',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
        )
        self.custom_credential_broker_lambda_function.node.add_dependency(custom_credential_broker_lambda_role_policy)
        self.add_common_tags(self.custom_credential_broker_lambda_function)

        custom_credential_broker_api_gateway_rest_api_resource_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["execute-api:Invoke"],
                    principals=[iam.ServicePrincipal("ec2.amazonaws.com")],
                    resources=[self.arn_builder.custom_credential_broker_api_gateway_execute_api_arn('*')],
                    conditions={
                        "IpAddress": {
                            "aws:SourceIp": vdi_cidr_blocks
                        }
                    }
                ),
            ]
        )

        custom_credential_broker_api_gateway_rest_api_access_logs = logs.LogGroup(
            scope=self.stack,
            id=f'{self.module_id}-custom-credential-broker-api-gateway-access-logs',
            retention=logs.RetentionDays.TEN_YEARS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.custom_credential_broker_api_gateway_vpc_endpoint_security_group = VpcEndpointSecurityGroup(
            context=self.context,
            scope=self.stack,
            vpc=self.cluster.vpc,
            name='Custom Credential Broker API Gateway VPC Endpoint Security Group',
        )

        create_tags = CreateTagsCustomResource(
            context=self.context,
            scope=self.stack,
        )

        self.custom_credential_broker_api_gateway_vpc_endpoint = VpcInterfaceEndpoint(
            context=self.context,
            scope=self.stack,
            vpc=self.cluster.vpc,
            service="execute-api",
            vpc_endpoint_security_group=self.custom_credential_broker_api_gateway_vpc_endpoint_security_group,
            create_tags=create_tags,
            lookup_supported_azs=False
        )

        self.custom_credential_broker_api_gateway_rest_api = APIGatewayRestApi(
            context=self.context,
            scope=self.stack,
            name=api_gateway_name,
            description=f'{self.module_id} api gateway to provide temporary credentials for mounting object storage to virtual desktop infrastructure (VDI) instances.',
            policy=custom_credential_broker_api_gateway_rest_api_resource_policy,
            deploy_options=apigateway.StageOptions(stage_name=constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_STAGE,
                                                   access_log_destination=apigateway.LogGroupLogDestination(custom_credential_broker_api_gateway_rest_api_access_logs),
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
                                                   )),
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.PRIVATE],
                vpc_endpoints=[self.custom_credential_broker_api_gateway_vpc_endpoint.get_endpoint()],
            ),
            default_method_options=apigateway.MethodOptions(authorization_type=apigateway.AuthorizationType.IAM),
            rest_api_name=api_gateway_name,
        )
        self.object_storage_temp_credentials_path_part = constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE
        self.object_storage_temp_credentials = self.custom_credential_broker_api_gateway_rest_api.root.add_resource(
            path_part=self.object_storage_temp_credentials_path_part
        )

        self.object_storage_temp_credentials.add_method(
            http_method="GET",
            integration=apigateway.LambdaIntegration(
                handler=self.custom_credential_broker_lambda_function
            ),
            authorization_type=apigateway.AuthorizationType.IAM
        )

        self.custom_credential_broker_api_gateway_rest_api.node.add_dependency(self.custom_credential_broker_lambda_function)

        self.custom_credential_broker_api_gateway_rest_api_request_validator = apigateway.RequestValidator(
            rest_api=self.custom_credential_broker_api_gateway_rest_api,
            scope=self.stack,
            id="custom-credential-broker-api-gateway-validator",
            validate_request_body=True,
            validate_request_parameters=True,
        )

        self.add_nag_suppression(
            construct=self.custom_credential_broker_api_gateway_rest_api,
            suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-APIG6', reason='This is a private API Gateway endpoint')],
            apply_to_children=True
        )

        self.add_nag_suppression(
            construct=self.custom_credential_broker_api_gateway_rest_api,
            suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-COG4', reason='This endpoint uses AWS IAM as the authorizer')],
            apply_to_children=True
        )

        self.add_nag_suppression(
            construct=self.custom_credential_broker_api_gateway_rest_api,
            suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-IAM4', reason='Suppressing AwsSolutions-IAM4 for CloudWatch logs role')],
            apply_to_children=True
        )

    def build_dcv_host_infra(self):
        self.dcv_host_role = self._build_iam_role(
            role_description=f'IAM role assigned to virtual-desktop-{self.COMPONENT_DCV_HOST}',
            component_name=self.COMPONENT_DCV_HOST,
            component_jinja='virtual-desktop-dcv-host.yml'
        )
        self.dcv_host_role.grant_pass_role(self.controller_role)

        self.dcv_host_instance_profile = InstanceProfile(
            context=self.context,
            name=f'{self.module_id}-{self.COMPONENT_DCV_HOST}-instance-profile',
            scope=self.stack,
            roles=[self.dcv_host_role]
        )
        self.dcv_host_security_group = VirtualDesktopBastionAccessSecurityGroup(
            context=self.context,
            name=f'{self.module_id}-dcv-host-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc,
            bastion_host_security_group=self.cluster.get_security_group('bastion-host'),
            description='Security Group for DCV Host',
            directory_service_access=True,
            component_name='DCV Host'
        )

    def _build_alb(self, component_name: str, internet_facing: bool, security_group: SecurityGroup) -> elbv2.ApplicationLoadBalancer:
        return elbv2.ApplicationLoadBalancer(
            self.stack,
            f'{self.cluster_name}-{self.module_id}-{component_name}-alb',
            load_balancer_name=f'{self.cluster_name}-{self.module_id}-alb',
            security_group=security_group,
            vpc=self.cluster.vpc,
            internet_facing=internet_facing
        )

    def build_dcv_broker(self):
        # client target group and registration
        client_target_group = elbv2.ApplicationTargetGroup(
            self.stack,
            f'{self.COMPONENT_DCV_BROKER}-client-target-group',
            port=self.BROKER_CLIENT_COMMUNICATION_PORT,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            vpc=self.cluster.vpc,
            target_group_name=self.get_target_group_name(f'{self.COMPONENT_DCV_BROKER}-c')
        )
        client_target_group.configure_health_check(
            enabled=True,
            path='/health'
        )

        cdk.CustomResource(
            self.stack,
            'dcv-broker-client-endpoint',
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                'endpoint_name': 'broker-client-endpoint',
                'listener_arn': self.context.config().get_string('cluster.load_balancers.internal_alb.dcv_broker_client_listener_arn', required=True),
                'priority': 0,
                'default_action': True,
                'actions': [
                    {
                        'Type': 'forward',
                        'TargetGroupArn': client_target_group.target_group_arn
                    }
                ]
            },
            resource_type='Custom::DcvBrokerClientEndpointInternal'
        )

        # agent target group and registration
        agent_target_group = elbv2.ApplicationTargetGroup(
            self.stack,
            f'{self.COMPONENT_DCV_BROKER}-agent-target-group',
            port=self.BROKER_AGENT_COMMUNICATION_PORT,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            vpc=self.cluster.vpc,
            target_group_name=self.get_target_group_name(f'{self.COMPONENT_DCV_BROKER}-a')
        )
        agent_target_group.configure_health_check(
            enabled=True,
            path='/health'
        )

        cdk.CustomResource(
            self.stack,
            'dcv-broker-agent-endpoint',
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                'endpoint_name': 'broker-client-endpoint',
                'listener_arn': self.context.config().get_string('cluster.load_balancers.internal_alb.dcv_broker_agent_listener_arn', required=True),
                'priority': 0,
                'default_action': True,
                'actions': [
                    {
                        'Type': 'forward',
                        'TargetGroupArn': agent_target_group.target_group_arn
                    }
                ]
            },
            resource_type='Custom::DcvBrokerAgentEndpointInternal'
        )

        # gateway target group and registration
        gateway_target_group = elbv2.ApplicationTargetGroup(
            self.stack,
            f'{self.COMPONENT_DCV_BROKER}-gateway-target-group',
            port=self.BROKER_GATEWAY_COMMUNICATION_PORT,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            vpc=self.cluster.vpc,
            target_group_name=self.get_target_group_name(f'{self.COMPONENT_DCV_BROKER}-g')
        )
        gateway_target_group.configure_health_check(
            enabled=True,
            path='/health'
        )

        cdk.CustomResource(
            self.stack,
            'dcv-broker-gateway-endpoint',
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                'endpoint_name': 'broker-gateway-endpoint',
                'listener_arn': self.context.config().get_string('cluster.load_balancers.internal_alb.dcv_broker_gateway_listener_arn', required=True),
                'priority': 0,
                'default_action': True,
                'actions': [
                    {
                        'Type': 'forward',
                        'TargetGroupArn': gateway_target_group.target_group_arn
                    }
                ]
            },
            resource_type='Custom::DcvBrokerGatewayEndpointInternal'
        )

        # security group
        self.dcv_broker_security_group = VirtualDesktopBastionAccessSecurityGroup(
            context=self.context,
            name=f'{self.module_id}-{self.COMPONENT_DCV_BROKER}-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc,
            bastion_host_security_group=self.cluster.get_security_group('bastion-host'),
            description='Security Group for Virtual Desktop DCV Broker',
            directory_service_access=False,
            component_name='DCV Broker'
        )

        # autoscaling group
        dcv_broker_package_uri = self.stack.node.try_get_context('dcv_broker_bootstrap_package_uri')
        https_proxy = self.context.config().get_string('cluster.network.https_proxy', required=False, default='')
        no_proxy = self.context.config().get_string('cluster.network.no_proxy', required=False, default='')
        proxy_config = {}
        if Utils.is_not_empty(https_proxy):
            proxy_config = {
                'http_proxy': https_proxy,
                'https_proxy': https_proxy,
                'no_proxy': no_proxy
            }

        if Utils.is_empty(dcv_broker_package_uri):
            dcv_broker_package_uri = 'not-provided'

        broker_userdata = BootstrapUserDataBuilder(
            aws_region=self.aws_region,
            bootstrap_package_uri=dcv_broker_package_uri,
            install_commands=[
                '/bin/bash dcv-broker/setup.sh'
            ],
            infra_config={
                'BROKER_CLIENT_TARGET_GROUP_ARN': '${__BROKER_CLIENT_TARGET_GROUP_ARN__}',
                'CONTROLLER_EVENTS_QUEUE_URL': '${__CONTROLLER_EVENTS_QUEUE_URL__}'
            },
            proxy_config=proxy_config,
            bootstrap_source_dir_path=ideaadministrator.props.bootstrap_source_dir,
            base_os=self.context.config().get_string('virtual-desktop-controller.dcv_broker.autoscaling.base_os', required=True)
        ).build()
        substituted_userdata = cdk.Fn.sub(broker_userdata, {
            '__BROKER_CLIENT_TARGET_GROUP_ARN__': client_target_group.target_group_arn,
            '__CONTROLLER_EVENTS_QUEUE_URL__': self.event_sqs_queue.queue_url
        })

        self.dcv_broker_role = self._build_iam_role(
            role_description=f'IAM role assigned to virtual-desktop-{self.COMPONENT_DCV_BROKER}',
            component_name=self.COMPONENT_DCV_BROKER,
            component_jinja='virtual-desktop-dcv-broker.yml'
        )

        self.dcv_broker_autoscaling_group = self._build_auto_scaling_group(
            component_name=self.COMPONENT_DCV_BROKER,
            security_group=self.dcv_broker_security_group,
            iam_role=self.dcv_broker_role,
            substituted_userdata=substituted_userdata,
            node_type=constants.NODE_TYPE_INFRA
        )
        self.dcv_broker_autoscaling_group.node.add_dependency(self.event_sqs_queue)

        # receiving error jsii.errors.JSIIError: Cannot add AutoScalingGroup to 2nd Target Group
        # if same ASG is added to both internal and external target groups.
        # workaround below - reference to https://github.com/aws/aws-cdk/issues/5667#issuecomment-827549394
        self.dcv_broker_autoscaling_group.node.default_child.target_group_arns = [
            agent_target_group.target_group_arn,
            client_target_group.target_group_arn,
            gateway_target_group.target_group_arn
        ]

    def _build_iam_role(self, role_description: str, component_name: str, component_jinja: str) -> Role:
        ec2_managed_policies = self.get_ec2_instance_managed_policies()

        role = Role(
            context=self.context,
            name=f'{self.module_id}-{component_name}-role',
            scope=self.stack,
            description=role_description,
            assumed_by=['ssm', 'ec2'],
            managed_policies=ec2_managed_policies
        )
        variables = SocaAnyPayload()
        variables.role_arn = role.role_arn
        role.attach_inline_policy(
            Policy(
                context=self.context,
                name=f'{self.cluster_name}-{self.module_id}-{component_name}-policy',
                scope=self.stack,
                policy_template_name=component_jinja,
                vars=variables
            )
        )
        return role

    def build_virtual_desktop_controller(self):
        self.controller_security_group = VirtualDesktopPublicLoadBalancerAccessSecurityGroup(
            context=self.context,
            name=f'{self.module_id}-{self.COMPONENT_CONTROLLER}-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc,
            bastion_host_security_group=self.cluster.get_security_group('bastion-host'),
            public_loadbalancer_security_group=self.cluster.get_security_group('external-load-balancer'),
            description='Security Group for Virtual Desktop Controller',
            directory_service_access=True,
            component_name='Virtual Desktop Controller'
        )

        controller_bootstrap_package_uri = self.stack.node.try_get_context('controller_bootstrap_package_uri')
        if Utils.is_empty(controller_bootstrap_package_uri):
            controller_bootstrap_package_uri = 'not-provided'

        self.controller_role = self._build_iam_role(
            role_description=f'IAM role assigned to virtual-desktop-{self.COMPONENT_CONTROLLER}',
            component_name=self.COMPONENT_CONTROLLER,
            component_jinja='virtual-desktop-controller.yml'
        )

        https_proxy = self.context.config().get_string('cluster.network.https_proxy', required=False, default='')
        no_proxy = self.context.config().get_string('cluster.network.no_proxy', required=False, default='')
        proxy_config = {}
        if Utils.is_not_empty(https_proxy):
            proxy_config = {
                'http_proxy': https_proxy,
                'https_proxy': https_proxy,
                'no_proxy': no_proxy
            }

        self.controller_auto_scaling_group = self._build_auto_scaling_group(
            component_name=self.COMPONENT_CONTROLLER,
            security_group=self.controller_security_group,
            iam_role=self.controller_role,
            substituted_userdata=cdk.Fn.sub(BootstrapUserDataBuilder(
                aws_region=self.aws_region,
                bootstrap_package_uri=controller_bootstrap_package_uri,
                install_commands=[
                    '/bin/bash virtual-desktop-controller/setup.sh'
                ],
                proxy_config=proxy_config,
                bootstrap_source_dir_path=ideaadministrator.props.bootstrap_source_dir,
                base_os=self.context.config().get_string('virtual-desktop-controller.controller.autoscaling.base_os', required=True)
            ).build()),
            node_type=constants.NODE_TYPE_APP
        )

        self.controller_auto_scaling_group.node.add_dependency(self.event_sqs_queue)
        self.controller_auto_scaling_group.node.add_dependency(self.controller_sqs_queue)

        # external target group
        external_target_group = elbv2.ApplicationTargetGroup(
            self.stack,
            'controller-target-group-ext',
            port=8443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            protocol_version=elbv2.ApplicationProtocolVersion.HTTP1,
            target_type=elbv2.TargetType.INSTANCE,
            vpc=self.cluster.vpc,
            target_group_name=self.get_target_group_name('vdc-ext')
        )
        external_target_group.configure_health_check(
            enabled=True,
            path='/healthcheck'
        )

        external_https_listener_arn = self.context.config().get_string('cluster.load_balancers.external_alb.https_listener_arn', required=True)
        path_patterns = self.context.config().get_list('virtual-desktop-controller.controller.endpoints.external.path_patterns', required=True)
        priority = self.context.config().get_int('virtual-desktop-controller.controller.endpoints.external.priority', required=True)
        cdk.CustomResource(
            self.stack,
            'controller-endpoint-ext',
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                'endpoint_name': f'{self.module_id}-controller-endpoint-ext',
                'listener_arn': external_https_listener_arn,
                'priority': priority,
                'conditions': [
                    {
                        'Field': 'path-pattern',
                        'Values': path_patterns
                    }
                ],
                'actions': [
                    {
                        'Type': 'forward',
                        'TargetGroupArn': external_target_group.target_group_arn
                    }
                ]
            },
            resource_type='Custom::ControllerEndpointExternal'
        )

        # internal target group
        internal_target_group = elbv2.ApplicationTargetGroup(
            self.stack,
            'controller-target-group-int',
            port=8443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            protocol_version=elbv2.ApplicationProtocolVersion.HTTP1,
            target_type=elbv2.TargetType.INSTANCE,
            vpc=self.cluster.vpc,
            target_group_name=self.get_target_group_name('vdc-int')
        )
        internal_target_group.configure_health_check(
            enabled=True,
            path='/healthcheck'
        )

        internal_https_listener_arn = self.context.config().get_string('cluster.load_balancers.internal_alb.https_listener_arn', required=True)
        path_patterns = self.context.config().get_list('virtual-desktop-controller.controller.endpoints.internal.path_patterns', required=True)
        priority = self.context.config().get_int('virtual-desktop-controller.controller.endpoints.internal.priority', required=True)
        cdk.CustomResource(
            self.stack,
            'controller-endpoint-int',
            service_token=self.CLUSTER_ENDPOINTS_LAMBDA_ARN,
            properties={
                'endpoint_name': f'{self.module_id}-controller-endpoint-int',
                'listener_arn': internal_https_listener_arn,
                'priority': priority,
                'conditions': [
                    {
                        'Field': 'path-pattern',
                        'Values': path_patterns
                    }
                ],
                'actions': [
                    {
                        'Type': 'forward',
                        'TargetGroupArn': internal_target_group.target_group_arn
                    }
                ]
            },
            resource_type='Custom::ControllerEndpointInternal'
        )

        # receiving error jsii.errors.JSIIError: Cannot add AutoScalingGroup to 2nd Target Group
        # if same ASG is added to both internal and external target groups.
        # workaround below - reference to https://github.com/aws/aws-cdk/issues/5667#issuecomment-827549394
        self.controller_auto_scaling_group.node.default_child.target_group_arns = [
            internal_target_group.target_group_arn,
            external_target_group.target_group_arn
        ]

    def _build_auto_scaling_group(self, component_name: str, security_group: SecurityGroup, iam_role: Role, substituted_userdata: str, node_type: str) -> asg.AutoScalingGroup:
        is_public = self.context.config().get_bool(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.public', False) and len(self.cluster.public_subnets) > 0
        if is_public:
            vpc_subnets = ec2.SubnetSelection(
                subnets=self.cluster.public_subnets
            )
        else:
            vpc_subnets = ec2.SubnetSelection(
                subnets=self.cluster.private_subnets
            )

        base_os = self.context.config().get_string(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.base_os', required=True)
        block_device_name = Utils.get_ec2_block_device_name(base_os)
        enable_detailed_monitoring = self.context.config().get_bool(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.enable_detailed_monitoring', default=False)
        metadata_http_tokens = self.context.config().get_string(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.metadata_http_tokens', required=True)

        kms_key_id = self.context.config().get_string('cluster.ebs.kms_key_id', required=False, default=None)
        if kms_key_id is not None:
            kms_key_arn = self.get_kms_key_arn(kms_key_id)
            ebs_kms_key = kms.Key.from_key_arn(scope=self.stack, id=f'{component_name}-ebs-kms-key', key_arn=kms_key_arn)
        else:
            ebs_kms_key = kms.Alias.from_alias_name(scope=self.stack, id=f'{component_name}-ebs-kms-key-default', alias_name='alias/aws/ebs')

        launch_template = ec2.LaunchTemplate(
            self.stack, f'{component_name}-lt',
            instance_type=ec2.InstanceType(self.context.config().get_string(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.instance_type', required=True)),
            machine_image=ec2.MachineImage.generic_linux({
                self.aws_region: self.context.config().get_string(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.instance_ami', required=True)
            }),
            security_group=security_group,
            user_data=ec2.UserData.custom(substituted_userdata),
            key_name=self.context.config().get_string('cluster.network.ssh_key_pair', required=True),
            block_devices=[ec2.BlockDevice(
                device_name=block_device_name,
                volume=ec2.BlockDeviceVolume(ebs_device=ec2.EbsDeviceProps(
                    encrypted=True,
                    kms_key=ebs_kms_key,
                    volume_size=self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.volume_size', default=200),
                    volume_type=ec2.EbsDeviceVolumeType.GP3
                ))
            )],
            role=iam_role,
            require_imdsv2=True if metadata_http_tokens == "required" else False,
            associate_public_ip_address=is_public
        )

        auto_scaling_group = asg.AutoScalingGroup(
            self.stack, f'{component_name}-asg',
            vpc=self.cluster.vpc,
            vpc_subnets=vpc_subnets,
            auto_scaling_group_name=f'{self.cluster_name}-{self.module_id}-{component_name}-asg',
            launch_template=launch_template,
            instance_monitoring=asg.Monitoring.DETAILED if enable_detailed_monitoring else asg.Monitoring.BASIC,
            group_metrics=[asg.GroupMetrics.all()],
            min_capacity=self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.min_capacity', default=1),
            max_capacity=self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.max_capacity', default=3),
            new_instances_protected_from_scale_in=self.context.config().get_bool(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.new_instances_protected_from_scale_in', default=True),
            cooldown=cdk.Duration.minutes(self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.cooldown_minutes', default=5)),
            default_instance_warmup=cdk.Duration.minutes(self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.default_instance_warmup', default=15)),
            health_check=asg.HealthCheck.elb(
                grace=cdk.Duration.minutes(self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.elb_healthcheck.grace_time_minutes', default=15))
            ),
            update_policy=asg.UpdatePolicy.rolling_update(
                max_batch_size=self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.rolling_update_policy.max_batch_size', default=1),
                min_instances_in_service=self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.rolling_update_policy.min_instances_in_service', default=1),
                pause_time=cdk.Duration.minutes(self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.rolling_update_policy.pause_time_minutes', default=15))
            ),
            termination_policies=[
                asg.TerminationPolicy.DEFAULT
            ]
        )

        auto_scaling_group.scale_on_cpu_utilization(
            'cpu-utilization-scaling-policy',
            target_utilization_percent=self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.cpu_utilization_scaling_policy.target_utilization_percent', default=80),
            estimated_instance_warmup=cdk.Duration.minutes(self.context.config().get_int(f'virtual-desktop-controller.{self.CONFIG_MAPPING[component_name]}.autoscaling.cpu_utilization_scaling_policy.estimated_instance_warmup_minutes', default=15))
        )

        cdk.Tags.of(auto_scaling_group).add(constants.IDEA_TAG_NODE_TYPE, node_type)
        cdk.Tags.of(auto_scaling_group).add(constants.IDEA_TAG_NAME, f'{self.cluster_name}-{self.module_id}-{component_name}')

        if not enable_detailed_monitoring:
            self.add_nag_suppression(
                construct=auto_scaling_group,
                suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-EC28', reason='detailed monitoring is a configurable option to save costs')],
                apply_to_children=True
            )

        self.add_nag_suppression(
            construct=auto_scaling_group,
            suppressions=[
                IdeaNagSuppression(rule_id='AwsSolutions-AS3', reason='ASG notifications scaling notifications can be managed via AWS Console')
            ]
        )
        return auto_scaling_group

    def _build_dcv_connection_gateway_instance_infrastructure(self):
        self.dcv_connection_gateway_security_group = VirtualDesktopPublicLoadBalancerAccessSecurityGroup(
            context=self.context,
            name=f'{self.module_id}-{self.COMPONENT_DCV_CONNECTION_GATEWAY}-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc,
            bastion_host_security_group=self.cluster.get_security_group('bastion-host'),
            public_loadbalancer_security_group=self.cluster.get_security_group('external-load-balancer'),
            description='Security Group for Virtual Desktop DCV Connection Gateway',
            directory_service_access=False,
            component_name='DCV Connection Gateway'
        )

        dcv_connection_gateway_bootstrap_package_uri = self.stack.node.try_get_context('dcv_connection_gateway_package_uri')
        if Utils.is_empty(dcv_connection_gateway_bootstrap_package_uri):
            dcv_connection_gateway_bootstrap_package_uri = 'not-provided'

        https_proxy = self.context.config().get_string('cluster.network.https_proxy', required=False, default='')
        no_proxy = self.context.config().get_string('cluster.network.no_proxy', required=False, default='')
        proxy_config = {}
        if Utils.is_not_empty(https_proxy):
            proxy_config = {
                'http_proxy': https_proxy,
                'https_proxy': https_proxy,
                'no_proxy': no_proxy
            }

        connection_gateway_userdata = BootstrapUserDataBuilder(
            aws_region=self.aws_region,
            bootstrap_package_uri=dcv_connection_gateway_bootstrap_package_uri,
            install_commands=[
                '/bin/bash dcv-connection-gateway/setup.sh'
            ],
            infra_config={
                'CERTIFICATE_SECRET_ARN': '${__CERTIFICATE_SECRET_ARN__}',
                'PRIVATE_KEY_SECRET_ARN': '${__PRIVATE_KEY_SECRET_ARN__}',
            },
            proxy_config=proxy_config,
            bootstrap_source_dir_path=ideaadministrator.props.bootstrap_source_dir,
            base_os=self.context.config().get_string('virtual-desktop-controller.dcv_connection_gateway.autoscaling.base_os', required=True)
        ).build()

        external_certificate_provided = self.context.config().get_bool('virtual-desktop-controller.dcv_connection_gateway.certificate.provided', required=True)
        if not external_certificate_provided:
            substituted_userdata = cdk.Fn.sub(connection_gateway_userdata, {
                '__CERTIFICATE_SECRET_ARN__': self.dcv_connection_gateway_self_signed_cert.get_att_string('certificate_secret_arn'),
                '__PRIVATE_KEY_SECRET_ARN__': self.dcv_connection_gateway_self_signed_cert.get_att_string('private_key_secret_arn')
            })
        else:
            substituted_userdata = cdk.Fn.sub(connection_gateway_userdata, {
                '__CERTIFICATE_SECRET_ARN__': self.context.config().get_string('virtual-desktop-controller.dcv_connection_gateway.certificate.certificate_secret_arn', required=True),
                '__PRIVATE_KEY_SECRET_ARN__': self.context.config().get_string('virtual-desktop-controller.dcv_connection_gateway.certificate.private_key_secret_arn', required=True)
            })

        self.dcv_connection_gateway_autoscaling_group = self._build_auto_scaling_group(
            component_name=self.COMPONENT_DCV_CONNECTION_GATEWAY,
            security_group=self.dcv_connection_gateway_security_group,
            iam_role=self._build_iam_role(
                role_description=f'IAM role assigned to virtual-desktop-{self.COMPONENT_DCV_CONNECTION_GATEWAY}',
                component_name=self.COMPONENT_DCV_CONNECTION_GATEWAY,
                component_jinja='virtual-desktop-dcv-connection-gateway.yml'
            ),
            substituted_userdata=substituted_userdata,
            node_type=constants.NODE_TYPE_INFRA
        )

    def _build_dcv_connection_gateway_network_infrastructure(self):

        is_public = self.context.config().get_bool('cluster.load_balancers.external_alb.public', default=True)
        external_nlb_subnets = self.cluster.existing_vpc.get_public_subnets(SubnetFilterKeys.LOAD_BALANCER_SUBNETS) if is_public is True else self.cluster.existing_vpc.get_private_subnets(SubnetFilterKeys.LOAD_BALANCER_SUBNETS)
        self.external_nlb = elbv2.NetworkLoadBalancer(
            self.stack,
            f'{self.cluster_name}-{self.module_id}-external-nlb',
            load_balancer_name=f'{self.cluster_name}-{self.module_id}-external-nlb',
            vpc=self.cluster.vpc,
            internet_facing=is_public,
            vpc_subnets=ec2.SubnetSelection(subnets=external_nlb_subnets)
        )

        # enable access logs
        external_alb_enable_access_log = self.context.config().get_bool('virtual-desktop-controller.external_nlb.access_logs', default=False)
        if external_alb_enable_access_log:
            access_log_destination = s3.Bucket.from_bucket_name(scope=self.stack, id='cluster-s3-bucket', bucket_name=self.context.config().get_string('cluster.cluster_s3_bucket', required=True))
            self.external_nlb.log_access_logs(access_log_destination, f'logs/{self.module_id}/external-nlb-access-logs')

        quic_supported = self.context.config().get_bool('virtual-desktop-controller.dcv_session.quic_support', required=True)
        protocol = elbv2.Protocol.TCP
        tg_suffix = 'TN'  # TCP Network
        if quic_supported:
            protocol = elbv2.Protocol.TCP_UDP
            tg_suffix = 'TUN'  # TCP - UDP Network

        dcv_connection_gateway_target_group = elbv2.NetworkTargetGroup(
            self.stack,
            'dcv-connection-gateway-target-group-nlb',
            port=8443,
            protocol=protocol,
            target_type=elbv2.TargetType.INSTANCE,
            vpc=self.cluster.vpc,
            targets=[self.dcv_connection_gateway_autoscaling_group],
            target_group_name=self.get_target_group_name(f'{self.COMPONENT_DCV_CONNECTION_GATEWAY}-{tg_suffix}'),
            health_check=elbv2.HealthCheck(
                port='8989',
                protocol=elbv2.Protocol.TCP
            ),
            connection_termination=True
        )
        # Can not provide stickiness attributes directly in CDK Construct. Refer - https://github.com/aws/aws-cdk/issues/17491
        # Documentation on attributes. Refer - https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-elasticloadbalancingv2-targetgroup-targetgroupattribute.html
        dcv_connection_gateway_target_group.set_attribute('stickiness.enabled', 'true')
        dcv_connection_gateway_target_group.set_attribute('stickiness.type', 'source_ip')

        elbv2.NetworkListener(
            self.external_nlb,
            'dcv-connection-gateway-nlb-listener',
            load_balancer=self.external_nlb,
            protocol=protocol,
            port=443,
            default_action=elbv2.NetworkListenerAction.forward(
                target_groups=[
                    dcv_connection_gateway_target_group
                ]
            )
        )

        self.dcv_connection_gateway_security_group.add_ingress_rule(
            ec2.Peer.ipv4(self.cluster.vpc.vpc_cidr_block),
            ec2.Port.tcp(8989),
            description='Allow TCP traffic access for HealthCheck to DCV Connection Gateway'
        )

        cluster_prefix_list_id = self.context.config().get_string('cluster.network.cluster_prefix_list_id', required=True)
        self.dcv_connection_gateway_security_group.add_ingress_rule(
            ec2.Peer.prefix_list(cluster_prefix_list_id),
            ec2.Port.all_traffic(),
            description='Allow all Traffic access from Cluster Prefix List to DCV Connection Gateway'
        )

        prefix_list_ids = [i for i in self.context.config().get_list('cluster.network.prefix_list_ids', default=[]) if i is not None]
        for prefix_list_id in prefix_list_ids:
            self.dcv_connection_gateway_security_group.add_ingress_rule(
                ec2.Peer.prefix_list(prefix_list_id),
                ec2.Port.all_traffic(),
                description='Allow all traffic access from Prefix List to DCV Connection Gateway'
            )

    def _build_self_signed_cert_for_dcv_connection_gateway(self):
        self_signed_certificate_lambda_arn = self.context.config().get_string('cluster.self_signed_certificate_lambda_arn', required=True)
        self.dcv_connection_gateway_self_signed_cert = cdk.CustomResource(
            self.stack,
            f'{self.cluster_name}-{self.module_id}-external-cert-{self.COMPONENT_DCV_CONNECTION_GATEWAY}',
            service_token=self_signed_certificate_lambda_arn,
            properties={
                'domain_name': f'{self.module_id}.{self.cluster_name}.idea.default',
                'certificate_name': f'{self.cluster_name}-{self.module_id}-{self.COMPONENT_DCV_CONNECTION_GATEWAY}-certificate',
                'create_acm_certificate': False,
                'kms_key_id': self.context.config().get_string('cluster.secretsmanager.kms_key_id'),
                'tags': {
                    'Name': f'{self.cluster_name}-{self.module_id}-{self.COMPONENT_DCV_CONNECTION_GATEWAY} Self Signed Certificate',
                    'res:EnvironmentName': self.cluster_name,
                    'res:ModuleName': 'virtual-desktop-controller'
                }
            },
            resource_type='Custom::SelfSignedCertificateConnectionGateway'
        )

    def build_dcv_connection_gateway(self):
        external_certificate_provided = self.context.config().get_bool('virtual-desktop-controller.dcv_connection_gateway.certificate.provided', required=True)
        if not external_certificate_provided:
            self._build_self_signed_cert_for_dcv_connection_gateway()

        self._build_dcv_connection_gateway_instance_infrastructure()
        self._build_dcv_connection_gateway_network_infrastructure()

    def build_backups(self):
        cluster_backups_enabled = self.context.config().get_string('cluster.backups.enabled', default=False)
        if not cluster_backups_enabled:
            return

        vdi_host_backup_enabled = self.context.config().get_bool('virtual-desktop-controller.vdi_host_backup.enabled', default=False)
        if not vdi_host_backup_enabled:
            return

        backup_vault_arn = self.context.config().get_string('cluster.backups.backup_vault.arn', required=True)
        backup_role_arn = self.context.config().get_string('cluster.backups.role_arn', required=True)

        backup_role = iam.Role.from_role_arn(self.stack, 'backup-role', backup_role_arn)
        backup_vault = backup.BackupVault.from_backup_vault_arn(self.stack, 'cluster-backup-vault', backup_vault_arn)

        backup_plan_config = self.context.config().get_config('virtual-desktop-controller.vdi_host_backup.backup_plan')

        self.backup_plan = BackupPlan(
            self.context, 'vdi-host-backup-plan', self.stack,
            backup_plan_name=f'{self.cluster_name}-{self.module_id}',
            backup_plan_config=backup_plan_config,
            backup_vault=backup_vault,
            backup_role=backup_role
        )

    def build_cluster_settings(self):
        cluster_settings = {
            'deployment_id': self.deployment_id,
            'client_id': self.oauth2_client_secret.client_id.ref,
            'client_secret': self.oauth2_client_secret.client_secret.ref,
            'dcv_host_security_group_id': self.dcv_host_security_group.security_group_id,
            'dcv_host_role_arn': self.dcv_host_role.role_arn,
            'dcv_host_role_name': self.dcv_host_role.role_name,
            'dcv_host_role_id': self.dcv_host_role.role_id,
            'dcv_broker_role_arn': self.dcv_broker_role.role_arn,
            'dcv_broker_role_name': self.dcv_broker_role.role_name,
            'dcv_broker_role_id': self.dcv_broker_role.role_id,
            'scheduled_event_transformer_lambda_role_arn': self.scheduled_event_transformer_lambda_role.role_arn,
            'scheduled_event_transformer_lambda_role_name': self.scheduled_event_transformer_lambda_role.role_name,
            'scheduled_event_transformer_lambda_role_id': self.scheduled_event_transformer_lambda_role.role_id,
            'custom_credential_broker_lambda_function_arn': self.custom_credential_broker_lambda_function.function_arn,
            'custom_credential_broker_api_gateway_url': self.custom_credential_broker_api_gateway_rest_api.url + self.object_storage_temp_credentials_path_part,
            'custom_credential_broker_api_gateway_id': self.custom_credential_broker_api_gateway_rest_api.rest_api_id,
            'custom_credential_broker_lambda_role_arn': self.custom_credential_broker_lambda_role.role_arn,
            's3_mount_base_bucket_read_only_role_arn': self.s3_mount_base_bucket_read_only_role.role_arn,
            's3_mount_base_bucket_read_write_role_arn': self.s3_mount_base_bucket_read_write_role.role_arn,
            'dcv_host_instance_profile_name': self.dcv_host_instance_profile.ref,
            'dcv_host_instance_profile_arn': self.build_instance_profile_arn(self.dcv_host_instance_profile.ref),
            'ssm_commands_sns_topic_arn': self.ssm_commands_sns_topic.topic_arn,
            'ssm_commands_sns_topic_name': self.ssm_commands_sns_topic.topic_name,
            'ssm_commands_pass_role_arn': self.ssm_command_pass_role.role_arn,
            'ssm_commands_pass_role_id': self.ssm_command_pass_role.role_id,
            'ssm_commands_pass_role_name': self.ssm_command_pass_role.role_name,
            'controller_iam_role_arn': self.controller_role.role_arn,
            'controller_iam_role_name': self.controller_role.role_name,
            'controller_iam_role_id': self.controller_role.role_id,
            'events_sqs_queue_url': self.event_sqs_queue.queue_url,
            'events_sqs_queue_arn': self.event_sqs_queue.queue_arn,
            'controller_sqs_queue_url': self.controller_sqs_queue.queue_url,
            'controller_sqs_queue_arn': self.controller_sqs_queue.queue_arn,
            'external_nlb.load_balancer_dns_name': self.external_nlb.load_balancer_dns_name,
            'external_nlb_arn': self.external_nlb.load_balancer_arn,
            'controller.asg_name': self.controller_auto_scaling_group.auto_scaling_group_name,
            'controller.asg_arn': self.controller_auto_scaling_group.auto_scaling_group_arn,
            'dcv_broker.asg_name': self.dcv_broker_autoscaling_group.auto_scaling_group_name,
            'dcv_broker.asg_arn': self.dcv_broker_autoscaling_group.auto_scaling_group_arn,
            'dcv_connection_gateway.asg_name': self.dcv_connection_gateway_autoscaling_group.auto_scaling_group_name,
            'dcv_connection_gateway.asg_arn': self.dcv_connection_gateway_autoscaling_group.auto_scaling_group_arn,
            'gateway_security_group_id': self.dcv_connection_gateway_security_group.security_group_id
        }

        if not self.context.config().get_bool('virtual-desktop-controller.dcv_connection_gateway.certificate.provided', default=False):
            cluster_settings['dcv_connection_gateway.certificate.certificate_secret_arn'] = self.dcv_connection_gateway_self_signed_cert.get_att_string('certificate_secret_arn')
            cluster_settings['dcv_connection_gateway.certificate.private_key_secret_arn'] = self.dcv_connection_gateway_self_signed_cert.get_att_string('private_key_secret_arn')
        else:
            cluster_settings['dcv_connection_gateway.certificate.provided'] = self.context.config().get_string('virtual-desktop-controller.dcv_connection_gateway.certificate.provided', required=True)
            cluster_settings['dcv_connection_gateway.certificate.certificate_secret_arn'] = self.context.config().get_string('virtual-desktop-controller.dcv_connection_gateway.certificate.certificate_secret_arn', required=True)
            cluster_settings['dcv_connection_gateway.certificate.private_key_secret_arn'] = self.context.config().get_string('virtual-desktop-controller.dcv_connection_gateway.certificate.private_key_secret_arn', required=True)
            cluster_settings['dcv_connection_gateway.certificate.custom_dns_name'] = self.context.config().get_string('virtual-desktop-controller.dcv_connection_gateway.certificate.custom_dns_name', required=True)

        if self.backup_plan is not None:
            cluster_settings['vdi_host_backup.backup_plan.arn'] = self.backup_plan.get_backup_plan_arn()

        self.update_cluster_settings(cluster_settings)
