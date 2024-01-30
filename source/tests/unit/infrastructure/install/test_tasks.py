#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import sys
from typing import Any, Callable

import click
import pytest
from aws_cdk.assertions import Match, Template

from idea.infrastructure.install.stack import InstallStack
from tests.unit.infrastructure.install import util


@pytest.fixture
def expected_environment() -> list[Any]:
    return [
        {
            "Name": "AWS_REGION",
            "Value": {"Ref": "AWS::Region"},
        },
        {
            "Name": "AWS_DEFAULT_REGION",
            "Value": {"Ref": "AWS::Region"},
        },
        {
            "Name": "IDEA_ADMIN_AWS_CREDENTIAL_PROVIDER",
            "Value": "Ec2InstanceMetadata",
        },
    ]


def test_ecs_cluster_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "Tasks", "Cluster"],
        cfn_type="AWS::ECS::Cluster",
        props={},
    )


def test_create_task_creation(
    stack: InstallStack,
    template: Template,
    registry_name: str,
    expected_environment: list[Any],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "Tasks", "CreateTaskDef"],
        cfn_type="AWS::ECS::TaskDefinition",
        props={
            "Properties": {
                "ContainerDefinitions": [
                    {
                        "Command": Match.array_with(["/bin/sh", "-c"]),
                        "Environment": expected_environment,
                        "Image": registry_name,
                        "LogConfiguration": {
                            "Options": {"awslogs-stream-prefix": "CreateLogStream"}
                        },
                    }
                ],
                "TaskRoleArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            stack, ["Installer", "Tasks", "Permissions", "PipelineRole"]
                        ),
                        "Arn",
                    ]
                },
            }
        },
    )


def test_update_task_creation(
    stack: InstallStack,
    template: Template,
    registry_name: str,
    expected_environment: list[Any],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "Tasks", "UpdateTaskDef"],
        cfn_type="AWS::ECS::TaskDefinition",
        props={
            "Properties": {
                "ContainerDefinitions": [
                    {
                        "Command": Match.array_with(["/bin/sh", "-c"]),
                        "Environment": expected_environment,
                        "Image": registry_name,
                        "LogConfiguration": {
                            "Options": {"awslogs-stream-prefix": "UpdateLogStream"}
                        },
                    }
                ],
                "TaskRoleArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            stack, ["Installer", "Tasks", "Permissions", "PipelineRole"]
                        ),
                        "Arn",
                    ]
                },
            }
        },
    )


def test_delete_task_creation(
    stack: InstallStack,
    template: Template,
    registry_name: str,
    expected_environment: list[Any],
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "Tasks", "DeleteTaskDef"],
        cfn_type="AWS::ECS::TaskDefinition",
        props={
            "Properties": {
                "ContainerDefinitions": [
                    {
                        "Command": Match.array_with(["/bin/sh", "-c"]),
                        "Environment": expected_environment,
                        "Image": registry_name,
                        "LogConfiguration": {
                            "Options": {"awslogs-stream-prefix": "DeleteLogStream"}
                        },
                    }
                ],
                "TaskRoleArn": {
                    "Fn::GetAtt": [
                        util.get_logical_id(
                            stack, ["Installer", "Tasks", "Permissions", "PipelineRole"]
                        ),
                        "Arn",
                    ]
                },
            }
        },
    )


@pytest.mark.parametrize(
    "with_code", [True, False], ids=["with exit code", "without exit code"]
)
def test_define_main_system_exit_handling_behavior(with_code: bool) -> None:
    """
    The res-admin app has a wrapper with logic for detecting success based on
    SystemExit error codes. It is not clear of the intended behavior for when
    `raise SystemExit` is called with no parameters. This test is to establish
    the existing behavior for later reference if it is determined to be incorrect.
    """

    custom_error_code = 2

    def representative_main_wrapper(thing_to_execute: Callable[[], None]) -> None:
        success = True
        exit_code = 0

        try:
            thing_to_execute()
        except SystemExit as e:
            success = e.code == 0
            exit_code = e.code

        if not success:
            if exit_code == 0:
                exit_code = 1
            sys.exit(exit_code)

    @click.command()
    def example_command_that_errors() -> None:
        if with_code:
            raise SystemExit(custom_error_code)
        raise SystemExit

    def call_command() -> None:
        ctx = example_command_that_errors.make_context(
            "example-command-that-errors", []
        )
        with ctx:
            example_command_that_errors.invoke(ctx)

    with pytest.raises(SystemExit) as e:
        representative_main_wrapper(call_command)

    assert e.type == SystemExit
    if with_code:
        assert e.value.code == custom_error_code
    else:
        assert e.value.code is None
