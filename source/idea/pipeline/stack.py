#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import pathlib
import typing

from aws_cdk import CfnOutput, Duration, IStackSynthesizer, RemovalPolicy, Stack, Stage
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import pipelines
from constructs import Construct

from idea.constants import (
    ARTIFACTS_BUCKET_PREFIX_NAME,
    DEFAULT_ECR_REPOSITORY_NAME,
    INSTALL_STACK_NAME,
)
from idea.infrastructure.install.parameters.parameters import Parameters
from idea.infrastructure.install.stack import InstallStack

UNITTESTS = [
    "tests.administrator",
    "tests.cluster-manager",
    "tests.virtual-desktop-controller",
    "tests.sdk",
    "tests.pipeline",
    "tests.infrastructure",
]
COVERAGEREPORTS = ["coverage"]
INTEG_TESTS = ["integ-tests.cluster-manager"]
SCANS = ["npm_audit", "bandit"]
PUBLICECRRepository = "public.ecr.aws/l6g7n3r5/research-engineering-studio"


class PipelineStack(Stack):
    # Set Default Values if Not in ENV
    _repository_name: str = "DigitalEngineeringPlatform"
    _branch_name: str = "develop"
    _deploy: bool = False
    _destroy: bool = False
    _publish_templates: bool = False

    @property
    def repository_name(self) -> str:
        return self._repository_name

    @property
    def branch_name(self) -> str:
        return self._branch_name

    @property
    def pipeline(self) -> pipelines.CodePipeline:
        return self._pipeline

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        synthesizer: typing.Optional[IStackSynthesizer] = None,
    ) -> None:
        super().__init__(scope, construct_id, synthesizer=synthesizer)

        context_repository_name = self.node.try_get_context("repository_name")
        if context_repository_name:
            self._repository_name = context_repository_name
        context_branch_name = self.node.try_get_context("branch_name")
        if context_branch_name:
            self._branch_name = context_branch_name
        context_deploy = self.node.try_get_context("deploy")
        if context_deploy:
            self._deploy = context_deploy.lower() == "true"
        context_destroy = self.node.try_get_context("destroy")
        if context_destroy:
            self._destroy = context_destroy.lower() == "true"
        context_publish_templates = self.node.try_get_context("publish_templates")
        if context_publish_templates:
            self._publish_templates = context_publish_templates.lower() == "true"
        self.params = Parameters.from_context(self)
        if self.params.cluster_name is None:
            self.params.cluster_name = "res-deploy"

        ecr_public_repository_name = self.node.try_get_context(
            "ecr_public_repository_name"
        )
        ecr_public_repository_name = (
            ecr_public_repository_name if ecr_public_repository_name else ""
        )

        ecr_actions = [
            "ecr:BatchCheckLayerAvailability",
            "ecr:CompleteLayerUpload",
            "ecr:InitiateLayerUpload",
            "ecr:PutImage",
            "ecr:UploadLayerPart",
            "ecr:DescribeRepositories",
            "ecr:BatchGetImage",
            "ecr:GetDownloadUrlForLayer",
        ]
        codebuild_ecr_access_actions = [
            "ecr:GetAuthorizationToken",
        ]
        # Create the ECR repository
        ecr_repository = ecr.Repository(
            self,
            DEFAULT_ECR_REPOSITORY_NAME,
            removal_policy=RemovalPolicy.DESTROY,
        )
        ecr_repository_name = ecr_repository.repository_name
        ecr_repository_arn = ecr_repository.repository_arn

        codebuild_ecr_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=codebuild_ecr_access_actions,
            resources=["*"],
        )

        codebuild_ecr_push = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=ecr_actions,
            resources=[ecr_repository_arn],
        )

        # Create a CodeBuild project
        self._pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            synth=self.get_synth_step(ecr_repository_name, ecr_public_repository_name),
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                    compute_type=codebuild.ComputeType.LARGE,
                    privileged=True,
                ),
                role_policy=[
                    codebuild_ecr_access,
                    codebuild_ecr_push,
                ],
            ),
        )

        audit_wave = self._pipeline.add_wave("SecurityAudit")
        audit_wave.add_post(*self.get_steps_from_tox(SCANS))
        unittest_wave = self._pipeline.add_wave("UnitTests")
        unittest_wave.add_post(*self.get_steps_from_tox(UNITTESTS))

        coverage_wave = self._pipeline.add_wave("Coverage")
        coverage_wave.add_post(*self.get_steps_from_tox(COVERAGEREPORTS))

        if self._deploy:
            deploy_stage = DeployStage(self, "Deploy", parameters=self.params)
            integ_test_steps = self.get_integ_test_step(INTEG_TESTS)

            if self._destroy:
                destroy_step = self.get_destroy_step()
                for integ_test_step in integ_test_steps:
                    destroy_step.add_step_dependency(integ_test_step)
                self._pipeline.add_stage(
                    deploy_stage,
                    post=integ_test_steps + [destroy_step],
                )
            else:
                self._pipeline.add_stage(deploy_stage, post=integ_test_steps)
        if self._publish_templates:
            publish_steps = self.get_publish_steps(ecr_public_repository_name)
            publish_wave = self._pipeline.add_wave("Publish")
            publish_wave.add_post(publish_steps)
        self._pipeline.build_pipeline()
        if self._publish_templates and publish_steps and publish_steps.project.role:
            CfnOutput(
                self,
                "PublishCodeBuildRole",
                value=publish_steps.project.role.role_name,
            )

    def get_connection(self) -> pipelines.CodePipelineSource:
        return pipelines.CodePipelineSource.code_commit(
            repository=codecommit.Repository.from_repository_name(
                scope=self,
                id="CodeCommitSource",
                repository_name=self._repository_name,
            ),
            branch=self._branch_name,
        )

    def get_synth_step(
        self, ecr_repository_name: str, ecr_public_repository_name: str
    ) -> pipelines.CodeBuildStep:
        return pipelines.CodeBuildStep(
            "Synth",
            input=self.get_connection(),
            env=dict(
                REPOSITORY_NAME=self._repository_name,
                BRANCH=self._branch_name,
                DEPLOY="true" if self._deploy else "false",
                DESTROY="true" if self._destroy else "false",
                ECR_REPOSITORY=ecr_repository_name,
                ECR_PUBLIC_REPOSITORY_NAME=ecr_public_repository_name,
                PUBLISH_TEMPLATES="true" if self._publish_templates else "false",
                **self.params.to_context(),
            ),
            install_commands=self.get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/common/install_commands.sh",
                    "source/idea/pipeline/scripts/synth/install_commands.sh",
                ]
            ),
            commands=self.get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/synth/commands.sh",
                ]
            ),
            partial_build_spec=self.get_reports_partial_build_spec("pytest-report.xml"),
        )

    def get_integ_test_step(
        self, integ_test_envs: list[str]
    ) -> list[pipelines.CodeBuildStep]:
        steps: list[pipelines.CodeBuildStep] = []
        clusteradmin_username = "clusteradmin"  # bootstrap user
        clusteradmin_password = "RESPassword1."  # fixed password for running tests

        for _env in integ_test_envs:
            # Setting up commands necessary to set clusteradmin password and then run integ tests
            commands = self.get_commands_for_scripts(
                ["source/idea/pipeline/scripts/integ_tests/setup_commands.sh"]
            )
            # The following command uses tox to invoke the integ-test; _env is in format like integ-tests.cluseter-manager
            commands += [
                f"tox -e {_env} -- -p cluster-name={self.params.cluster_name} -p aws-region={self.region} "
                f"-p admin-username={clusteradmin_username} "
                f"-p admin-password={clusteradmin_password}",
            ]
            commands += self.get_commands_for_scripts(
                ["source/idea/pipeline/scripts/integ_tests/teardown_commands.sh"]
            )
            _step = pipelines.CodeBuildStep(
                _env,
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                    compute_type=codebuild.ComputeType.SMALL,
                    privileged=True,
                ),
                env=dict(
                    CLUSTER_NAME=self.params.cluster_name,
                    AWS_REGION=self.region,
                    CLUSTERADMIN_USERNAME=clusteradmin_username,
                    CLUSTERADMIN_PASSWORD=clusteradmin_password,
                ),
                install_commands=self.get_commands_for_scripts(
                    [
                        "source/idea/pipeline/scripts/common/install_commands.sh",
                        "source/idea/pipeline/scripts/integ_tests/install_commands.sh",
                        "source/idea/pipeline/scripts/tox/install_commands.sh",
                    ]
                ),
                commands=commands,
                role_policy_statements=[
                    iam.PolicyStatement.from_json(
                        {
                            "Effect": "Allow",
                            "Action": [
                                "cognito-idp:ListUserPools",
                                "cognito-idp:AdminSetUserPassword",
                            ],
                            "Resource": "*",
                        }
                    ),
                    iam.PolicyStatement.from_json(
                        {
                            "Effect": "Allow",
                            "Action": [
                                "dynamodb:DescribeTable",
                                "dynamodb:Scan",
                                "dynamodb:GetItem",
                            ],
                            "Resource": [
                                f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.cluster-settings",
                                f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.modules",
                            ],
                        }
                    ),
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
                ],
                timeout=Duration.hours(4),
            )
            steps.append(_step)
        return steps

    @staticmethod
    def get_steps_from_tox(tox_env: list[str]) -> list[pipelines.CodeBuildStep]:
        steps: list[pipelines.CodeBuildStep] = []
        for _env in tox_env:
            _step = pipelines.CodeBuildStep(
                _env,
                install_commands=PipelineStack.get_commands_for_scripts(
                    [
                        "source/idea/pipeline/scripts/common/install_commands.sh",
                        "source/idea/pipeline/scripts/tox/install_commands.sh",
                    ]
                ),
                commands=[
                    f"tox -e {_env}",
                ],
            )
            steps.append(_step)
        return steps

    def get_destroy_step(self) -> pipelines.CodeBuildStep:
        codebuild_cloudformation_read_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudformation:ListStacks",
                "cloudformation:DescribeStacks",
            ],
            resources=[
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/Deploy-{INSTALL_STACK_NAME}/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-bootstrap/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-cluster/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-metrics/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-directoryservice/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-identity-provider/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-analytics/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-shared-storage/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-cluster-manager/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-vdc/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-bastion-host/*",
            ],
        )
        codebuild_cloudformation_delete_stack_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudformation:DeleteStack",
            ],
            resources=[
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/Deploy-{INSTALL_STACK_NAME}/*"
            ],
        )
        return pipelines.CodeBuildStep(
            "Destroy",
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                compute_type=codebuild.ComputeType.SMALL,
                privileged=True,
            ),
            env=dict(
                CLUSTER_NAME=self.params.cluster_name,
                AWS_REGION=self.region,
                INSTALL_STACK_NAME=INSTALL_STACK_NAME,
            ),
            commands=self.get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/destroy/commands.sh",
                ]
            ),
            role_policy_statements=[
                codebuild_cloudformation_read_policy,
                codebuild_cloudformation_delete_stack_policy,
            ],
            timeout=Duration.hours(2),
        )

    def get_publish_steps(
        self, ecr_public_repository_name: str
    ) -> pipelines.CodeBuildStep:
        ecr_public_repository_uri = (
            "" if ecr_public_repository_name else PUBLICECRRepository
        )
        ecr_public_repository_actions = [
            "ecr-public:BatchCheckLayerAvailability",
            "ecr-public:CompleteLayerUpload",
            "ecr-public:InitiateLayerUpload",
            "ecr-public:PutImage",
            "ecr-public:UploadLayerPart",
            "ecr-public:DescribeRepositories",
        ]
        ecr_public_access_actions = [
            "ecr-public:GetAuthorizationToken",
            "sts:GetServiceBearerToken",
        ]
        ecr_repository_arn = f"arn:{self.partition}:ecr-public::{self.account}:repository/{ecr_public_repository_name}"

        codebuild_ecr_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=ecr_public_access_actions,
            resources=["*"],
        )
        codebuild_ecr_repository = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=ecr_public_repository_actions,
            resources=[ecr_repository_arn],
        )
        codebuild_describe_regions = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["ec2:DescribeRegions"],
            resources=["*"],
        )
        return pipelines.CodeBuildStep(
            "Publish templates and docker image",
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                compute_type=codebuild.ComputeType.SMALL,
                privileged=True,
            ),
            env=dict(
                ARTIFACTS_BUCKET_PREFIX_NAME=ARTIFACTS_BUCKET_PREFIX_NAME,
                INSTALL_STACK_NAME=INSTALL_STACK_NAME,
                ECR_REPOSITORY=ecr_public_repository_name,
                PUBLISH_TEMPLATES="true" if self._publish_templates else "false",
                ECR_REPOSITORY_URI_PARAMETER=ecr_public_repository_uri,
            ),
            install_commands=self.get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/common/install_commands.sh",
                    "source/idea/pipeline/scripts/publish/install_commands.sh",
                ]
            ),
            commands=self.get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/publish/commands.sh",
                ]
            ),
            role_policy_statements=[
                codebuild_ecr_access,
                codebuild_ecr_repository,
                codebuild_describe_regions,
            ],
        )

    @staticmethod
    def get_commands_for_scripts(paths: list[str]) -> list[str]:
        commands = []
        root = pathlib.Path("source").parent
        scripts = root / "source/idea/pipeline/scripts"
        for raw_path in paths:
            path = pathlib.Path(raw_path)
            if not path.exists():
                raise ValueError(f"script path doesn't exist: {path}")
            if not path.is_relative_to(scripts):
                raise ValueError(f"script path isn't in {scripts}: {path}")
            relative = path.relative_to(root)
            commands.append(f"chmod +x {relative}")
            commands.append(str(relative))
        return commands

    def get_reports_partial_build_spec(self, filename: str) -> codebuild.BuildSpec:
        return codebuild.BuildSpec.from_object(
            {
                "reports": {
                    "pytest_reports": {
                        "files": [filename],
                        "file-format": "JUNITXML",
                    }
                }
            }
        )


class DeployStage(Stage):
    def __init__(self, scope: Construct, construct_id: str, parameters: Parameters):
        super().__init__(scope, construct_id)
        registry_name = self.node.try_get_context("registry_name")
        self.install_stack = InstallStack(
            self, INSTALL_STACK_NAME, parameters=parameters, registry_name=registry_name
        )
