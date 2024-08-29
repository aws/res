#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import pathlib
import typing
from typing import Union

import aws_cdk
from aws_cdk import (
    CfnOutput,
    Duration,
    Fn,
    IStackSynthesizer,
    RemovalPolicy,
    Stack,
    Stage,
)
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import pipelines
from constructs import Construct

from idea.batteries_included.parameters.parameters import BIParameters
from idea.batteries_included.stack import BiStack
from idea.constants import (
    ARTIFACTS_BUCKET_PREFIX_NAME,
    BATTERIES_INCLUDED_STACK_NAME,
    DEFAULT_ECR_REPOSITORY_NAME,
    INSTALL_STACK_NAME,
)
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.stack import InstallStack
from idea.pipeline.integ_tests.integ_test_step_builder import IntegTestStepBuilder
from idea.pipeline.utils import get_commands_for_scripts

UNITTESTS = [
    "tests.administrator",
    "tests.cluster-manager",
    "tests.virtual-desktop-controller",
    "tests.sdk",
    "tests.pipeline",
    "tests.infrastructure",
    "tests.lambda-functions",
]
COVERAGEREPORTS = ["coverage"]
COMPONENT_INTEG_TESTS = ["integ-tests.cluster-manager"]
SCANS = ["npm_audit", "bandit", "viperlight_scan"]
PUBLICECRRepository = "public.ecr.aws/l6g7n3r5/research-engineering-studio"
ONBOARDED_REGIONS = "ap-northeast-1,ap-northeast-2,ap-south-1,ap-southeast-1,ap-southeast-2,ca-central-1,eu-central-1,eu-north-1,eu-south-1,eu-west-1,eu-west-2,eu-west-3,us-east-1,us-east-2,us-west-1,us-west-2"
ONBOARDED_REGIONS_GOVCLOUD = "us-gov-west-1"


class PipelineStack(Stack):
    # Set Default Values if Not in ENV
    _repository_name: str = "DigitalEngineeringPlatform"
    _branch_name: str = "develop"
    _deploy: bool = False
    _integ_tests: bool = False
    _bi: bool = False
    _use_bi_parameters_from_ssm: bool = False
    _destroy: bool = False
    _destroy_bi: bool = False
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
        context_bi = self.node.try_get_context("batteries_included")
        if context_bi:
            self._bi = context_bi.lower() == "true"
        context_use_bi_parameters_from_ssm = self.node.try_get_context(
            "use_bi_parameters_from_ssm"
        )
        context_use_bi_parameters_from_ssm = (
            context_use_bi_parameters_from_ssm
            if context_use_bi_parameters_from_ssm
            else ""
        )
        self._use_bi_parameters_from_ssm = (
            context_use_bi_parameters_from_ssm.lower() == "true"
        )
        context_portal_domain_name = self.node.try_get_context("portal_domain_name")
        self._portal_domain_name = (
            context_portal_domain_name if context_portal_domain_name else ""
        )
        context_destroy = self.node.try_get_context("destroy")
        context_destroy_bi = self.node.try_get_context("destroy_batteries_included")
        context_integ_tests = self.node.try_get_context("integration_tests")
        self._integ_tests = (
            context_integ_tests.lower() == "true" if context_integ_tests else "true"
        )
        if context_destroy:
            self._destroy = context_destroy.lower() == "true"
        if context_destroy_bi:
            self._destroy_bi = context_destroy_bi.lower() == "true"
        context_publish_templates = self.node.try_get_context("publish_templates")
        if context_publish_templates:
            self._publish_templates = context_publish_templates.lower() == "true"
        self.params: Union[RESParameters, BIParameters]
        if self._bi or self._use_bi_parameters_from_ssm:
            self.params = BIParameters.from_context(self)
        else:
            self.params = RESParameters.from_context(self)
        if self.params.cluster_name is None:
            self.params.cluster_name = "res-deploy"

        bi_stack_template_url = self.node.try_get_context("BIStackTemplateURL")
        bi_stack_template_url = bi_stack_template_url if bi_stack_template_url else ""

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
        ecr_repository.grant_pull(
            iam.Role(
                self,
                "PrivateEcrPull",
                assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            )
        )
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
            synth=self.get_synth_step(
                ecr_repository_name,
                ecr_public_repository_name,
                bi_stack_template_url,
                context_use_bi_parameters_from_ssm,
            ),
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
            deploy_stage = DeployStage(
                self,
                "Deploy",
                use_bi_parameters_from_ssm=self._use_bi_parameters_from_ssm,
                parameters=self.params,
            )

            post_steps = []
            create_web_and_vdi_record_step = self.get_create_web_and_vdi_record_step()
            if self._portal_domain_name != "":
                post_steps.append(create_web_and_vdi_record_step)

            if self._integ_tests:
                component_integ_test_steps = self.get_component_integ_test_steps(
                    COMPONENT_INTEG_TESTS
                )
                smoke_test_step = self.get_smoke_test_step()
                # Smoke test cannot run with other integ tests in parallel, as it requires to relaunch the web servers
                # and the servers will become temporarily unresponsive to other integ tests.
                # And all integ tests should run after create_web_and_vdi_record_step.
                for component_integ_test_step in component_integ_test_steps:
                    smoke_test_step.add_step_dependency(component_integ_test_step)
                    if self._portal_domain_name != "":
                        component_integ_test_step.add_step_dependency(
                            create_web_and_vdi_record_step
                        )

                post_steps += component_integ_test_steps
                post_steps.append(smoke_test_step)

            if self._destroy:
                destroy_step = self.get_destroy_step()
                # Destroy step should only execute after all the other steps complete
                for step in post_steps:
                    destroy_step.add_step_dependency(step)
                post_steps.append(destroy_step)

            self._pipeline.add_stage(deploy_stage, post=post_steps)

        if self._publish_templates:
            is_classic_region = aws_cdk.CfnCondition(
                self,
                "IsClassicRegion",
                expression=Fn.condition_equals(self.partition, "aws"),
            )
            self.onboarded_regions = Fn.condition_if(
                is_classic_region.logical_id,
                ONBOARDED_REGIONS,
                ONBOARDED_REGIONS_GOVCLOUD,
            ).to_string()
            publish_wave = self._pipeline.add_wave("Publish")
            publish_steps = self.get_publish_steps(ecr_public_repository_name)
            publish_wave.add_post(publish_steps)

            # After the artifacts gets published into each region's "RELEASE_VERSION" prefixed bucket, we will release
            # the change to "/latest" bucket after a manual approval.
            manual_approval_step = pipelines.ManualApprovalStep(
                "ManualApprovalForLatestBucketRefresh"
            )
            manual_approval_step.add_step_dependency(publish_steps)
            publish_wave.add_post(manual_approval_step)

            artifacts_release_steps = self.get_latest_bucket_refresh_steps()
            artifacts_release_steps.add_step_dependency(manual_approval_step)
            publish_wave.add_post(artifacts_release_steps)

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
        self,
        ecr_repository_name: str,
        ecr_public_repository_name: str,
        bi_stack_template_url: str,
        use_bi_parameters_from_ssm: str,
    ) -> pipelines.CodeBuildStep:
        return pipelines.CodeBuildStep(
            "Synth",
            input=self.get_connection(),
            env=dict(
                REPOSITORY_NAME=self._repository_name,
                BRANCH=self._branch_name,
                DEPLOY="true" if self._deploy else "false",
                INTEGRATION_TESTS="true" if self._integ_tests else "false",
                DESTROY="true" if self._destroy else "false",
                DESTROY_BATTERIES_INCLUDED="true" if self._destroy_bi else "false",
                BATTERIES_INCLUDED="true" if self._bi else "false",
                BIStackTemplateURL=bi_stack_template_url,
                ECR_REPOSITORY=ecr_repository_name,
                ECR_PUBLIC_REPOSITORY_NAME=ecr_public_repository_name,
                USE_BI_PARAMETERS_FROM_SSM=use_bi_parameters_from_ssm,
                PUBLISH_TEMPLATES="true" if self._publish_templates else "false",
                SKIP_ENV_UPDATE="true",
                PORTAL_DOMAIN_NAME=self._portal_domain_name,
                **self.params.to_context(),
            ),
            install_commands=get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/common/install_commands.sh",
                    "source/idea/pipeline/scripts/synth/install_commands.sh",
                ]
            ),
            commands=get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/synth/commands.sh",
                ]
            ),
            partial_build_spec=self.get_reports_partial_build_spec("pytest-report.xml"),
        )

    def get_web_and_vdi_record_policy(
        self,
    ) -> tuple[iam.PolicyStatement, iam.PolicyStatement]:
        codebuild_read_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "route53:ListHostedZones",
                "elasticloadbalancing:DescribeLoadBalancers",
            ],
            resources=["*"],
        )
        codebuild_route53_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["route53:ChangeResourceRecordSets", "route53:GetChange"],
            resources=["arn:aws:route53:::hostedzone/*", "arn:aws:route53:::change/*"],
        )
        return codebuild_read_policy, codebuild_route53_policy

    def get_create_web_and_vdi_record_step(self) -> pipelines.CodeBuildStep:
        codebuild_read_policy, codebuild_route53_policy = (
            self.get_web_and_vdi_record_policy()
        )
        return pipelines.CodeBuildStep(
            "CreateWebAndVdiDNSRecords",
            env=dict(
                PORTAL_DOMAIN=self._portal_domain_name,
                WEB_PORTAL_DOMAIN=self.params.custom_domain_name_for_web_ui,
                VDI_PORTAL_DOMAIN=self.params.custom_domain_name_for_vdi,
                CLUSTER_NAME=self.params.cluster_name,
                WEB_AND_VDI_RECORD_ACTION="UPSERT",
            ),
            commands=get_commands_for_scripts(
                ["source/idea/pipeline/scripts/common/web_and_vdi_record_commands.sh"]
            ),
            role_policy_statements=[codebuild_read_policy, codebuild_route53_policy],
        )

    def get_component_integ_test_steps(
        self, integ_test_envs: list[str]
    ) -> list[pipelines.CodeBuildStep]:
        steps: list[pipelines.CodeBuildStep] = []
        clusteradmin_username = "clusteradmin"  # bootstrap user
        clusteradmin_password = "RESPassword1."  # fixed password for running tests

        for _env in integ_test_envs:
            _step = (
                IntegTestStepBuilder(_env, self.params.cluster_name, self.region, True)
                .test_specific_tox_command_argument(
                    f"admin-username={clusteradmin_username}",
                    f"admin-password={clusteradmin_password}",
                )
                .test_specific_env(
                    CLUSTERADMIN_USERNAME=clusteradmin_username,
                    CLUSTERADMIN_PASSWORD=clusteradmin_password,
                )
                .test_specific_role_policy_statement(
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
                )
                .build()
            )
            steps.append(_step)
        return steps

    def get_smoke_test_step(self) -> pipelines.CodeBuildStep:
        step = (
            IntegTestStepBuilder(
                "integ-tests.smoke", self.params.cluster_name, self.region
            )
            .test_specific_install_command(
                *get_commands_for_scripts(
                    ["source/idea/pipeline/scripts/chrome/install_commands.sh"]
                )
            )
            .test_specific_role_policy_statement(
                iam.PolicyStatement.from_json(
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ssm:SendCommand",
                        ],
                        "Resource": [
                            f"arn:{self.partition}:ssm:{self.region}:*:document/*",
                        ],
                    }
                ),
                iam.PolicyStatement.from_json(
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ssm:SendCommand",
                        ],
                        "Resource": [
                            f"arn:{self.partition}:ec2:{self.region}:{self.account}:instance/*"
                        ],
                        "Condition": {
                            "StringLike": {
                                "ssm:resourceTag/res:EnvironmentName": [
                                    self.params.cluster_name
                                ]
                            }
                        },
                    }
                ),
                iam.PolicyStatement.from_json(
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ssm:GetCommandInvocation",
                        ],
                        "Resource": "*",
                    }
                ),
                iam.PolicyStatement.from_json(
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                        ],
                        # TODO: Specify the bucket to which SSM writes command outputs
                        "Resource": "*",
                    }
                ),
                iam.PolicyStatement.from_json(
                    {
                        "Effect": "Allow",
                        "Action": [
                            "elasticloadbalancing:DescribeLoadBalancers",
                        ],
                        "Resource": "*",
                    }
                ),
                iam.PolicyStatement.from_json(
                    {
                        "Effect": "Allow",
                        "Action": [
                            "elasticloadbalancing:ModifyLoadBalancerAttributes",
                        ],
                        "Resource": f"arn:{self.partition}:elasticloadbalancing:{self.region}:{self.account}:loadbalancer/app/{self.params.cluster_name}-external-alb/*",
                    }
                ),
                iam.PolicyStatement.from_json(
                    {
                        "Effect": "Allow",
                        "Action": [
                            "autoscaling:DescribeAutoScalingGroups",
                        ],
                        "Resource": "*",
                    }
                ),
            )
            .build()
        )

        return step

    @staticmethod
    def get_steps_from_tox(tox_env: list[str]) -> list[pipelines.CodeBuildStep]:
        steps: list[pipelines.CodeBuildStep] = []
        for _env in tox_env:
            _step = pipelines.CodeBuildStep(
                _env,
                install_commands=get_commands_for_scripts(
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
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-shared-storage/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-cluster-manager/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-vdc/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/{self.params.cluster_name}-bastion-host/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/Deploy-{BATTERIES_INCLUDED_STACK_NAME}*",
            ],
        )
        codebuild_cloudformation_delete_stack_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudformation:DeleteStack",
            ],
            resources=[
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/Deploy-{INSTALL_STACK_NAME}/*",
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/Deploy-{BATTERIES_INCLUDED_STACK_NAME}*",
            ],
        )
        codebuild_read_ssm_parameter_vpc_id_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ssm:GetParameter",
            ],
            resources=[
                f"arn:{self.partition}:ssm:{self.region}:{self.account}:parameter{self.params.vpc_id}"
            ],
        )
        codebuild_read_file_systems_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "elasticfilesystem:DescribeFileSystems",
                "elasticfilesystem:DescribeMountTargets",
                "fsx:DescribeFileSystems",
                "fsx:DescribeStorageVirtualMachines",
                "fsx:DescribeVolumes",
            ],
            resources=["*"],
        )
        codebuild_efs_delete_file_systems_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "elasticfilesystem:DeleteMountTarget",
                "elasticfilesystem:DeleteFileSystem",
            ],
            resources=["*"],
            conditions={
                "StringEquals": {
                    "aws:ResourceTag/res:EnvironmentName": [self.params.cluster_name],
                },
            },
        )
        codebuild_efs_filesystem_ec2_delete_eni_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ec2:DeleteNetworkInterface",
            ],
            resources=["*"],
        )
        codebuild_fsx_delete_file_systems_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "fsx:DeleteFileSystem",
            ],
            resources=["*"],
            conditions={
                "StringEquals": {
                    "aws:ResourceTag/res:EnvironmentName": [self.params.cluster_name],
                },
            },
        )
        codebuild_fsx_delete_svms_volumes_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "fsx:DeleteVolume",
                "fsx:DeleteStorageVirtualMachine",
                "fsx:CreateBackup",
                "fsx:TagResource",
            ],
            resources=["*"],
        )
        codebuild_shared_storage_security_group_read_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ec2:DescribeSecurityGroups",
            ],
            resources=["*"],
        )
        codebuild_shared_storage_security_group_delete_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ec2:DeleteSecurityGroup",
            ],
            resources=["*"],
            conditions={
                "StringEquals": {
                    "aws:ResourceTag/Name": [
                        f"{self.params.cluster_name}-shared-storage-security-group"
                    ],
                },
            },
        )
        (
            codebuild_destroy_records_read_policy,
            codebuild_destroy_records_route53_policy,
        ) = self.get_web_and_vdi_record_policy()

        commands = ["source/idea/pipeline/scripts/destroy/commands.sh"]
        if self._portal_domain_name != "":
            commands.insert(
                0, "source/idea/pipeline/scripts/common/web_and_vdi_record_commands.sh"
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
                BATTERIES_INCLUDED="true" if self._bi else "false",
                USE_BI_PARAMETERS_FROM_SSM=(
                    "true" if self._use_bi_parameters_from_ssm else "false"
                ),
                DESTROY_BATTERIES_INCLUDED="true" if self._destroy_bi else "false",
                VPC_ID=self.params.vpc_id,
                INSTALL_STACK_NAME=INSTALL_STACK_NAME,
                BATTERIES_INCLUDED_STACK_NAME=f"Deploy-{BATTERIES_INCLUDED_STACK_NAME}",
                PORTAL_DOMAIN=self._portal_domain_name,
                WEB_PORTAL_DOMAIN=self.params.custom_domain_name_for_web_ui,
                VDI_PORTAL_DOMAIN=self.params.custom_domain_name_for_vdi,
                WEB_AND_VDI_RECORD_ACTION="DELETE",
            ),
            install_commands=get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/common/install_commands.sh",
                    "source/idea/pipeline/scripts/destroy/install_commands.sh",
                ]
            ),
            commands=get_commands_for_scripts(commands),
            role_policy_statements=[
                codebuild_cloudformation_read_policy,
                codebuild_cloudformation_delete_stack_policy,
                codebuild_read_ssm_parameter_vpc_id_policy,
                codebuild_read_file_systems_policy,
                codebuild_efs_delete_file_systems_policy,
                codebuild_efs_filesystem_ec2_delete_eni_policy,
                codebuild_fsx_delete_file_systems_policy,
                codebuild_fsx_delete_svms_volumes_policy,
                codebuild_shared_storage_security_group_read_policy,
                codebuild_shared_storage_security_group_delete_policy,
                codebuild_destroy_records_read_policy,
                codebuild_destroy_records_route53_policy,
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
                SKIP_ENV_UPDATE="true",
                ONBOARDED_REGIONS=self.onboarded_regions,
            ),
            install_commands=get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/common/install_commands.sh",
                    "source/idea/pipeline/scripts/publish/install_commands.sh",
                ]
            ),
            commands=get_commands_for_scripts(
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

    def get_latest_bucket_refresh_steps(self) -> pipelines.CodeBuildStep:
        codebuild_s3_all_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:PutObject",
                "s3:getBucketLocation",
                "s3:ListBucket",
                "s3:GetObject",
                "s3:DeleteObject",
            ],
            resources=[
                f"arn:{self.partition}:s3:::{ARTIFACTS_BUCKET_PREFIX_NAME}-*",
            ],
        )

        return pipelines.CodeBuildStep(
            "Refresh the /latest bucket",
            env=dict(
                ARTIFACTS_BUCKET_PREFIX_NAME=ARTIFACTS_BUCKET_PREFIX_NAME,
                ONBOARDED_REGIONS=self.onboarded_regions,
            ),
            commands=get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/publish/latest_bucket_refresh.sh",
                ]
            ),
            role_policy_statements=[codebuild_s3_all_access],
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
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        use_bi_parameters_from_ssm: bool,
        parameters: Union[RESParameters, BIParameters],
    ):
        super().__init__(scope, construct_id)
        registry_name = self.node.try_get_context("registry_name")

        self.batteries_included_stack = None
        if isinstance(parameters, BIParameters) and not use_bi_parameters_from_ssm:
            bi_stack_template_url = self.node.try_get_context("BIStackTemplateURL")
            self.batteries_included_stack = BiStack(
                self,
                BATTERIES_INCLUDED_STACK_NAME,
                template_url=bi_stack_template_url,
                parameters=parameters,
            )

        self.install_stack = InstallStack(
            self,
            INSTALL_STACK_NAME,
            parameters=parameters,
            registry_name=registry_name,
        )
        if self.batteries_included_stack:
            self.install_stack.add_dependency(target=self.batteries_included_stack)
