#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Optional, TypedDict, Union

import aws_cdk
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks
from constructs import Construct, DependencyGroup

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import handlers
from idea.infrastructure.install.commands import create
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.permissions import Permissions


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
        params: Union[RESParameters, BIParameters],
        dependency_group: DependencyGroup,
    ):
        super().__init__(scope, id)

        self.registry_name = registry_name
        self.cluster = ecs.Cluster(self, "Cluster")
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
        task_definition = ecs.FargateTaskDefinition(
            self,
            f"{name}TaskDef",
            task_role=task_role,
            execution_role=task_role,
            memory_limit_mib=4096,
            cpu=2048,
        )
        commands = "\n".join(command)
        task_definition.add_container(
            f"{name}Container",
            image=ecs.ContainerImage.from_registry(self.registry_name),
            environment=dict(**environment),
            command=["/bin/sh", "-c", f"/bin/sh -ex <<'EOC'\n{commands}\nEOC\n"],
            logging=ecs.LogDriver.aws_logs(stream_prefix=f"{name}LogStream"),
        )

        self.dependency_group.add(task_definition)

        return task_definition

    def get_create_task(self) -> sfn_tasks.EcsRunTask:
        return self.get_task(
            name="Create",
            command=create.Create(params=self.params).get_commands(),
            task_role=self.permissions.pipeline_role,
        )

    def get_update_task(self) -> sfn_tasks.EcsRunTask:
        return self.get_task(
            name="Update",
            command=[
                "res-admin --version",
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
            result_path=f"$.{handlers.EnvKeys.RESULT}",
        )

        self.dependency_group.add(task)

        return task
