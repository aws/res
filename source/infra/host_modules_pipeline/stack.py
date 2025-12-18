#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk import CfnCondition, Fn, Stack
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_iam as iam
from aws_cdk import pipelines
from constructs import Construct

from idea.constants import ARTIFACTS_BUCKET_PREFIX_NAME
from idea.pipeline.utils import get_commands_for_scripts

VERSION_FILE = "source/infra/host_modules/modules.json"
ONBOARDED_REGIONS = "ap-northeast-1,ap-northeast-2,ap-northeast-3,ap-south-1,ap-southeast-1,ap-southeast-2,ca-central-1,eu-central-1,eu-north-1,eu-south-1,eu-west-1,eu-west-2,eu-west-3,sa-east-1,us-east-1,us-east-2,us-west-1,us-west-2"
ONBOARDED_REGIONS_GOVCLOUD = "us-gov-west-1,us-gov-east-1"


class HostModulePipelineStack(Stack):
    _repository_name: str = "DigitalEngineeringPlatform"
    _branch_name: str = "develop"
    _publish_modules: bool = False
    _public_release: bool = False
    _s3_bucket_name: str = ""

    @property
    def repository_name(self) -> str:
        return self._repository_name

    @property
    def branch_name(self) -> str:
        return self._branch_name

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)
        self._load_context()

        pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            synth=self._create_synth_step(),
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    privileged=True,
                ),
            ),
        )

        # Add unit test stage
        pipeline.add_wave("UnitTest", pre=[self._create_unit_test_step()])

        # Add build stages (parallel) with outputs
        build_amd64 = self._create_build_step("BuildAmd64")
        build_arm64 = self._create_build_step("BuildArm64", arch="arm64")
        build_wave = pipeline.add_wave("BuildModules")
        build_wave.add_pre(build_amd64)
        build_wave.add_pre(build_arm64)

        # Add publish stages if enabled
        if self._publish_modules:
            is_classic_region = CfnCondition(
                self,
                "IsClassicRegion",
                expression=Fn.condition_equals(self.partition, "aws"),
            )
            self.onboarded_regions = Fn.condition_if(
                is_classic_region.logical_id,
                ONBOARDED_REGIONS,
                ONBOARDED_REGIONS_GOVCLOUD,
            ).to_string()

            pipeline.add_wave(
                "Publish",
                pre=[self._create_publish_step([build_amd64, build_arm64])],
            )

            if self._public_release:
                pipeline.add_wave(
                    "ApprovalForLatest",
                    pre=[pipelines.ManualApprovalStep("ApprovePublishingToLatest")],
                )
                pipeline.add_wave(
                    "PublishToLatest",
                    pre=[self._create_publish_latest_step([build_amd64, build_arm64])],
                )

    def _load_context(self) -> None:
        context_repository_name = self.node.try_get_context("repository_name")
        if context_repository_name:
            self._repository_name = context_repository_name
        context_branch_name = self.node.try_get_context("branch_name")
        if context_branch_name:
            self._branch_name = context_branch_name
        context_publish_modules = self.node.try_get_context("publish_modules")
        if context_publish_modules:
            self._publish_modules = context_publish_modules.lower() == "true"
            context_public_release = self.node.try_get_context("public_release")
            if context_public_release:
                self._public_release = context_public_release.lower() == "true"
            if not self._public_release:
                context_s3_bucket_name = self.node.try_get_context("s3_bucket_name")
                if context_s3_bucket_name:
                    self._s3_bucket_name = context_s3_bucket_name

    def _create_synth_step(self) -> pipelines.CodeBuildStep:
        env_vars = {
            "PIPELINE_REPOSITORY_NAME": self._repository_name,
            "PIPELINE_BRANCH_NAME": self._branch_name,
            "PIPELINE_PUBLISH_MODULES": str(self._publish_modules).lower(),
        }

        if self._publish_modules:
            env_vars["PIPELINE_PUBLIC_RELEASE"] = str(self._public_release).lower()
            if not self._public_release and self._s3_bucket_name:
                env_vars["PIPELINE_S3_BUCKET_NAME"] = self._s3_bucket_name

        return pipelines.CodeBuildStep(
            "Synth",
            input=pipelines.CodePipelineSource.code_commit(
                repository=codecommit.Repository.from_repository_name(
                    scope=self,
                    id="CodeCommitSource",
                    repository_name=self._repository_name,
                ),
                branch=self._branch_name,
            ),
            install_commands=get_commands_for_scripts(
                [
                    "source/idea/pipeline/scripts/common/install_commands.sh",
                    "source/idea/pipeline/scripts/synth/install_commands.sh",
                ]
            ),
            commands=get_commands_for_scripts(
                [
                    "source/infra/host_modules_pipeline/scripts/synth.sh",
                ]
            ),
            env=env_vars,
        )

    def _create_unit_test_step(self) -> pipelines.CodeBuildStep:
        return pipelines.CodeBuildStep(
            "UnitTest",
            commands=[
                "chmod +x source/infra/host_modules_pipeline/scripts/unit_test.sh",
                "source/infra/host_modules_pipeline/scripts/unit_test.sh",
            ],
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0
            ),
        )

    def _create_build_step(
        self, step_id: str, arch: str = ""
    ) -> pipelines.CodeBuildStep:
        build_image = (
            codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM
            if arch == "arm64"
            else codebuild.LinuxBuildImage.STANDARD_5_0
        )
        return pipelines.CodeBuildStep(
            step_id,
            commands=[
                "chmod +x source/infra/host_modules_pipeline/scripts/build.sh",
                "source/infra/host_modules_pipeline/scripts/build.sh",
            ],
            build_environment=codebuild.BuildEnvironment(
                build_image=build_image, privileged=True
            ),
            primary_output_directory=".",
        )

    def _create_publish_step(
        self, build_steps: list[pipelines.CodeBuildStep]
    ) -> pipelines.CodeBuildStep:
        environment_variables = {
            "S3_BUCKET_NAME": self._s3_bucket_name,
            "VERSION_FILE": VERSION_FILE,
            "ONBOARDED_REGIONS": self.onboarded_regions,
            "PUBLIC_RELEASE": str(self._public_release).lower(),
            "ARTIFACTS_BUCKET_PREFIX_NAME": ARTIFACTS_BUCKET_PREFIX_NAME,
        }

        # Add S3 permissions
        s3_resources = (
            [
                f"arn:{self.partition}:s3:::{ARTIFACTS_BUCKET_PREFIX_NAME}-*/host_modules/*"
            ]
            if self._public_release
            else [f"arn:{self.partition}:s3:::{self._s3_bucket_name}/host_modules/*"]
        )

        return pipelines.CodeBuildStep(
            "PublishHostModules",
            commands=[
                "chmod +x source/infra/host_modules_pipeline/scripts/publish.sh",
                "source/infra/host_modules_pipeline/scripts/publish.sh $CODEBUILD_SRC_DIR $CODEBUILD_SRC_DIR/build_arm64",
            ],
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0, privileged=True
            ),
            env=environment_variables,
            input=build_steps[0],
            additional_inputs={
                "build_arm64": build_steps[1],
            },
            role_policy_statements=[
                iam.PolicyStatement(
                    actions=["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
                    resources=s3_resources,
                )
            ],
        )

    def _create_publish_latest_step(
        self, build_steps: list[pipelines.CodeBuildStep]
    ) -> pipelines.CodeBuildStep:
        environment_variables = {
            "VERSION_FILE": VERSION_FILE,
            "ONBOARDED_REGIONS": self.onboarded_regions,
            "ARTIFACTS_BUCKET_PREFIX_NAME": ARTIFACTS_BUCKET_PREFIX_NAME,
        }

        return pipelines.CodeBuildStep(
            "PublishHostModulesToLatest",
            commands=[
                "chmod +x source/infra/host_modules_pipeline/scripts/publish_latest.sh",
                "source/infra/host_modules_pipeline/scripts/publish_latest.sh $CODEBUILD_SRC_DIR $CODEBUILD_SRC_DIR/build_arm64",
            ],
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0, privileged=True
            ),
            env=environment_variables,
            input=build_steps[0],
            additional_inputs={
                "build_arm64": build_steps[1],
            },
            role_policy_statements=[
                iam.PolicyStatement(
                    actions=["s3:PutObject", "s3:DeleteObject"],
                    resources=[
                        f"arn:{self.partition}:s3:::{ARTIFACTS_BUCKET_PREFIX_NAME}-*/host_modules/*"
                    ],
                )
            ],
        )
