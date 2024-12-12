#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from typing import Optional, Union

import aws_cdk as cdk
import constructs
from aws_cdk import Duration
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk.aws_events import Schedule
from res.constants import (  # type: ignore
    AD_SYNC_LOCK_TABLE,
    LOCK_DB_HASH_KEY,
    LOCK_DB_RANGE_KEY,
    MODULE_NAME_DIRECTORY_SERVICE,
)

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constants import (
    RES_COMMON_LAMBDA_RUNTIME,
    RES_ECR_REPO_NAME_SUFFIX,
)
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.ddb_tables.base import RESDDBTableBase
from idea.infrastructure.install.ddb_tables.list import RESDDBTable
from idea.infrastructure.install.handlers import scheduled_ad_sync_handler
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.utils import InfraUtils
from idea.infrastructure.resources.lambda_functions.custom_resource.ad_sync_task_terminator_lambda import (
    handler,
)


class ADSyncStack(ResBaseConstruct):
    """
    Setup infrastructure for the AD Sync process
    """

    def __init__(
        self,
        scope: constructs.Construct,
        lambda_layer: _lambda.LayerVersion,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
        registry_name: Optional[str] = None,
    ):
        self.parameters = parameters
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.registry_name = registry_name if registry_name else ""
        self.lambda_layer = lambda_layer

        super().__init__(
            self.cluster_name,
            cdk.Aws.REGION,
            "ad-sync",
            scope,
            parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "ad-sync",
            description="Nested Stack for supporting AD Sync",
        )

        vpc = ec2.Vpc.from_vpc_attributes(
            self.nested_stack,
            "ExistingVpc",
            availability_zones=[""],
            vpc_id=self.parameters.get_str(CommonKey.VPC_ID),
            private_subnet_ids=[
                cdk.Fn.select(
                    0,
                    self.parameters.get(
                        CommonKey.INFRASTRUCTURE_HOST_SUBNETS
                    ).value_as_list,
                ),
                cdk.Fn.select(
                    1,
                    self.parameters.get(
                        CommonKey.INFRASTRUCTURE_HOST_SUBNETS
                    ).value_as_list,
                ),
            ],
        )
        self.ecs_cluster = ecs.Cluster(
            self.nested_stack,
            "ADSyncCluster",
            vpc=vpc,
            cluster_name=f"{self.cluster_name}-ad-sync-cluster",
        )

        self.build_ad_sync_security_group(vpc)
        self.build_ad_sync_lock_table()
        self.build_scheduled_event_ad_sync_infra()
        self.build_ad_sync_task_definition()
        self.terminate_ad_sync_ecs_task()

        self.nested_stack.node.add_dependency(self.lambda_layer)
        self.apply_permission_boundary(self.nested_stack)

    def build_ad_sync_security_group(self, vpc: ec2.IVpc) -> None:
        """
        Create the AD Sync Security Group.
        """
        self.ad_sync_security_group = ec2.SecurityGroup(
            self.nested_stack,
            "ADSyncSecurityGroup",
            security_group_name=f"{self.cluster_name}-ad-sync-security-group",
            vpc=vpc,
            description="Security group for AD Sync task",
        )

        self.ad_sync_security_group.add_egress_rule(
            ec2.Peer.ipv4("0.0.0.0/0"),
            ec2.Port.all_traffic(),
            description="Allow all outbound traffic by default",
        )
        self.add_common_tags(self.ad_sync_security_group)

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

    def build_scheduled_event_ad_sync_infra(self) -> None:
        lambda_name = f"{self.cluster_name}-scheduled-ad-sync"
        scheduled_ad_sync_lambda_role = iam.Role(
            self.nested_stack,
            id="scheduled-ad-sync-role",
            role_name=f"{lambda_name}-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description=f"{lambda_name}-role",
        )

        scheduled_ad_sync_lambda_role.attach_inline_policy(
            iam.Policy(
                self.nested_stack,
                id="scheduled-ad-sync-policy",
                policy_name=f"{lambda_name}-policy",
                statements=[
                    iam.PolicyStatement(
                        actions=["logs:CreateLogGroup"],
                        sid="CloudWatchLogsPermissions",
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "logs:DeleteLogStream",
                        ],
                        sid="CloudWatchLogStreamPermissions",
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "dynamodb:GetItem",
                            "dynamodb:Scan",
                        ],
                        sid="ClusterSettingsTablePermissions",
                        resources=[
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.cluster-settings",
                        ],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:DeleteItem",
                        ],
                        sid="ADSyncLockTablePermissions",
                        resources=[
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.ad-sync.distributed-lock",
                        ],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "ecs:RunTask",
                            "ecs:StopTask",
                            "ecs:ListTasks",
                        ],
                        resources=["*"],
                        conditions={
                            "ArnEquals": {"ecs:cluster": self.ecs_cluster.cluster_arn}
                        },
                    ),
                    iam.PolicyStatement(
                        actions=["iam:PassRole"],
                        resources=[
                            f"arn:{cdk.Aws.PARTITION}:iam::{cdk.Aws.ACCOUNT_ID}:role/{self.cluster_name}-ad-sync-task-role",
                        ],
                    ),
                    iam.PolicyStatement(
                        actions=["ec2:DescribeSecurityGroups"],
                        resources=["*"],
                    ),
                ],
            )
        )
        self.add_common_tags(scheduled_ad_sync_lambda_role)

        scheduled_ad_sync_lambda = _lambda.Function(
            self.nested_stack,
            id="scheduled-ad-sync",
            function_name=lambda_name,
            description=f"Lambda to send scheduled event to trigger ad sync",
            environment={
                "environment_name": self.cluster_name,
            },
            timeout=Duration.seconds(180),
            role=scheduled_ad_sync_lambda_role,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            **InfraUtils.get_handler_and_code_for_function(
                scheduled_ad_sync_handler.handler
            ),
            layers=[self.lambda_layer],
        )
        self.add_common_tags(scheduled_ad_sync_lambda)

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
        task_definition = ecs.TaskDefinition(
            self.nested_stack,
            id="ad-sync-task-definition",
            compatibility=ecs.Compatibility.FARGATE,
            task_role=ad_sync_task_role,
            execution_role=ad_sync_task_role,
            memory_mib="1024",
            cpu="512",
            family=f"{self.cluster_name}-ad-sync-task-definition",
        )

        commands = "\n".join(
            [
                "source venv/bin/activate",
                "res-ad-sync",
            ]
        )
        task_definition.add_container(
            "ad-sync-task-container",
            image=ecs.ContainerImage.from_registry(self.registry_name),
            command=["/bin/sh", "-c", f"/bin/sh -ex <<'EOC'\n{commands}\nEOC\n"],
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
        self.add_common_tags(task_definition)

    def build_ad_sync_task_role(self) -> iam.Role:
        ad_sync_task_role = iam.Role(
            self.nested_stack,
            id="ad-sync-task-role",
            role_name=f"{self.cluster_name}-ad-sync-task-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description=f"ad-sync-task-role",
        )
        ad_sync_task_role.attach_inline_policy(
            iam.Policy(
                self.nested_stack,
                id="ad-sync-task-policy",
                policy_name=f"{self.cluster_name}-ad-sync-task-policy",
                statements=[
                    iam.PolicyStatement(
                        actions=["logs:CreateLogGroup"],
                        sid="CloudWatchLogsPermissions",
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "logs:DeleteLogStream",
                        ],
                        sid="CloudWatchLogStreamPermissions",
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=["secretsmanager:GetSecretValue"],
                        sid="SecretsManagerPermissions",
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=[
                            "dynamodb:GetItem",
                            "dynamodb:Query",
                            "dynamodb:Scan",
                            "dynamodb:UpdateItem",
                            "dynamodb:PutItem",
                            "dynamodb:DeleteItem",
                        ],
                        sid="DynamoDBPermissions",
                        resources=[
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.cluster-settings",
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.accounts.users",
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.accounts.users/index/*",
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.accounts.groups",
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.accounts.group-members",
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.projects",
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.projects/index/*",
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.authz.role-assignments",
                            f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.authz.role-assignments/index/*",
                        ],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        resources=[
                            f"arn:{cdk.Aws.PARTITION}:ecr:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:repository/{self.cluster_name}{RES_ECR_REPO_NAME_SUFFIX}"
                        ],
                        actions=[
                            "ecr:BatchGetImage",
                            "ecr:DescribeRepositories",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:GetLifecyclePolicy",
                            "ecr:GetRepositoryPolicy",
                            "ecr:ListTagsForResource",
                        ],
                        sid="ECRPermissions",
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        resources=["*"],
                        actions=[
                            "ecr:GetAuthorizationToken",
                        ],
                        sid="ECRAuthorizationPermissions",
                    ),
                ],
            )
        )
        self.add_common_tags(ad_sync_task_role)

        return ad_sync_task_role

    # Create a custom lambda to terminate AD sync ECS task before deleting AD sync ECS cluster
    def terminate_ad_sync_ecs_task(self) -> None:
        lambda_name = f"{self.cluster_name}-terminate-ad-sync-ecs-task"
        terminate_ad_sync_ecs_task_role = iam.Role(
            self.nested_stack,
            id="terminate-ad-sync-ecs-task-role",
            role_name=f"{lambda_name}-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description=f"{lambda_name}-role",
        )

        terminate_ad_sync_ecs_task_policy = iam.Policy(
            self.nested_stack,
            id="terminate-ad-sync-ecs-task-policy",
            policy_name=f"{lambda_name}-policy",
            statements=[
                iam.PolicyStatement(
                    actions=["logs:CreateLogGroup"],
                    sid="CloudWatchLogsPermissions",
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DeleteLogStream",
                    ],
                    sid="CloudWatchLogStreamPermissions",
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:DeleteItem",
                    ],
                    sid="ADSyncLockTablePermissions",
                    resources=[
                        f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.ad-sync.distributed-lock",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "ecs:StopTask",
                        "ecs:ListTasks",
                        "ecs:DescribeTasks",
                    ],
                    resources=["*"],
                    conditions={
                        "ArnEquals": {"ecs:cluster": self.ecs_cluster.cluster_arn}
                    },
                ),
                iam.PolicyStatement(
                    actions=["iam:PassRole"],
                    resources=[
                        f"arn:{cdk.Aws.PARTITION}:iam::{cdk.Aws.ACCOUNT_ID}:role/{self.cluster_name}-ad-sync-task-role",
                    ],
                ),
            ],
        )
        terminate_ad_sync_ecs_task_role.attach_inline_policy(
            terminate_ad_sync_ecs_task_policy
        )
        self.add_common_tags(terminate_ad_sync_ecs_task_role)

        terminate_ad_sync_ecs_task_lambda = _lambda.Function(
            self.nested_stack,
            id="terminate-ad-sync-ecs-task",
            function_name=lambda_name,
            description=f"Custom lambda to terminate AD sync ECS task before deleting AD sync ECS cluster",
            environment={
                "environment_name": self.cluster_name,
            },
            timeout=Duration.seconds(300),
            role=terminate_ad_sync_ecs_task_role,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            **InfraUtils.get_handler_and_code_for_function(handler.handler),
            layers=[self.lambda_layer],
        )
        self.add_common_tags(terminate_ad_sync_ecs_task_lambda)

        terminate_ad_sync_ecs_task_custom_resource = cdk.CustomResource(
            self.nested_stack,
            id="terminate-ad-sync-ecs-task-custom-resource",
            service_token=terminate_ad_sync_ecs_task_lambda.function_arn,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::TerminateADSyncECSTask",
        )

        terminate_ad_sync_ecs_task_custom_resource.node.add_dependency(
            terminate_ad_sync_ecs_task_policy
        )
        terminate_ad_sync_ecs_task_custom_resource.node.add_dependency(self.ecs_cluster)
        terminate_ad_sync_ecs_task_custom_resource.node.add_dependency(
            self.ad_sync_lock_table
        )
