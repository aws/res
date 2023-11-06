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
    'AmazonEFS',
    'FSxForLustre'
)

from ideaadministrator.app.cdk.idea_code_asset import IdeaCodeAsset, SupportedLambdaPlatforms
from ideasdk.utils import Utils

from ideaadministrator.app.cdk.constructs import SocaBaseConstruct
from ideaadministrator.app.cdk.constructs.common import (
    SNSTopic,
    SNSSubscription,
    CloudWatchAlarm,
    Role,
    Policy,
    LambdaFunction
)
from ideaadministrator.app_context import AdministratorContext

from typing import List, Optional, Tuple, Dict

import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_efs as efs,
    aws_fsx as fsx,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns
)


class AmazonEFS(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc,
                 security_group: ec2.SecurityGroup,
                 efs_config: Dict,
                 subnets: List[ec2.ISubnet] = None,
                 log_retention_role: Optional[iam.IRole] = None,
                 ):
        super().__init__(context, name)

        self.scope = scope
        self.vpc = vpc
        self.security_group = security_group
        self.kms_key_id = Utils.get_value_as_string('kms_key_id', efs_config)
        self.subnets = subnets
        self.log_retention_role = log_retention_role
        self.cloud_watch_monitoring = Utils.get_value_as_bool('cloudwatch_monitoring', efs_config, False)
        removal_policy = Utils.get_value_as_string('removal_policy', efs_config)
        if removal_policy == 'DESTROY':
            removal_policy = 'DELETE'
        self.deletion_policy = cdk.CfnDeletionPolicy(removal_policy)
        self.transition_to_ia = Utils.get_value_as_string('transition_to_ia', efs_config)
        self.encrypted = Utils.get_value_as_bool('encrypted', efs_config, True)
        self.throughput_mode = Utils.get_value_as_string('throughput_mode', efs_config, 'bursting')
        self.performance_mode = Utils.get_value_as_string('performance_mode', efs_config, 'generalPurpose')

        file_system, mount_targets = self.build_file_system()
        self.file_system = file_system
        self.mount_targets = mount_targets

        self.cloud_watch_monitoring: Optional[Tuple[sns.Topic,
                                                    cloudwatch.Alarm,
                                                    cloudwatch.Alarm,
                                                    lambda_.Function,
                                                    sns.Subscription]] = None

        if self.cloud_watch_monitoring:
            self.cloud_watch_monitoring = self.build_cloudwatch_monitoring()

    def get_subnets(self) -> List[ec2.ISubnet]:
        if self.subnets is not None:
            return self.subnets
        else:
            return self.vpc.private_subnets

    def build_file_system(self) -> Tuple[efs.CfnFileSystem, List[efs.CfnMountTarget]]:

        lifecycle_policies = None
        if Utils.is_not_empty(self.transition_to_ia):
            lifecycle_policies = [efs.CfnFileSystem.LifecyclePolicyProperty(transition_to_ia=self.transition_to_ia)]

        file_system = efs.CfnFileSystem(
            scope=self.scope,
            id=self.name,
            encrypted=self.encrypted,
            file_system_tags=[
                efs.CfnFileSystem.ElasticFileSystemTagProperty(
                    key='Name',
                    value=self.build_resource_name(self.name)
                )
            ],
            kms_key_id=self.kms_key_id,
            throughput_mode=self.throughput_mode,
            performance_mode=self.performance_mode,
            lifecycle_policies=lifecycle_policies,
            file_system_policy={
                "Version": "2012-10-17",
                "Id": "efs-prevent-anonymous-access-policy",
                "Statement": [
                    {
                        "Sid": "efs-statement",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": "*"
                        },
                        "Action": [
                            "elasticfilesystem:ClientRootAccess",
                            "elasticfilesystem:ClientWrite",
                            "elasticfilesystem:ClientMount"
                        ],
                        "Condition": {
                            "Bool": {
                                "elasticfilesystem:AccessedViaMountTarget": "true"
                            }
                        }
                    }
                ]
            }
        )
        self.add_common_tags(file_system)
        self.add_backup_tags(file_system)
        file_system.cfn_options.deletion_policy = self.deletion_policy

        security_group_ids = [self.security_group.security_group_id]

        mount_targets = []
        for index, subnet in enumerate(self.get_subnets()):
            mount_target_construct_id = f'{self.construct_id}-mount-target-{index + 1}'
            mount_target = efs.CfnMountTarget(
                scope=file_system,
                id=mount_target_construct_id,
                file_system_id=file_system.ref,
                security_groups=security_group_ids,
                subnet_id=subnet.subnet_id
            )
            self.add_common_tags(mount_target)
            mount_targets.append(mount_target)

        return file_system, mount_targets

    def build_cloudwatch_monitoring(self) -> Tuple[sns.Topic,
                                                   cloudwatch.Alarm,
                                                   cloudwatch.Alarm,
                                                   lambda_.Function,
                                                   sns.Subscription]:

        sns_topic_name = f'{self.name}-alarms'
        sns_topic = SNSTopic(
            self.context, sns_topic_name, self.file_system,
            topic_name=self.build_resource_name(sns_topic_name),
            display_name=f'({self.cluster_name}) {sns_topic_name}',
            master_key=self.context.config().get_string('cluster.sns.kms_key_id')
        )

        sns_topic_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['sns:Publish'],
            resources=[sns_topic.topic_arn],
            principals=[self.build_service_principal('cloudwatch')],
            conditions={
                'ArnLike': {
                    'aws:SourceArn': self.aws_account_arn
                }
            }
        )
        sns_topic.add_to_resource_policy(sns_topic_policy)

        alarm_props = {
            'context': self.context,
            'scope': self.file_system,
            'metric_name': 'BurstCreditBalance',
            'metric_namespace': 'AWS/EFS',
            'metric_dimensions': {
                'FileSystemId': self.file_system.ref
            },
            'evaluation_periods': 10,
            'period_seconds': 60,
            'statistic': 'Average',
            'actions': [cw_actions.SnsAction(sns_topic)]
        }

        low_alarm = CloudWatchAlarm(
            **alarm_props,
            name=f'{self.name}-burst-credit-balance-low',
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
            threshold=10000000
        )

        high_alarm = CloudWatchAlarm(
            **alarm_props,
            name=f'{self.name}-burst-credit-balance-high',
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            threshold=2000000000000
        )

        efs_throughput_lambda_name = f'{self.name}-throughput'
        efs_throughput_lambda_role = Role(
            self.context,
            f'{efs_throughput_lambda_name}-role',
            self.scope,
            f'IAM role to monitor {self.name} throughput for Cluster: {self.cluster_name}',
            assumed_by=['lambda'],
            inline_policies=[
                Policy(
                    context=self.context,
                    name=f'{efs_throughput_lambda_name}-policy',
                    scope=self.scope,
                    policy_template_name='efs-throughput-lambda.yml'
                )
            ]
        )

        efs_throughput_lambda = LambdaFunction(
            context=self.context,
            name=efs_throughput_lambda_name,
            scope=self.file_system,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_efs_throughput',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            role=efs_throughput_lambda_role,
            log_retention_role=self.log_retention_role
        )
        efs_throughput_lambda.add_environment('EFSBurstCreditLowThreshold', '10000000')
        efs_throughput_lambda.add_environment('EFSBurstCreditHighThreshold', '2000000000000')
        efs_throughput_lambda.add_permission('InvokePermissions',
                                             principal=self.build_service_principal('sns'),
                                             action='lambda:InvokeFunction')

        sns_topic_subscription = SNSSubscription(
            context=self.context,
            name=f'{sns_topic_name}-subscription',
            scope=sns_topic,
            protocol=sns.SubscriptionProtocol.LAMBDA,
            endpoint=efs_throughput_lambda.function_arn,
            topic=sns_topic
        )

        return sns_topic, low_alarm, high_alarm, efs_throughput_lambda, sns_topic_subscription


class FSxForLustre(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc,
                 fsx_lustre_config: Dict,
                 security_group: ec2.SecurityGroup,
                 subnets: Optional[List[ec2.ISubnet]] = None):
        super().__init__(context, name)

        self.scope = scope
        self.vpc = vpc
        self.security_group = security_group
        self.subnets = subnets

        self.kms_key_id = Utils.get_value_as_string('kms_key_id', fsx_lustre_config)
        self.deployment_type = Utils.get_value_as_string('deployment_type', fsx_lustre_config)
        self.storage_type = Utils.get_value_as_string('storage_type', fsx_lustre_config)
        self.per_unit_storage_throughput = Utils.get_value_as_int('per_unit_storage_throughput', fsx_lustre_config)
        self.storage_capacity = Utils.get_value_as_int('storage_capacity', fsx_lustre_config)
        self.drive_cache_type = Utils.get_value_as_int('drive_cache_type', fsx_lustre_config)

        self.file_system = self.build_file_system()

    def get_subnets(self) -> List[ec2.ISubnet]:
        if self.subnets is not None:
            return self.subnets
        else:
            return self.vpc.private_subnets

    def build_file_system(self) -> fsx.CfnFileSystem:

        deployment_type = self.deployment_type
        storage_type = self.storage_type
        per_unit_storage_throughput = None
        drive_cache_type = None
        if storage_type == 'SSD':
            if deployment_type == 'PERSISTENT_1':
                per_unit_storage_throughput = self.per_unit_storage_throughput
        else:
            drive_cache_type = self.drive_cache_type

        security_group_ids = [self.security_group.security_group_id]

        first_subnet = self.get_subnets()[0]
        file_system = fsx.CfnFileSystem(
            scope=self.scope,
            id=self.name,
            file_system_type='LUSTRE',
            subnet_ids=[first_subnet.subnet_id],
            lustre_configuration=fsx.CfnFileSystem.LustreConfigurationProperty(
                deployment_type=deployment_type,
                per_unit_storage_throughput=per_unit_storage_throughput,
                drive_cache_type=drive_cache_type
            ),
            security_group_ids=security_group_ids,
            kms_key_id=self.kms_key_id,
            storage_capacity=self.storage_capacity
        )
        self.add_common_tags(file_system)
        self.add_backup_tags(file_system)
        return file_system
