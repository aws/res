#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Optional, TypedDict, Union

import aws_cdk
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks
from constructs import Construct, DependencyGroup

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.commands import create
from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.handlers import installer_handlers
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.permissions import Permissions
from idea.infrastructure.install.utils import InfraUtils


class TaskEnvironment(TypedDict):
    AWS_REGION: str
    AWS_DEFAULT_REGION: str
    IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER: str


class Tasks(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        registry_name: str,
        installer_registry_name: str,
        params: Union[RESParameters, BIParameters],
        dependency_group: DependencyGroup,
        lambda_layer_arn: str,
    ):

        super().__init__(scope, id)

        self.lambda_layer_arn = lambda_layer_arn
        self.registry_name = registry_name
        self.installer_registry_name = installer_registry_name

        vpc = ec2.Vpc.from_vpc_attributes(
            self,
            "ExistingVpc",
            availability_zones=[""],
            vpc_id=params.get_str(CommonKey.VPC_ID),
            private_subnet_ids=[
                aws_cdk.Fn.select(
                    0, params.get(CommonKey.INFRASTRUCTURE_HOST_SUBNETS).value_as_list
                ),
                aws_cdk.Fn.select(
                    1, params.get(CommonKey.INFRASTRUCTURE_HOST_SUBNETS).value_as_list
                ),
            ],
        )
        self.cluster = ecs.Cluster(self, "Cluster", vpc=vpc)
        self.permissions = Permissions(
            self,
            "Permissions",
            dependency_group=dependency_group,
            environment_name=params.get_str(CommonKey.CLUSTER_NAME),
        )
        self.params = params
        self.dependency_group = dependency_group
        self.dependency_group.add(self.cluster)

    def get_task_definition(
        self,
        name: str,
        environment: TaskEnvironment,
        command: list[str],
        task_role: Optional[iam.Role] = None,
    ) -> ecs.FargateTaskDefinition:
        task_definition_name = f"{name}TaskDef"
        task_definition = ecs.FargateTaskDefinition(
            self,
            task_definition_name,
            task_role=task_role,
            execution_role=task_role,
            memory_limit_mib=4096,
            cpu=2048,
            family=f"{self.params.get_str(CommonKey.CLUSTER_NAME)}{task_definition_name}",
        )
        commands = "\n".join(command)
        task_definition.add_container(
            f"{name}Container",
            image=ecs.ContainerImage.from_registry(self.installer_registry_name),
            environment=dict(**environment),
            command=["/bin/sh", "-c", f"/bin/sh -ex <<'EOC'\n{commands}\nEOC\n"],
            logging=ecs.LogDriver.aws_logs(stream_prefix=f"{name}LogStream"),
        )

        self.dependency_group.add(task_definition)

        return task_definition

    def get_create_task(self) -> sfn_tasks.EcsRunTask:
        return self.get_task(
            name="Create",
            command=create.Create(
                params=self.params,
                lambda_layer_arn=self.lambda_layer_arn,
            ).get_commands(),
            task_role=self.permissions.pipeline_role,
        )

    def get_update_task(self) -> sfn_tasks.EcsRunTask:
        return self.get_task(
            name="Update",
            command=[
                "res-admin --version",
                f"res-admin config set Key=shared_library_arn,Type=str,Value={self.lambda_layer_arn} --force --cluster-name {self.params.get_str(CommonKey.CLUSTER_NAME)} --aws-region {aws_cdk.Aws.REGION}",
                f"res-admin deploy all --upgrade --cluster-name {self.params.get_str(CommonKey.CLUSTER_NAME)} --aws-region {aws_cdk.Aws.REGION}",
            ],
            task_role=self.permissions.pipeline_role,
        )

    def get_delete_task(self) -> sfn_tasks.EcsRunTask:
        return self.get_task(
            name="Delete",
            command=[
                "res-admin --version",
                (
                    "res-admin delete-cluster --delete-databases --delete-bootstrap --force "
                    f"--cluster-name {self.params.get_str(CommonKey.CLUSTER_NAME)} --aws-region {aws_cdk.Aws.REGION}"
                ),
            ],
            task_role=self.permissions.pipeline_role,
        )

    def get_installer_ecr_pull_image_task(self) -> sfn_tasks.CodeBuildStartBuild:
        resources = [
            self.get_ecr_arn_from_private_registry_name(self.installer_registry_name)
        ]
        if self.registry_name.startswith("public"):
            commands = []
        else:
            resources.append(
                self.get_ecr_arn_from_private_registry_name(self.registry_name)
            )
            commands = [
                "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${PROVIDED_REPO_URI}"
            ]

        project = codebuild.Project(
            self,
            "CopyImageToInstallerEcr",
            project_name=aws_cdk.Fn.join(
                "-",
                [
                    self.params.get_str(CommonKey.CLUSTER_NAME),
                    "copyImageToInstallerEcr",
                ],
            ),
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "build": {
                            "commands": [
                                *commands,
                                "docker pull ${PROVIDED_REPO_URI}",
                                "docker tag ${PROVIDED_REPO_URI} ${INSTALLER_REPO_URI}",
                                "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${INSTALLER_REPO_URI}",
                                "docker push ${INSTALLER_REPO_URI}",
                            ]
                        }
                    },
                }
            ),
            environment_variables={
                "AWS_REGION": codebuild.BuildEnvironmentVariable(
                    value=aws_cdk.Aws.REGION
                ),
                "INSTALLER_REPO_URI": codebuild.BuildEnvironmentVariable(
                    value=self.installer_registry_name
                ),
                "PROVIDED_REPO_URI": codebuild.BuildEnvironmentVariable(
                    value=self.registry_name
                ),
            },
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5
            ),
        )
        auth_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["ecr:GetAuthorizationToken"],
            resources=["*"],
        )
        project.add_to_role_policy(auth_policy)
        access_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ecr:ListImages",
                "ecr:DescribeImages",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:PutImage",
            ],
            resources=resources,
        )
        project.add_to_role_policy(access_policy)
        task = sfn_tasks.CodeBuildStartBuild(
            self,
            "InstallerCodeBuildStart",
            project=project,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            result_path=f"$.{installer_handlers.EnvKeys.RESULT}",
        )
        self.dependency_group.add(task)
        return task

    def get_ecr_arn_from_private_registry_name(self, registry_name: str) -> str:
        """
        Remove the prefix and tag to get reporsitory name
        """
        repository_name = aws_cdk.Fn.select(
            0,
            aws_cdk.Fn.split(
                ":", aws_cdk.Fn.select(1, aws_cdk.Fn.split("/", registry_name))
            ),
        )
        return aws_cdk.Fn.join(
            "",
            [
                "arn:",
                aws_cdk.Aws.PARTITION,
                ":ecr:",
                aws_cdk.Aws.REGION,
                ":",
                aws_cdk.Aws.ACCOUNT_ID,
                ":repository/",
                repository_name,
            ],
        )

    def get_installer_ecr_images_delete_task(self) -> sfn_tasks.LambdaInvoke:
        installer_ecr_images_delete = lambda_.Function(
            self,
            "InstallerDeleteEcrImagesLambda",
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            timeout=aws_cdk.Duration.minutes(2),
            description="Lambda to delete installer ecr repository images",
            **InfraUtils.get_handler_and_code_for_function(
                installer_handlers.delete_installer_ecr_images
            ),
        )
        installer_ecr_images_delete.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ecr:BatchDeleteImage", "ecr:ListImages"],
                resources=[
                    self.get_ecr_arn_from_private_registry_name(
                        self.installer_registry_name
                    )
                ],
            )
        )

        return sfn_tasks.LambdaInvoke(
            self,
            "InstallerDeleteEcrImages",
            lambda_function=installer_ecr_images_delete,
            payload_response_only=True,
            result_path=f"$.{installer_handlers.EnvKeys.RESULT}",
        )

    def get_cognito_user_pool_unprotect_task(self) -> sfn_tasks.LambdaInvoke:
        unprotect_cognito_user_pool_lambda_task = lambda_.Function(
            self,
            "UnprotectCognitoUserPoolLambda",
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            timeout=aws_cdk.Duration.minutes(2),
            description="Lambda to unprotect Cognito user pool",
            **InfraUtils.get_handler_and_code_for_function(
                installer_handlers.unprotect_cognito_user_pool
            ),
        )
        unprotect_cognito_user_pool_lambda_task.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["cognito-idp:ListUserPools"],
                resources=["*"],
            )
        )
        user_pool_arn_pattern = aws_cdk.Fn.join(
            "",
            [
                "arn:",
                aws_cdk.Aws.PARTITION,
                ":cognito-idp:",
                aws_cdk.Aws.REGION,
                ":",
                aws_cdk.Aws.ACCOUNT_ID,
                ":userpool/*",
            ],
        )
        unprotect_cognito_user_pool_lambda_task.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:DescribeUserPool",
                    "cognito-idp:UpdateUserPool",
                ],
                resources=[user_pool_arn_pattern],
            )
        )
        return sfn_tasks.LambdaInvoke(
            self,
            "UnprotectCognitoUserPool",
            lambda_function=unprotect_cognito_user_pool_lambda_task,
            payload_response_only=True,
            result_path=f"$.{installer_handlers.EnvKeys.RESULT}",
        )

    def get_task(
        self,
        name: str,
        command: list[str],
        task_role: Optional[iam.Role] = None,
    ) -> sfn_tasks.EcsRunTask:
        task = sfn_tasks.EcsRunTask(
            self,
            name,
            cluster=self.cluster,
            task_definition=self.get_task_definition(
                name=name,
                environment=TaskEnvironment(
                    AWS_REGION=aws_cdk.Aws.REGION,
                    AWS_DEFAULT_REGION=aws_cdk.Aws.REGION,
                    IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER="Ec2InstanceMetadata",  # TODO: get proper credentials
                ),
                command=command,
                task_role=task_role,
            ),
            launch_target=sfn_tasks.EcsFargateLaunchTarget(
                platform_version=ecs.FargatePlatformVersion.LATEST
            ),
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            result_path=f"$.{installer_handlers.EnvKeys.RESULT}",
        )

        self.dependency_group.add(task)

        return task
