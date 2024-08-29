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
    'LambdaFunction',
    'Policy',
    'ManagedPolicy',
    'Role',
    'InstanceProfile',
    'CustomResource',
    'CreateTagsCustomResource',
    'SQSQueue',
    'SNSTopic',
    'SNSSubscription',
    'CloudWatchAlarm',
    'Output',
    'DynamoDBTable',
    'APIGatewayRestApi'
)

import re

from aws_cdk.aws_ec2 import IVpc, SubnetSelection, ISecurityGroup

from ideaadministrator.app.cdk.idea_code_asset import IdeaCodeAsset, SupportedLambdaPlatforms
from ideaadministrator.app_context import AdministratorContext
from ideaadministrator.app.cdk.constructs import SocaBaseConstruct, IdeaNagSuppression
from ideaadministrator.app_utils import AdministratorUtils
from ideasdk.utils import Utils
from ideadatamodel import SocaAnyPayload, exceptions, constants

from typing import List, Dict, Optional, Any, Union

import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    aws_kinesis as kinesis,
    aws_kms as kms,
    aws_apigateway as apigateway
)


class LambdaFunction(SocaBaseConstruct, lambda_.Function):
    MAX_NAME_LENGTH = 64

    def __init__(self, context: AdministratorContext,
                 name: str,
                 scope: constructs.IConstruct,
                 idea_code_asset: IdeaCodeAsset = None,
                 code: lambda_.AssetCode = None,
                 handler: str = None,
                 description: str = None,
                 memory_size: int = 128,
                 runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9,
                 timeout_seconds: int = 60,
                 vpc: Optional[IVpc] = None,
                 security_groups: Optional[List[ISecurityGroup]] = None,
                 vpc_subnets: Optional[SubnetSelection] = None,
                 log_retention: logs.RetentionDays = None,
                 log_retention_role: Optional[iam.IRole] = None,
                 environment: dict = None,
                 role: iam.IRole = None):
        self.context = context

        if Utils.is_empty(idea_code_asset):
            if Utils.are_empty(code, handler):
                raise exceptions.invalid_params('Provide either idea_code_asset or (code and handler)')
        else:
            lambda_build_dir = idea_code_asset.build_lambda()
            code = lambda_.Code.from_asset(
                path=lambda_build_dir,
                asset_hash_type=cdk.AssetHashType.CUSTOM,
                asset_hash=idea_code_asset.asset_hash
            )
            handler = idea_code_asset.lambda_handler

        timeout = cdk.Duration.seconds(timeout_seconds)
        function_name = self.build_resource_name(name),
        if isinstance(function_name, tuple):
            function_name = ' '.join(function_name)

        if len(function_name) > self.MAX_NAME_LENGTH:
            function_name = self.build_trimmed_resource_name(name, trim_length=self.MAX_NAME_LENGTH)

        super().__init__(
            context, name, scope,
            function_name=function_name,
            description=description,
            memory_size=memory_size,
            runtime=runtime,
            timeout=timeout,
            log_retention=log_retention,
            handler=handler,
            environment=environment,
            code=code,
            role=role,
            vpc=vpc,
            security_groups=security_groups,
            vpc_subnets=vpc_subnets,
            log_retention_role=log_retention_role)

        self.add_nag_suppression(suppressions=[
            IdeaNagSuppression(rule_id='AwsSolutions-L1', reason='Lambda runtime uses Python 3.9 by default.')
        ])


class APIGatewayRestApi(SocaBaseConstruct, apigateway.RestApi):

    def __init__(self, context: AdministratorContext,
                 name: str,
                 rest_api_name: str,
                 scope: constructs.Construct,
                 description: str = None,
                 policy: iam.PolicyDocument = None,
                 deploy: bool = True,
                 deploy_options: apigateway.StageOptions = None,
                 default_method_options: apigateway.MethodOptions = None,
                 endpoint_types: List[apigateway.EndpointType] = None,
                 endpoint_configuration: apigateway.EndpointConfiguration = None
                 ) -> None:
        super().__init__(context, name, scope,
                         description=description,
                         policy=policy,
                         deploy=deploy,
                         endpoint_types=endpoint_types,
                         endpoint_configuration=endpoint_configuration,
                         rest_api_name=rest_api_name,
                         deploy_options=deploy_options,
                         default_method_options=default_method_options
                         )


class Policy(SocaBaseConstruct, iam.Policy):

    def __init__(self, context: AdministratorContext,
                 name: str,
                 scope: constructs.Construct,
                 policy_template_name: str,
                 vars: SocaAnyPayload = None,  # noqa
                 module_id: str = None):
        self.context = context
        self.policy_template_name = policy_template_name
        self.vars = vars
        self.module_id = module_id
        super().__init__(context, name, scope, document=self.build_policy_json())

        self.add_nag_suppression(suppressions=[
            IdeaNagSuppression(rule_id='AwsSolutions-IAM5', reason='Wild-card policies are scoped with conditions and/or applicable prefixes.')
        ])

    def build_policy_json(self) -> iam.PolicyDocument:
        policy = AdministratorUtils.render_policy(
            policy_template_name=self.policy_template_name,
            cluster_name=self.context.cluster_name(),
            module_id=self.module_id,
            config=self.context.config(),
            vars=self.vars
        )
        return iam.PolicyDocument.from_json(policy)


class ManagedPolicy(SocaBaseConstruct, iam.ManagedPolicy):

    def __init__(self, context: AdministratorContext,
                 name: str,
                 scope: constructs.Construct,
                 description: str,
                 policy_template_name: str,
                 managed_policy_name: str,
                 vars: SocaAnyPayload = None,  # noqa
                 module_id: str = None):
        self.context = context
        self.policy_template_name = policy_template_name
        self.vars = vars
        self.module_id = module_id
        super().__init__(context, name, scope, managed_policy_name=managed_policy_name, description=description, document=self.build_policy_json())

        self.add_nag_suppression(suppressions=[
            IdeaNagSuppression(rule_id='AwsSolutions-IAM5', reason='AWS Managed Policies are expected to be customized and scoped down.'
                                                                   'AWS Managed policies are copied over to enable these customizations.')
        ])

    def build_policy_json(self) -> iam.PolicyDocument:
        policy = AdministratorUtils.render_policy(
            policy_template_name=self.policy_template_name,
            cluster_name=self.context.cluster_name(),
            module_id=self.module_id,
            config=self.context.config(),
            vars=self.vars
        )
        return iam.PolicyDocument.from_json(policy)


class Role(SocaBaseConstruct, iam.Role):
    MAX_NAME_LENGTH = 64

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 description: str,
                 assumed_by: List[str],
                 inline_policies: List[iam.Policy] = None,
                 managed_policies: List[str] = None):

        self.context = context
        role_name = self.build_resource_name(name, region_suffix=True)
        if isinstance(role_name, tuple):
            role_name = ' '.join(role_name)

        if len(role_name) > self.MAX_NAME_LENGTH:
            role_name = self.build_trimmed_resource_name(name, region_suffix=True, trim_length=self.MAX_NAME_LENGTH)

        super().__init__(context, name, scope,
                         role_name=role_name,
                         description=description,
                         assumed_by=self.build_assumed_by(assumed_by))
        if inline_policies is not None:
            for policy in inline_policies:
                self.attach_inline_policy(policy)
        if managed_policies is not None:
            for policy in managed_policies:
                if policy.startswith('arn:'):
                    name = policy.split('/')[1]
                    self.add_managed_policy(iam.ManagedPolicy.from_managed_policy_arn(self, name, policy))
                else:
                    self.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name(policy))

    def build_assumed_by(self, assumed_by: List[str]) -> iam.IPrincipal:
        principals = []
        for service in assumed_by:
            principals.append(self.build_service_principal(service))
        return iam.CompositePrincipal(*principals)


class InstanceProfile(SocaBaseConstruct, iam.CfnInstanceProfile):
    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 roles: List[iam.Role]):
        self.context = context
        role_names = []
        for role in roles:
            role_names.append(role.role_name)
        super().__init__(context, name, scope, instance_profile_name=self.build_resource_name(name, region_suffix=True), roles=role_names)


class CustomResource(SocaBaseConstruct):
    def __init__(self, context: AdministratorContext,
                 name: str,
                 scope: constructs.Construct,
                 idea_code_asset: IdeaCodeAsset,
                 policy_statements: Optional[List[iam.PolicyStatement]] = None,
                 policy_template_name: Optional[str] = None,
                 removal_policy: Optional[cdk.RemovalPolicy] = None,
                 resource_type: Optional[str] = None,
                 runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_9,
                 lambda_timeout_seconds: int = 60,
                 lambda_log_retention_role: Optional[iam.IRole] = None):

        super().__init__(context, name)
        self.scope = scope
        self.idea_code_asset = idea_code_asset
        self.policy_template_name = policy_template_name
        self.policy_statements = policy_statements
        self.removal_policy = removal_policy
        self.lambda_timeout_seconds = lambda_timeout_seconds
        self.lambda_log_retention_role = lambda_log_retention_role
        self.runtime = runtime

        prefix = 'Custom::'
        if Utils.is_empty(resource_type):
            self.resource_type = f'{prefix}{self.name_title_case()}'
        else:
            if resource_type.startswith(prefix):
                self.resource_type = resource_type
            else:
                self.resource_type = f'{prefix}{resource_type}'

        self.lambda_role: Optional[Role] = None
        self.lambda_policy: Optional[Policy] = None
        self.lambda_function: Optional[LambdaFunction] = None

        self.build_lambda_function()

    def build_lambda_function(self):

        if Utils.is_not_empty(self.policy_template_name):
            self.lambda_policy = Policy(
                context=self.context,
                name=f'{self.name}-lambda-policy',
                scope=self.scope,
                policy_template_name=self.policy_template_name
            )

        self.lambda_role = Role(
            self.context,
            f'{self.name}-role',
            self.scope,
            f'Role for {self.resource_type} for Cluster: {self.cluster_name}',
            assumed_by=['lambda']
        )
        if self.lambda_policy is not None:
            self.lambda_role.attach_inline_policy(self.lambda_policy)

        self.lambda_function = LambdaFunction(
            self.context,
            f'{self.name}-lambda',
            self.scope,
            idea_code_asset=self.idea_code_asset,
            description=f'{self.resource_type} Lambda Function for Cluster: {self.cluster_name}',
            timeout_seconds=self.lambda_timeout_seconds,
            role=self.lambda_role,
            log_retention_role=self.lambda_log_retention_role,
            runtime=self.runtime
        )

        if self.policy_statements is not None:
            for statement in self.policy_statements:
                self.lambda_function.add_to_role_policy(statement=statement)

        if self.lambda_role is not None:
            self.lambda_function.node.add_dependency(self.lambda_role)
        if self.lambda_policy is not None:
            self.lambda_function.node.add_dependency(self.lambda_policy)

    def invoke(self, name: str, properties: Dict[str, Any]) -> cdk.CustomResource:
        custom_resource = cdk.CustomResource(
            self.scope,
            name,
            service_token=self.lambda_function.function_arn,
            properties=properties,
            removal_policy=self.removal_policy,
            resource_type=self.resource_type
        )
        custom_resource.node.add_dependency(self.lambda_function)
        return custom_resource


class CreateTagsCustomResource(CustomResource):
    def __init__(self, context: AdministratorContext,
                 scope: constructs.Construct,
                 lambda_log_retention_role: Optional[iam.IRole] = None):
        super().__init__(
            context, 'ec2-create-tags', scope,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_custom_resource_create_tags',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            policy_template_name='custom-resource-ec2-create-tags.yml',
            resource_type='EC2CreateTags',
            lambda_log_retention_role=lambda_log_retention_role)

    def apply(self, name: str, resource_id: str, tags: Dict[str, Any]) -> cdk.CustomResource:
        aws_tags = []
        for key, value in tags.items():
            aws_tags.append({
                'Key': key,
                'Value': str(value)
            })
        return super().invoke(name, properties={
            'ResourceId': resource_id,
            'Tags': aws_tags
        })


class SQSQueue(SocaBaseConstruct, sqs.Queue):

    def __init__(self, context: AdministratorContext, id_: str, scope: constructs.Construct, *,
                 content_based_deduplication: Optional[bool] = None,
                 data_key_reuse: Optional[cdk.Duration] = None,
                 dead_letter_queue: Optional[Union[sqs.DeadLetterQueue, Dict[str, Any]]] = None,
                 deduplication_scope: Optional[sqs.DeduplicationScope] = None,
                 delivery_delay: Optional[cdk.Duration] = None,
                 encrypt_at_rest: Optional[bool] = True,
                 encryption: Optional[sqs.QueueEncryption] = None,
                 encryption_master_key: Optional[str] = None,
                 fifo: Optional[bool] = None,
                 fifo_throughput_limit: Optional[sqs.FifoThroughputLimit] = None,
                 max_message_size_bytes: Optional[int] = None,
                 queue_name: Optional[str] = None,
                 receive_message_wait_time: Optional[cdk.Duration] = None,
                 removal_policy: Optional[cdk.RemovalPolicy] = None,
                 retention_period: Optional[cdk.Duration] = None,
                 visibility_timeout: Optional[cdk.Duration] = None,
                 is_dead_letter_queue: bool = False):
        self.context = context

        if encrypt_at_rest:
            if encryption is None:
                encryption = sqs.QueueEncryption.KMS_MANAGED

            encryption_master_key_ = None
            if Utils.is_not_empty(encryption_master_key):
                key_arn = self.get_kms_key_arn(encryption_master_key)
                encryption_master_key_ = kms.Key.from_key_arn(scope=scope, id=f'{id_}-kms-key', key_arn=key_arn)
                encryption = sqs.QueueEncryption.KMS
        else:
            encryption = sqs.QueueEncryption.UNENCRYPTED
            encryption_master_key_ = None

        super().__init__(
            context=context,
            name=id_,
            scope=scope,
            content_based_deduplication=content_based_deduplication,
            data_key_reuse=data_key_reuse,
            dead_letter_queue=dead_letter_queue,
            deduplication_scope=deduplication_scope,
            delivery_delay=delivery_delay,
            encryption=encryption,
            encryption_master_key=encryption_master_key_,
            fifo=fifo,
            fifo_throughput_limit=fifo_throughput_limit,
            max_message_size_bytes=max_message_size_bytes,
            queue_name=queue_name,
            receive_message_wait_time=receive_message_wait_time,
            removal_policy=removal_policy,
            retention_period=retention_period,
            visibility_timeout=visibility_timeout
        )

        if encrypt_at_rest:
            self.add_to_resource_policy(iam.PolicyStatement(
                sid='AlwaysEncrypted',
                effect=iam.Effect.DENY,
                actions=['sqs:*'],
                conditions={
                    'Bool': {
                        'aws:SecureTransport': 'false'
                    }
                },
                resources=[self.queue_arn],
                principals=[iam.AnyPrincipal()]
            ))
        else:
            self.add_nag_suppression(suppressions=[
                IdeaNagSuppression(rule_id='AwsSolutions-SQS2', reason='SQS encryption key is configurable, but is not provided in cluster config.')
            ])
            self.add_nag_suppression(suppressions=[
                IdeaNagSuppression(rule_id='AwsSolutions-SQS4', reason='SQS encryption key is configurable, but is not provided in cluster config.')
            ])

        if is_dead_letter_queue:
            self.add_nag_suppression(suppressions=[
                IdeaNagSuppression(rule_id='AwsSolutions-SQS3', reason='Dead letter queue')
            ])


class SNSTopic(SocaBaseConstruct, sns.Topic):

    def __init__(self, context: AdministratorContext, id_: str, scope: constructs.Construct, *,
                 fifo: bool = None,
                 master_key: str = None,
                 display_name: str = None,
                 topic_name: str = None,
                 policy_statements: List[iam.PolicyStatement] = None):

        self.context = context

        if Utils.is_empty(topic_name):
            topic_name = self.build_resource_name(id_)

        if Utils.is_empty(display_name):
            display_name = topic_name

        if Utils.is_not_empty(master_key):
            kms_key_arn = self.get_kms_key_arn(master_key)
            master_key_ = kms.Key.from_key_arn(scope=scope, id=f'{id_}-kms-key', key_arn=kms_key_arn)
        else:
            master_key_ = kms.Alias.from_alias_name(scope=scope, id=f'{id_}-kms-key-default', alias_name='alias/aws/sns')

        super().__init__(
            context, id_, scope,
            display_name=display_name,
            fifo=fifo,
            topic_name=topic_name,
            master_key=master_key_)

        if policy_statements is not None:
            for statement in policy_statements:
                self.add_to_resource_policy(statement)

        self.add_to_resource_policy(iam.PolicyStatement(
            sid='AlwaysEncrypted',
            effect=iam.Effect.DENY,
            actions=['SNS:Publish'],
            conditions={
                'Bool': {
                    'aws:SecureTransport': 'false'
                }
            },
            resources=[self.topic_arn],
            principals=[iam.AnyPrincipal()]
        ))


class SNSSubscription(SocaBaseConstruct, sns.Subscription):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 protocol: sns.SubscriptionProtocol,
                 endpoint: str,
                 topic: sns.ITopic):
        super().__init__(context, name, scope,
                         protocol=protocol,
                         endpoint=endpoint,
                         topic=topic)


class CloudWatchAlarm(SocaBaseConstruct, cloudwatch.Alarm):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 metric_name: str,
                 metric_namespace: str,
                 threshold: Union[int, float],
                 metric_dimensions: Dict = None,
                 period: cdk.Duration = None,
                 period_seconds=60,
                 statistic: str = 'Average',
                 actions_enabled: bool = None,
                 alarm_description: str = None,
                 comparison_operator: cloudwatch.ComparisonOperator = None,
                 evaluation_periods=10,
                 datapoints_to_alarm: Union[int, float, None] = None,
                 evaluate_low_sample_count_percentile: str = None,
                 treat_missing_data: cloudwatch.TreatMissingData = None,
                 actions: List[cloudwatch.IAlarmAction] = None):

        self.context = context

        if period is None:
            period = cdk.Duration.seconds(period_seconds)

        if alarm_description is None:
            alarm_description = f'{metric_name} Alarm'

        super().__init__(context, name, scope,
                         metric=cloudwatch.Metric(
                             metric_name=metric_name,
                             namespace=metric_namespace,
                             dimensions_map=metric_dimensions,
                             period=period,
                             statistic=statistic
                         ),
                         threshold=threshold,
                         evaluation_periods=evaluation_periods,
                         actions_enabled=actions_enabled,
                         alarm_description=alarm_description,
                         alarm_name=self.build_resource_name(name),
                         comparison_operator=comparison_operator,
                         datapoints_to_alarm=datapoints_to_alarm,
                         evaluate_low_sample_count_percentile=evaluate_low_sample_count_percentile,
                         treat_missing_data=treat_missing_data)

        if actions is not None:
            for action in actions:
                self.add_alarm_action(action)


class Output(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 value_ref: Any, description: str = None, export_name=None):
        super().__init__(context, name)
        self.output = cdk.CfnOutput(
            scope,
            name,
            value=value_ref,
            description=description,
            export_name=export_name
        )

    @property
    def description(self) -> str:
        return self.output.description

    @property
    def value(self) -> Any:
        return self.output.value

    @property
    def string_value(self) -> str:
        return str(self.output.value)


class DynamoDBTable(SocaBaseConstruct, dynamodb.Table):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 table_name: str,
                 partition_key: dynamodb.Attribute,
                 billing_mode: Optional[dynamodb.BillingMode] = None,
                 read_capacity: Optional[int] = None,
                 write_capacity: Optional[int] = None,
                 sort_key: Optional[dynamodb.Attribute] = None,
                 removal_policy: Optional[cdk.RemovalPolicy] = None,
                 replication_regions: Optional[List[str]] = None,
                 replication_timeout: Optional[cdk.Duration] = None,
                 stream: Optional[dynamodb.StreamViewType] = None,
                 time_to_live_attribute: Optional[str] = None,
                 wait_for_replication_to_finish: Optional[bool] = None):
        self.context = context

        super().__init__(context, name, scope,
                         table_name=table_name,
                         billing_mode=billing_mode,
                         contributor_insights_enabled=False,
                         encryption=None,
                         encryption_key=None,
                         point_in_time_recovery=None,
                         read_capacity=read_capacity,
                         removal_policy=removal_policy,
                         replication_regions=replication_regions,
                         replication_timeout=replication_timeout,
                         stream=stream,
                         time_to_live_attribute=time_to_live_attribute,
                         wait_for_replication_to_finish=wait_for_replication_to_finish,
                         write_capacity=write_capacity,
                         partition_key=partition_key,
                         sort_key=sort_key)
