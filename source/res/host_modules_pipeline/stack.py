#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk import CfnCondition, Fn, Stack
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_iam as iam
from constructs import Construct

from idea.constants import ARTIFACTS_BUCKET_PREFIX_NAME

VERSION_FILE = "source/res/host_modules/modules.json"
ONBOARDED_REGIONS = "ap-northeast-1,ap-northeast-2,ap-south-1,ap-southeast-1,ap-southeast-2,ca-central-1,eu-central-1,eu-north-1,eu-south-1,eu-west-1,eu-west-2,eu-west-3,us-east-1,us-east-2,us-west-1,us-west-2"
ONBOARDED_REGIONS_GOVCLOUD = "us-gov-west-1"


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

        source_output = codepipeline.Artifact()
        build_output_x86_64 = codepipeline.Artifact("BuildOutputX86_64")
        build_output_arm64 = codepipeline.Artifact("BuildOutputArm64")

        stages = [
            self._create_source_stage(source_output),
            self._create_unit_test_stage(source_output),
            self._create_build_stage(
                source_output, build_output_x86_64, build_output_arm64
            ),
        ]

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

            stages.append(
                self._create_publish_stage(
                    source_output, build_output_x86_64, build_output_arm64
                )
            )
            if self._public_release:
                stages.append(self._create_manual_approval_stage())
                stages.append(
                    self._create_publish_latest_stage(
                        source_output, build_output_x86_64, build_output_arm64
                    )
                )

        pipeline = codepipeline.Pipeline(self, "Pipeline", stages=stages)

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

    def _create_source_stage(
        self, source_output: codepipeline.Artifact
    ) -> codepipeline.StageProps:
        repository = codecommit.Repository.from_repository_name(
            scope=self,
            id="CodeCommitSource",
            repository_name=self._repository_name,
        )
        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="CodeCommit_Source",
            repository=repository,
            branch=self._branch_name,
            output=source_output,
        )
        return codepipeline.StageProps(stage_name="Source", actions=[source_action])

    def _create_unit_test_stage(
        self, source_output: codepipeline.Artifact
    ) -> codepipeline.StageProps:
        unit_test_project = codebuild.PipelineProject(
            self,
            "UnitTest",
            build_spec=codebuild.BuildSpec.from_source_filename(
                "source/res/host_modules_pipeline/buildspecs/unit_test_buildspec.yml"
            ),
        )
        unit_test_action = codepipeline_actions.CodeBuildAction(
            action_name="CodeBuildUnitTest",
            project=unit_test_project,
            input=source_output,
        )
        return codepipeline.StageProps(
            stage_name="UnitTest", actions=[unit_test_action]
        )

    def _create_build_stage(
        self,
        source_output: codepipeline.Artifact,
        build_output_x86_64: codepipeline.Artifact,
        build_output_arm64: codepipeline.Artifact,
    ) -> codepipeline.StageProps:
        build_action_amd64 = codepipeline_actions.CodeBuildAction(
            action_name="CodeBuildAmd64",
            project=self._create_build_project("BuildProjectAmd64"),
            input=source_output,
            outputs=[build_output_x86_64],
        )
        build_action_arm64 = codepipeline_actions.CodeBuildAction(
            action_name="CodeBuildArm64",
            project=self._create_build_project("BuildProjectArm64", arch="arm64"),
            input=source_output,
            outputs=[build_output_arm64],
        )
        return codepipeline.StageProps(
            stage_name="Build", actions=[build_action_amd64, build_action_arm64]
        )

    def _create_build_project(
        self, id: str, arch: str = ""
    ) -> codebuild.PipelineProject:
        environment = codebuild.BuildEnvironment(
            build_image=(
                codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM
                if arch == "arm64"
                else codebuild.LinuxBuildImage.STANDARD_5_0
            ),
            privileged=True,
        )
        return codebuild.PipelineProject(
            self,
            id,
            build_spec=codebuild.BuildSpec.from_source_filename(
                "source/res/host_modules_pipeline/buildspecs/buildspec.yml"
            ),
            environment=environment,
        )

    def _create_publish_stage(
        self,
        source_output: codepipeline.Artifact,
        build_output_x86_64: codepipeline.Artifact,
        build_output_arm64: codepipeline.Artifact,
    ) -> codepipeline.StageProps:
        publish_project = self._create_publish_project()
        publish_action = codepipeline_actions.CodeBuildAction(
            action_name="PublishHostModules",
            project=publish_project,
            input=source_output,
            extra_inputs=[build_output_x86_64, build_output_arm64],
        )
        return codepipeline.StageProps(stage_name="Publish", actions=[publish_action])

    def _create_publish_project(self) -> codebuild.PipelineProject:
        environment_variables = {
            "S3_BUCKET_NAME": {"value": self._s3_bucket_name},
            "VERSION_FILE": {"value": VERSION_FILE},
            "ONBOARDED_REGIONS": {"value": self.onboarded_regions},
            "PUBLIC_RELEASE": {"value": str(self._public_release).lower()},
            "ARTIFACTS_BUCKET_PREFIX_NAME": {"value": ARTIFACTS_BUCKET_PREFIX_NAME},
        }
        project = codebuild.PipelineProject(
            self,
            "PublishProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0, privileged=True
            ),
            build_spec=codebuild.BuildSpec.from_source_filename(
                "source/res/host_modules_pipeline/buildspecs/publish_buildspec.yml"
            ),
            environment_variables=environment_variables,
        )
        s3_policy = iam.PolicyStatement(
            actions=["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
            resources=(
                [
                    f"arn:{self.partition}:s3:::{ARTIFACTS_BUCKET_PREFIX_NAME}-*/host_modules/*"
                ]
                if self._public_release
                else [
                    f"arn:{self.partition}:s3:::{self._s3_bucket_name}/host_modules/*"
                ]
            ),
        )
        role = project.role
        if isinstance(role, iam.Role):
            role.add_to_policy(s3_policy)
        return project

    def _create_manual_approval_stage(self) -> codepipeline.StageProps:
        manual_approval_action = codepipeline_actions.ManualApprovalAction(
            action_name="ApprovePublishingToLatest"
        )
        return codepipeline.StageProps(
            stage_name="ManualApproval", actions=[manual_approval_action]
        )

    def _create_publish_latest_stage(
        self,
        source_output: codepipeline.Artifact,
        build_output_x86_64: codepipeline.Artifact,
        build_output_arm64: codepipeline.Artifact,
    ) -> codepipeline.StageProps:
        publish_latest_project = self._create_publish_latest_project()
        publish_latest_action = codepipeline_actions.CodeBuildAction(
            action_name="PublishHostModulesToLatest",
            project=publish_latest_project,
            input=source_output,
            extra_inputs=[build_output_x86_64, build_output_arm64],
        )
        return codepipeline.StageProps(
            stage_name="PublishToLatest", actions=[publish_latest_action]
        )

    def _create_publish_latest_project(self) -> codebuild.PipelineProject:
        environment_variables = {
            "VERSION_FILE": {"value": VERSION_FILE},
            "ONBOARDED_REGIONS": {"value": self.onboarded_regions},
            "ARTIFACTS_BUCKET_PREFIX_NAME": {"value": ARTIFACTS_BUCKET_PREFIX_NAME},
        }
        project = codebuild.PipelineProject(
            self,
            "PublishLatestProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0, privileged=True
            ),
            build_spec=codebuild.BuildSpec.from_source_filename(
                "source/res/host_modules_pipeline/buildspecs/publish_latest_buildspec.yml"
            ),
            environment_variables=environment_variables,
        )
        s3_policy = iam.PolicyStatement(
            actions=["s3:PutObject", "s3:DeleteObject"],
            resources=[
                f"arn:{self.partition}:s3:::{ARTIFACTS_BUCKET_PREFIX_NAME}-*/host_modules/*"
            ],
        )
        role = project.role
        if isinstance(role, iam.Role):
            role.add_to_policy(s3_policy)
        return project
