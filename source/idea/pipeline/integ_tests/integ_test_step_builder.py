#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from aws_cdk import Duration
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_iam as iam
from aws_cdk import pipelines

from idea.pipeline.utils import get_commands_for_scripts


class IntegTestStepBuilder:
    def __init__(
        self,
        invoke_command: str,
        environment_name: str,
        region: str,
        is_legacy: bool = False,
        requires_alb: bool = True,
        compute_type: codebuild.ComputeType = codebuild.ComputeType.SMALL,
    ):
        self._invoke_command = invoke_command
        self._invoke_command_arguments = [f"aws-region={region}"]
        if is_legacy:
            self._invoke_command_arguments.append(f"cluster-name={environment_name}")
        else:
            self._invoke_command_arguments.append(
                f"environment-name={environment_name}"
            )
        self._env = dict(
            CLUSTER_NAME=environment_name,
            AWS_REGION=region,
        )
        self._install_commands = get_commands_for_scripts(
            [
                "source/idea/pipeline/scripts/common/install_commands.sh",
                "source/idea/pipeline/scripts/integ_tests/install_commands.sh",
                "source/idea/pipeline/scripts/chrome/install_commands.sh",
            ]
        )
        self._role_policy_statements = [
            # Default permissions to update security groups so that the integ test can get HTTP access to the RES environment
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSecurityGroupRules",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:RevokeSecurityGroupIngress",
                    ],
                    "Resource": "*",
                }
            ),
        ]
        self._requires_alb = requires_alb
        self._compute_type = compute_type

    def test_specific_invoke_command_argument(
        self, *arguments: str
    ) -> IntegTestStepBuilder:
        for argument in arguments:
            self._invoke_command_arguments.append(argument)

        return self

    def test_specific_install_command(self, *commands: str) -> IntegTestStepBuilder:
        for command in commands:
            self._install_commands.append(command)

        return self

    def test_specific_env(self, **env_variables: str) -> IntegTestStepBuilder:
        self._env.update(env_variables)

        return self

    def test_specific_role_policy_statement(
        self, *statements: iam.PolicyStatement
    ) -> IntegTestStepBuilder:
        for statement in statements:
            self._role_policy_statements.append(statement)

        return self

    def build(self) -> pipelines.CodeBuildStep:
        # Setting up commands necessary to run integ tests
        commands = (
            get_commands_for_scripts(
                ["source/idea/pipeline/scripts/integ_tests/setup_commands.sh"]
            )
            if self._requires_alb
            else []
        )
        invoke_command = f"invoke {self._invoke_command}"
        for invoke_command_argument in self._invoke_command_arguments:
            invoke_command = invoke_command + f" -p {invoke_command_argument}"
        commands.append(invoke_command)

        if self._requires_alb:
            commands += get_commands_for_scripts(
                ["source/idea/pipeline/scripts/integ_tests/teardown_commands.sh"]
            )

        return pipelines.CodeBuildStep(
            self._invoke_command,
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=self._compute_type,
                privileged=True,
            ),
            env=self._env,
            install_commands=self._install_commands,
            commands=commands,
            role_policy_statements=self._role_policy_statements,
            timeout=Duration.hours(4),
        )
