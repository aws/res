#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from typing import Any, Dict, Optional, Union

import aws_cdk
import aws_cdk as cdk
import constructs
from aws_cdk import CfnCondition, Fn
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_events import Schedule
from res.constants import (  # type: ignore
    AD_SYNC_LOCK_TABLE,
    AD_SYNC_STATUS_SUBMISSION_TIME_KEY,
    AD_SYNC_STATUS_TABLE,
    AD_SYNC_STATUS_TASK_ID_KEY,
    AD_SYNC_STATUS_TTL_KEY,
    ENVIRONMENT_NAME_KEY,
    LOCK_DB_HASH_KEY,
    LOCK_DB_RANGE_KEY,
    MODULE_NAME_DIRECTORY_SERVICE,
)
from res.resources import cluster_settings  # type: ignore

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.constructs import cognito as cognito_
from idea.infrastructure.install.constructs import lambda_
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.constructs.ec2 import SecurityGroup
from idea.infrastructure.install.constructs.iam import Role
from idea.infrastructure.install.constructs.sqs import SQSQueue
from idea.infrastructure.install.ddb_tables.base import RESDDBTableBase
from idea.infrastructure.install.ddb_tables.list import RESDDBTable
from idea.infrastructure.install.handlers import scheduled_ad_sync_handler
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.cognito_user_pool import CognitoUserPoolKey
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import (
    ADSyncTaskPolicy,
    DisableCognitoProtectionPolicy,
    GetUserPoolClientSecretPolicy,
    ScheduledADSyncPolicy,
    TerminateADSyncTaskPolicy,
)
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.resources.lambda_functions.custom_resource.ad_sync_task_terminator_lambda import (
    handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.deletion_cleanup_resources_lambda import (
    handler as cleanup_handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.get_user_pool_client_secret_lambda import (
    get_user_pool_client_secret_handler,
)


class IdentityStack(ResBaseConstruct):
    """
    Setup infrastructure for the AD Sync process
    """

    def __init__(
        self,
        scope: constructs.Construct,
        lambda_layer: _lambda.LayerVersion,
        cluster_stack: ClusterStack,
        external_alb_dns_name: str,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
        registry_name: Optional[str] = None,
    ):
        self.parameters = parameters
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.registry_name = registry_name if registry_name else ""
        self.external_alb_dns_name = external_alb_dns_name
        self.lambda_layer = lambda_layer
        self.aws_region = cdk.Aws.REGION
        self.cluster_stack = cluster_stack

        super().__init__(
            scope,
            "identity",
            self.cluster_name,
            parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "identity",
            description="Nested Stack for supporting AD Sync",
        )
        self.has_iam_prefix_condition = InfraUtils.get_iam_prefix_condition(
            self.nested_stack, parameters
        )

        self.has_iam_path_condition = InfraUtils.get_iam_path_condition(
            self.nested_stack, parameters
        )

        self.cognito_user_pool_id_not_provided = (
            InfraUtils.get_cognito_user_pool_id_not_provided_condition(
                self.nested_stack, parameters
            )
        )

        self.cluster_settings = ClusterSettings(self.cluster_name, self.nested_stack)
        self.arn_builder = ArnBuilder(
            self.cluster_name, self.cluster_settings, parameters=parameters
        )

        vpc = cluster_stack.vpc
        self.ecs_cluster = ecs.Cluster(
            self.nested_stack,
            "ADSyncCluster",
            vpc=vpc,
            cluster_name=f"{self.cluster_name}-ad-sync-cluster",
        )

        self.build_ad_sync_security_group(vpc)
        self.build_ad_sync_lock_table()
        self.build_ad_sync_status_table()
        self.build_scheduled_event_ad_sync_infra()
        self.build_ad_sync_task_definition()
        self.terminate_ad_sync_ecs_task()
        self.build_ad_automation_sqs_queue()
        self.build_cognito_idp()
        self.disable_cognito_protection()
        self.update_cluster_settings()

        self.nested_stack.node.add_dependency(self.lambda_layer)
        self.apply_permission_boundary(self.nested_stack)
        self.add_common_tags(self.nested_stack)

    def build_ad_sync_security_group(self, vpc: ec2.IVpc) -> None:
        """
        Create the AD Sync Security Group.
        """
        self.ad_sync_security_group = SecurityGroup(
            scope=self.nested_stack,
            vpc=vpc,
            name="ad-sync-security-group",
            description="Security group for AD Sync task",
            allow_all_outbound=True,
            parameters=self.parameters,
        )

    def build_ad_sync_lock_table(self) -> None:
        """
        Create the DynamoDB table used to lock AD Sync operations.
        """
        ad_sync_lock_table: RESDDBTable = RESDDBTable(
            id=AD_SYNC_LOCK_TABLE,
            module_id=MODULE_NAME_DIRECTORY_SERVICE,
            table_props=dynamodb.TableProps(
                partition_key=dynamodb.Attribute(
                    name=LOCK_DB_HASH_KEY, type=dynamodb.AttributeType.STRING
                ),
                sort_key=dynamodb.Attribute(
                    name=LOCK_DB_RANGE_KEY, type=dynamodb.AttributeType.STRING
                ),
            ),
        )
        self.ad_sync_lock_table = RESDDBTableBase(
            self.nested_stack,
            ad_sync_lock_table.id,
            self.cluster_name,
            ad_sync_lock_table,
        ).ddb_table

    def build_ad_sync_status_table(self) -> None:
        """
        Create the DynamoDB table for tracking AD Sync ECS task status.
        """
        ad_sync_status_table: RESDDBTable = RESDDBTable(
            id=AD_SYNC_STATUS_TABLE,
            module_id=MODULE_NAME_DIRECTORY_SERVICE,
            table_props=dynamodb.TableProps(
                partition_key=dynamodb.Attribute(
                    name=AD_SYNC_STATUS_TASK_ID_KEY, type=dynamodb.AttributeType.STRING
                ),
                sort_key=dynamodb.Attribute(
                    name=AD_SYNC_STATUS_SUBMISSION_TIME_KEY,
                    type=dynamodb.AttributeType.NUMBER,
                ),
                time_to_live_attribute=AD_SYNC_STATUS_TTL_KEY,
            ),
        )

        self.ad_sync_status_table = RESDDBTableBase(
            self.nested_stack,
            ad_sync_status_table.id,
            self.cluster_name,
            ad_sync_status_table,
        ).ddb_table

    def build_scheduled_event_ad_sync_infra(self) -> None:
        lambda_name = "scheduled-ad-sync"
        scheduled_ad_sync_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="Lambda to send scheduled event to trigger ad sync",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=scheduled_ad_sync_handler.handler,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=ScheduledADSyncPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.cluster_stack.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
            environment={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
            },
        )

        # CloudFormation that doesn't support Tags for Event Bridge rule currently:
        # Check https://github.com/aws/aws-cdk/issues/4907
        schedule_trigger_rule = events.Rule(
            self.nested_stack,
            id="ad-sync-schedule-rule",
            enabled=True,
            rule_name=f"{self.cluster_name}-ad-sync-schedule-rule",
            description="Event Rule to Trigger schedule AD sync EVERY hour",
            schedule=Schedule.cron(minute="0", hour="0/1"),  # every 1 hour
        )

        schedule_trigger_rule.add_target(
            events_targets.LambdaFunction(
                scheduled_ad_sync_lambda,
            )
        )

    def build_ad_sync_task_definition(self) -> None:
        ad_sync_task_role = self.build_ad_sync_task_role()
        self.task_definition = ecs.TaskDefinition(
            self.nested_stack,
            id="ad-sync-task-definition",
            compatibility=ecs.Compatibility.FARGATE,
            task_role=ad_sync_task_role,
            execution_role=ad_sync_task_role,
            memory_mib="1024",
            cpu="512",
            family=f"{self.cluster_name}-ad-sync-task-definition",
        )

        commands = " && ".join(
            [
                "source venv/bin/activate",
                "exec res-ad-sync",
            ]
        )
        self.task_definition.add_container(
            "ad-sync-task-container",
            image=ecs.ContainerImage.from_registry(self.registry_name),
            command=["/bin/sh", "-exc", commands],
            environment={
                "environment_name": self.cluster_name,
                "AWS_DEFAULT_REGION": cdk.Aws.REGION,
            },
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_group=logs.LogGroup(
                    self.nested_stack,
                    "ad-sync-task-log-group",
                    log_group_name=f"{self.cluster_name}/ad-sync",
                    removal_policy=cdk.RemovalPolicy.DESTROY,
                ),
            ),
        )
        self.add_common_tags(self.task_definition)

    def build_ad_sync_task_role(self) -> Role:
        ad_sync_task_policy = ADSyncTaskPolicy(
            self.nested_stack,
            "ad-sync-task-policy",
            self.arn_builder,
            self.parameters,
        )
        ad_sync_task_role = Role(
            scope=self.nested_stack,
            name="ad-sync-task-role",
            description="ad-sync-task-role",
            assumed_by=["ecs-tasks"],
            inline_policies=[
                ad_sync_task_policy,
            ],
            parameters=self.parameters,
            arn_builder=self.arn_builder,
        )

        return ad_sync_task_role

    # Create a custom lambda to terminate AD sync ECS task before deleting AD sync ECS cluster
    def terminate_ad_sync_ecs_task(self) -> None:
        lambda_name = "terminate-ad-sync-ecs-task"
        terminate_ad_sync_ecs_task_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="Custom lambda to terminate AD sync ECS task before deleting AD sync ECS cluster",  # type: ignore
            timeout=cdk.Duration.seconds(300),  # type: ignore
            handler=handler.handler,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=TerminateADSyncTaskPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.cluster_stack.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
            environment={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
            },
        )

        terminate_ad_sync_ecs_task_custom_resource = cdk.CustomResource(
            self.nested_stack,
            id="terminate-ad-sync-ecs-task-custom-resource",
            service_token=terminate_ad_sync_ecs_task_lambda.function_arn,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::TerminateADSyncECSTask",
        )

        terminate_ad_sync_ecs_task_custom_resource.node.add_dependency(self.ecs_cluster)
        terminate_ad_sync_ecs_task_custom_resource.node.add_dependency(
            self.ad_sync_lock_table
        )

    def update_cluster_settings(self) -> None:
        identity_cluster_settings = self.build_identity_cluster_settings()

        for module_id, settings in identity_cluster_settings.items():
            cdk.CustomResource(
                self.nested_stack,
                f"identity-cluster-settings-{module_id}",
                service_token=self.cluster_stack.cluster_settings_lambda.function_arn,
                properties={
                    "cluster_name": self.cluster_name,
                    "module_id": module_id,
                    "version": self.get_res_release_version(),
                    "settings": settings,
                },
                resource_type="Custom::ClusterSettings",
            )

    def build_ad_automation_sqs_queue(self) -> None:
        sqs_kms_key_id = self.cluster_settings.kms_sqs_key_id

        ad_automation_dlq = SQSQueue(
            "ad-automation-dlq",
            self.nested_stack,
            self.arn_builder,
            self.parameters,
            fifo=True,
            content_based_deduplication=True,
            encryption_master_key=sqs_kms_key_id,
        )

        self.ad_automation_sqs_queue = SQSQueue(
            "ad-automation",
            self.nested_stack,
            self.arn_builder,
            self.parameters,
            fifo=True,
            content_based_deduplication=True,
            encryption_master_key=sqs_kms_key_id,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=30, queue=ad_automation_dlq
            ),
        )

    def build_cognito_idp(self) -> None:
        removal_policy = cdk.RemovalPolicy(self.cluster_settings.cognito_removal_policy)
        self.new_user_pool = cognito_.UserPool(
            self.nested_stack,
            "cognito-user-pool",
            self.parameters,
            domain_uuid=self.cluster_settings.random_uuid,  # type: ignore
            props=cognito.UserPoolProps(
                removal_policy=removal_policy,
                user_invitation=cognito.UserInvitationConfig(
                    email_subject=cognito_.UserPool.get_cognito_user_invitation_email_subject(
                        self.cluster_name
                    ),
                    email_body=cognito_.UserPool.get_user_invitation_email_body(
                        self.cluster_name, self.external_alb_dns_name
                    ),
                ),
                self_sign_up_enabled=True,
                auto_verify=cognito.AutoVerifiedAttrs(
                    email=True,
                    phone=False,
                ),
            ),
        )
        # Only create a Cognito user pool if no external user pool ID is provided
        self.new_user_pool.apply_condition_aspect(
            self.cognito_user_pool_id_not_provided
        )

        self.user_pool = cognito.UserPool.from_user_pool_id(
            self.nested_stack,
            "cognito-user-pool-from-id",
            Fn.condition_if(
                self.cognito_user_pool_id_not_provided.logical_id,
                self.new_user_pool.user_pool.user_pool_id,
                self.parameters.get_str(CognitoUserPoolKey.COGNITO_USER_POOL_ID),
            ).to_string(),
        )
        self.user_pool_domain_url = Fn.condition_if(
            self.cognito_user_pool_id_not_provided.logical_id,
            self.new_user_pool.get_domain_url(),
            self.parameters.get_str(CognitoUserPoolKey.COGNITO_USER_POOL_DOMAIN_URL),
        )

        client = self.user_pool.add_client(
            id="vdi-client",
            auth_flows=cognito.AuthFlow(admin_user_password=True),
            prevent_user_existence_errors=True,
            read_attributes=cdk.aws_cognito.ClientAttributes().with_custom_attributes(
                "uid"
            ),
            write_attributes=cdk.aws_cognito.ClientAttributes().with_standard_attributes(
                email=True
            ),
            user_pool_client_name=f"{self.cluster_name}-vdi",
            disable_o_auth=True,
        )
        self.vdi_client_id = client.user_pool_client_id

        lambda_name = "oauth-credentials"
        self.oauth_credentials_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="Get OAuth Credentials for a ClientId in UserPool",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=get_user_pool_client_secret_handler.handler,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=GetUserPoolClientSecretPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.parameters,
            log_retention_role=self.cluster_stack.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
        )

    def disable_cognito_protection(self) -> None:
        lambda_name = "disable-cognito-protection"
        disable_cognito_protection_lambda = lambda_.Function(
            self.nested_stack,
            lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="Custom lambda to disable cognito user pool protection when deleting RES environment",  # type: ignore
            timeout=cdk.Duration.seconds(900),  # type: ignore
            handler=cleanup_handler.disable_cognito_protection_handler,
            parameters=self.parameters,
            layers=[self.lambda_layer],  # type: ignore
            initial_policy=DisableCognitoProtectionPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            environment={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
                "cognito_user_pool_id": Fn.condition_if(
                    self.cognito_user_pool_id_not_provided.logical_id,
                    self.user_pool.user_pool_id,
                    # Do not change the protection status on external Cognito user pool
                    aws_cdk.Aws.NO_VALUE,
                ).to_string(),
            },
            log_retention_role=self.cluster_stack.roles[constants.LOG_RETENTION_ROLE_NAME],  # type: ignore
        )

        self.disable_cognito_protection_custom_resource = cdk.CustomResource(
            self.nested_stack,
            id=f"{lambda_name}-custom-resource",
            service_token=disable_cognito_protection_lambda.function_arn,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::DisableCognitoProtection",
        )

        self.disable_cognito_protection_custom_resource.node.add_dependency(
            self.user_pool
        )

    def build_identity_cluster_settings(self) -> Dict[str, Any]:
        return {
            "ad-sync": {
                "security_group_id": self.ad_sync_security_group.security_group_id,
                "task_cluster": self.ecs_cluster.cluster_name,
                "task_definition": self.task_definition.family,
            },
            "directoryservice": {
                "ad_automation.sqs_queue_url": self.ad_automation_sqs_queue.queue_url,
                "ad_automation.sqs_queue_arn": self.ad_automation_sqs_queue.queue_arn,
            },
            "identity-provider": {
                "cognito.user_pool_id": self.user_pool.user_pool_id,
                "cognito.vdi_client_id": self.vdi_client_id,
                "cognito.provider_url": f"https://cognito-idp.{self.aws_region}.amazonaws.com/{self.user_pool.user_pool_id}",
                "cognito.domain_url": self.user_pool_domain_url,
                "cognito.oauth_credentials_lambda_arn": self.oauth_credentials_lambda.function_arn,
            },
        }
