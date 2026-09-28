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
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import pipelines
from constructs import Construct

from idea.batteries_included.parameters.parameters import BIParameters
from idea.batteries_included.stack import BiStack
from idea.constants import (
    ARTIFACTS_BUCKET_PREFIX_NAME,
    BATTERIES_INCLUDED_STACK_NAME,
    DEFAULT_ECR_REPOSITORY_NAME,
    INSTALL_STACK_NAME,
    STAGING_BUCKET_PREFIX_NAME,
    TESTING_INFRA_STACK_NAME,
)
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.stacks.install_stack import InstallStack
from idea.isolated_vpc.parameters import IsolatedVpcParameters
from idea.pipeline.ami_build_stack import AMIBuildStack
from idea.pipeline.integ_tests.integ_test_step_builder import IntegTestStepBuilder
from idea.pipeline.isolated_vpc_infra_stack import IsolatedVpcInfraStack
from idea.pipeline.testing_infra_stack import StorageTemplateUrls, TestingInfraStack
from idea.pipeline.utils import get_commands_for_scripts

UNIT_TESTS = [
    "tests.administrator",
    "tests.cluster-manager",
    "tests.library",
    "tests.datamodel",
    "tests.sdk",
    "tests.bootstrap",
    "tests.pipeline",
    "tests.infrastructure",
    "tests.dcv-session-management",
]
COVERAGEREPORTS = ["coverage"]
INFRA_HOST_INTEG_TESTS = ["integ-tests.cluster-manager"]
SCANS = ["npm_audit", "bandit", "viperlight_scan"]
PUBLICECRRepository = "public.ecr.aws/l6g7n3r5/research-engineering-studio"
ONBOARDED_REGIONS = "ap-northeast-1,ap-northeast-2,ap-northeast-3,ap-south-1,ap-southeast-1,ap-southeast-2,ca-central-1,eu-central-1,eu-north-1,eu-south-1,eu-west-1,eu-west-2,eu-west-3,sa-east-1,us-east-1,us-east-2,us-west-1,us-west-2"
ONBOARDED_REGIONS_GOVCLOUD = "us-gov-west-1,us-gov-east-1"


class PipelineStack(Stack):
    # Set Default Values if Not in ENV
    _repository_name: str = "DigitalEngineeringPlatform"
    _branch_name: str = "develop"
    _deploy: bool = False
    _integ_tests: bool = False
    _test_suite: str = "dev"
    # Source trigger for the pipeline: "events" (default; fire on CodeCommit commit)
    # or "none" (no commit trigger — e.g. a schedule-only nightly pipeline).
    _source_trigger: str = "events"
    # When true, add an EventBridge rule that starts the pipeline on _schedule_cron.
    _schedule_trigger: bool = False
    # UTC cron for the scheduled trigger. Default 09:00 UTC = 2am PT (PDT) / 1am (PST),
    # weekdays only (Mon-Fri, evaluated in UTC; 09:00 UTC keeps the PT weekday aligned).
    _schedule_cron: str = "cron(0 9 ? * MON-FRI *)"
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
        env: Union[aws_cdk.Environment, dict[str, typing.Any], None] = None,
    ) -> None:
        super().__init__(scope, construct_id, synthesizer=synthesizer, env=env)

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
        # Which integration test suite the pipeline runs: dev (default, fast
        # per-commit), nightly, or release. Selected via `-c test_suite=<suite>`.
        context_test_suite = self.node.try_get_context("test_suite")
        if context_test_suite:
            self._test_suite = context_test_suite.lower()
        # Source trigger: "events" (default) or "none" to disable the CodeCommit
        # commit trigger (e.g. for a schedule-only nightly pipeline).
        context_source_trigger = self.node.try_get_context("source_trigger")
        if context_source_trigger:
            self._source_trigger = context_source_trigger.lower()
        # Optional scheduled trigger (EventBridge cron) — used by the scheduled
        # nightly pipelines. `schedule_cron` overrides the default UTC cron.
        context_schedule_trigger = self.node.try_get_context("schedule_trigger")
        if context_schedule_trigger:
            self._schedule_trigger = context_schedule_trigger.lower() == "true"
        context_schedule_cron = self.node.try_get_context("schedule_cron")
        if context_schedule_cron:
            self._schedule_cron = context_schedule_cron
        if context_destroy:
            self._destroy = context_destroy.lower() == "true"
        if context_destroy_bi:
            self._destroy_bi = context_destroy_bi.lower() == "true"
        context_publish_templates = self.node.try_get_context("publish_templates")
        if context_publish_templates:
            self._publish_templates = context_publish_templates.lower() == "true"

        context_is_load_balancer_internet_facing = self.node.try_get_context(
            "IsLoadBalancerInternetFacing"
        )
        is_load_balancer_internet_facing = (
            context_is_load_balancer_internet_facing.strip('"').lower() != "false"
            if context_is_load_balancer_internet_facing
            else True
        )

        self.params: Union[RESParameters, BIParameters, IsolatedVpcParameters]
        if self._bi or self._use_bi_parameters_from_ssm:
            self.params = BIParameters.from_context(self)
        elif not is_load_balancer_internet_facing:
            self.params = IsolatedVpcParameters.from_context(self)
        else:
            self.params = RESParameters.from_context(self)
        if self.params.cluster_name is None:
            self.params.cluster_name = "res-deploy"

        bi_stack_template_url = self.node.try_get_context("BIStackTemplateURL")
        bi_stack_template_url = bi_stack_template_url if bi_stack_template_url else ""

        # Storage recipe template URLs for TestingInfraStack
        self._efs_template_url = self.node.try_get_context("AmazonEFSTemplateURL") or ""
        self._fsx_lustre_template_url = (
            self.node.try_get_context("AmazonFSxForLustreTemplateURL") or ""
        )
        self._fsx_ontap_template_url = (
            self.node.try_get_context("AmazonFSxForONTAPTemplateURL") or ""
        )
        context_testing_infra_included = self.node.try_get_context(
            "testing_infra_included"
        )
        self._testing_infra_included = (
            str(context_testing_infra_included).lower() == "true"
            if context_testing_infra_included
            else False
        )
        context_ontap_ad_join = self.node.try_get_context("ontap_ad_join")
        self._ontap_ad_join = (
            str(context_ontap_ad_join).lower() == "true"
            if context_ontap_ad_join
            else False
        )

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

        ssm_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ssm:GetParameter",
            ],
            resources=["*"],
        )

        vpc_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeRouteTables",
                "ec2:DescribeNetworkAcls",
                "ec2:DescribeInternetGateways",
                "ec2:DescribeVpnGateways",
            ],
            resources=["*"],
        )

        # Create staging bucket
        self.staging_bucket_name = f"{STAGING_BUCKET_PREFIX_NAME}-{aws_cdk.Aws.REGION}-{aws_cdk.Aws.ACCOUNT_ID}"
        staging_bucket = s3.Bucket(
            self,
            STAGING_BUCKET_PREFIX_NAME,
            bucket_name=self.staging_bucket_name,
            access_control=s3.BucketAccessControl.PRIVATE,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
        )
        staging_bucket_write_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:PutObject",
                "s3:DeleteObject",
            ],
            resources=[
                f"arn:{self.partition}:s3:::{self.staging_bucket_name}",
                f"arn:{self.partition}:s3:::{self.staging_bucket_name}/*",
            ],
        )

        # CodeBuild permissions for pipeline to start pre-synth steps
        codebuild_start_build_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "codebuild:StartBuild",
                "codebuild:BatchGetBuilds",
                "codebuild:StopBuild",
            ],
            resources=[
                f"arn:{self.partition}:codebuild:{self.region}:{self.account}:project/*",
            ],
        )

        # S3 permissions for Config Update step to read AMI manifest and access staging bucket
        staging_bucket_read_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:ListBucket",
            ],
            resources=[
                f"arn:{self.partition}:s3:::{self.staging_bucket_name}",
                f"arn:{self.partition}:s3:::{self.staging_bucket_name}/*",
            ],
        )

        # Create a CodeBuild project with synth step that includes AMI build and config update
        synth_step = self.get_synth_step(
            ecr_repository_name,
            ecr_public_repository_name,
            bi_stack_template_url,
            context_use_bi_parameters_from_ssm,
            self.staging_bucket_name,
            is_load_balancer_internet_facing,
        )

        self._pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            synth=synth_step,
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    compute_type=codebuild.ComputeType.LARGE,
                    privileged=True,
                ),
                role_policy=[
                    codebuild_ecr_access,
                    codebuild_ecr_push,
                    ssm_access,
                    vpc_access,
                    staging_bucket_write_access,
                    staging_bucket_read_access,
                    codebuild_start_build_policy,
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["sts:AssumeRole"],
                        resources=[
                            f"arn:{self.partition}:iam::{self.account}:role/*",
                        ],
                    ),
                ],
            ),
        )

        audit_wave = self._pipeline.add_wave("SecurityAudit")
        audit_wave.add_post(*self.get_steps_from_tox(SCANS))
        unittest_wave = self._pipeline.add_wave("UnitTests")
        unittest_wave.add_post(*self.get_steps_for_unit_tests(UNIT_TESTS))
        coverage_wave = self._pipeline.add_wave("Coverage")
        coverage_wave.add_post(*self.get_steps_for_unit_tests(COVERAGEREPORTS))

        if self._deploy:
            deploy_stage = DeployStage(
                self,
                "Deploy",
                use_bi_parameters_from_ssm=self._use_bi_parameters_from_ssm,
                parameters=self.params,
                staging_bucket_name=self.staging_bucket_name,
            )

            post_steps = []
            create_web_and_vdi_record_step = self.get_create_web_and_vdi_record_step()
            if self._portal_domain_name != "":
                post_steps.append(create_web_and_vdi_record_step)

            if self._integ_tests:
                component_integ_test_steps = self.get_infra_host_integ_test_steps(
                    INFRA_HOST_INTEG_TESTS
                )
                component_integ_test_steps.append(self.get_ad_sync_integ_test_step())

                # Run the marker-based suite selected by the `test_suite` context
                # variable (default dev). The dev suite is a superset of the api
                # tests (the tests/api dir is auto-marked @dev) plus the Tier 0
                # infra_validation checks, so it replaces the standalone api step.
                suite_test_step = self.get_suite_test_step(self._test_suite)

                # Suite tests cannot run with other integ tests in parallel, as they require to relaunch the infra host applications
                # and the servers will become temporarily unresponsive to other integ tests.
                # And all integ tests should run after create_web_and_vdi_record_step.
                for component_integ_test_step in component_integ_test_steps:
                    suite_test_step.add_step_dependency(component_integ_test_step)
                    if self._portal_domain_name != "":
                        component_integ_test_step.add_step_dependency(
                            create_web_and_vdi_record_step
                        )

                post_steps += component_integ_test_steps
                post_steps.append(suite_test_step)

                # The per-commit (dev) pipeline runs the AL2023 smoke subset as a
                # separate parallel step. For nightly/release the full smoke matrix is
                # collected by the suite step itself (smoke tests are @nightly-tagged),
                # so no standalone smoke step is added there.
                if self._test_suite == "dev":
                    smoke_test_step = self.get_smoke_test_step()
                    # Smoke tests cannot run with the suite tests in parallel,
                    # since both of them need to restart the infra host applications.
                    smoke_test_step.add_step_dependency(suite_test_step)
                    post_steps.append(smoke_test_step)

            if self._destroy:
                destroy_step = self.get_destroy_step()
                # Destroy step should only execute after all the other steps complete
                for step in post_steps:
                    destroy_step.add_step_dependency(step)
                post_steps.append(destroy_step)

            # The AMI build step now runs before build stages, so artifacts are available in deploy stage
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
            publish_steps = self.get_publish_steps(
                ecr_public_repository_name, self.staging_bucket_name
            )
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

        # Add nested stacks for isolated VPC deployments
        # Only created when IsLoadBalancerInternetFacing=false
        self.prebaked_res_ready_amis_stack = None
        self.isolated_vpc_infra_stack = None
        if not is_load_balancer_internet_facing:
            # VPC endpoints + proxy server (must deploy before AMI builds need proxy)
            vpc_id = self.params.vpc_id or ""
            private_subnet_ids = self.params.infrastructure_host_subnets or []
            vpc_cidr = self.node.try_get_context("VpcCIDR") or ""
            public_subnet_id = self.node.try_get_context("PublicSubnetId") or ""

            if vpc_id and private_subnet_ids and public_subnet_id and vpc_cidr:
                self.isolated_vpc_infra_stack = IsolatedVpcInfraStack(
                    self,
                    "IsolatedVpcInfraStack",
                    vpc_id=vpc_id,
                    private_subnet_ids=private_subnet_ids,
                    public_subnet_id=public_subnet_id,
                    vpc_cidr=vpc_cidr,
                    http_proxy_ssm_path=self.params.http_proxy or "HttpProxy",
                    https_proxy_ssm_path=self.params.https_proxy or "HttpsProxy",
                    no_proxy_ssm_path=self.params.no_proxy or "NoProxy",
                )

            # Image Builder pipelines for pre-baking AMIs
            self.prebaked_res_ready_amis_stack = AMIBuildStack(
                self,
                "AMIBuildStackV2",
                staging_bucket=self.staging_bucket_name,
            )
        if self._publish_templates and publish_steps and publish_steps.project.role:
            CfnOutput(
                self,
                "PublishCodeBuildRole",
                value=publish_steps.project.role.role_name,
            )

        # Scheduled trigger (e.g. the 2am-PT nightly pipelines). The underlying
        # CodePipeline is only available after build_pipeline(); the CodePipeline
        # event target self-grants StartPipelineExecution.
        if self._schedule_trigger:
            events.Rule(
                self,
                "ScheduledTrigger",
                schedule=events.Schedule.expression(self._schedule_cron),
                targets=[events_targets.CodePipeline(self._pipeline.pipeline)],
            )

    def get_connection(self) -> pipelines.CodePipelineSource:
        # "none" disables the on-commit trigger (e.g. schedule-only nightly pipelines);
        # default "events" fires the pipeline whenever the branch receives a commit.
        trigger = (
            codepipeline_actions.CodeCommitTrigger.NONE
            if self._source_trigger == "none"
            else codepipeline_actions.CodeCommitTrigger.EVENTS
        )
        return pipelines.CodePipelineSource.code_commit(
            repository=codecommit.Repository.from_repository_name(
                scope=self,
                id="CodeCommitSource",
                repository_name=self._repository_name,
            ),
            branch=self._branch_name,
            trigger=trigger,
        )

    def get_synth_step(
        self,
        ecr_repository_name: str,
        ecr_public_repository_name: str,
        bi_stack_template_url: str,
        use_bi_parameters_from_ssm: str,
        staging_bucket_name: str,
        is_load_balancer_internet_facing: bool,
    ) -> pipelines.CodeBuildStep:
        # Determine install commands based on whether AMI build is needed
        install_commands = [
            "source/idea/pipeline/scripts/common/install_commands.sh",
            "source/idea/pipeline/scripts/synth/install_commands.sh",
        ]

        # Determine commands based on whether AMI build is needed
        commands = []

        # Add AMI build and config update commands if load balancer is NOT internet facing
        if not is_load_balancer_internet_facing:
            install_commands.append(
                "source/idea/pipeline/scripts/ami_build/install_commands.sh"
            )
            commands.extend(
                [
                    "source/idea/pipeline/scripts/ami_build/ami_build_commands.sh",
                    "source/idea/pipeline/scripts/ami_build/config_update_commands.sh",
                ]
            )

        # Always add synth commands at the end
        commands.append("source/idea/pipeline/scripts/synth/commands.sh")

        # Additional IAM permissions needed for AMI build functionality
        additional_role_policies = []
        if not is_load_balancer_internet_facing:
            # CloudFormation permissions for AMI build
            cloudformation_read_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudformation:DescribeStackResources",
                    "cloudformation:ListStackResources",
                ],
                resources=[
                    f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/*",
                ],
            )
            cloudformation_list_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "cloudformation:DescribeStacks",
                    "cloudformation:ListStacks",
                ],
                resources=["*"],
            )

            # ImageBuilder permissions
            imagebuilder_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "imagebuilder:StartImagePipelineExecution",
                    "imagebuilder:GetImage",
                    "imagebuilder:GetImagePipeline",
                ],
                resources=[
                    f"arn:{self.partition}:imagebuilder:{self.region}:{self.account}:image/*",
                    f"arn:{self.partition}:imagebuilder:{self.region}:{self.account}:image-pipeline/*",
                ],
            )
            imagebuilder_list_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "imagebuilder:ListImagePipelines",
                    "imagebuilder:ListImages",
                ],
                resources=["*"],
            )

            # Parameter Store permissions for AMI manifest storage
            parameter_store_policy = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ssm:GetParameter",
                    "ssm:PutParameter",
                ],
                resources=[
                    f"arn:{self.partition}:ssm:{self.region}:{self.account}:parameter/*",
                ],
            )

            additional_role_policies.extend(
                [
                    cloudformation_read_policy,
                    cloudformation_list_policy,
                    imagebuilder_policy,
                    imagebuilder_list_policy,
                    parameter_store_policy,
                ]
            )

        return pipelines.CodeBuildStep(
            "Synth",
            input=self.get_connection(),
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=(
                    codebuild.ComputeType.LARGE
                    if not is_load_balancer_internet_facing
                    else codebuild.ComputeType.MEDIUM
                ),
                privileged=True,
            ),
            timeout=(
                Duration.hours(4)
                if not is_load_balancer_internet_facing
                else Duration.hours(1)
            ),  # Allow more time for AMI builds
            env=dict(
                REPOSITORY_NAME=self._repository_name,
                BRANCH=self._branch_name,
                DEPLOY="true" if self._deploy else "false",
                INTEGRATION_TESTS="true" if self._integ_tests else "false",
                TEST_SUITE=self._test_suite,
                SOURCE_TRIGGER=self._source_trigger,
                SCHEDULE_TRIGGER="true" if self._schedule_trigger else "false",
                SCHEDULE_CRON=self._schedule_cron,
                DESTROY="true" if self._destroy else "false",
                DESTROY_BATTERIES_INCLUDED="true" if self._destroy_bi else "false",
                BATTERIES_INCLUDED="true" if self._bi else "false",
                BIStackTemplateURL=bi_stack_template_url,
                AmazonEFSTemplateURL=self._efs_template_url,
                AmazonFSxForLustreTemplateURL=self._fsx_lustre_template_url,
                AmazonFSxForONTAPTemplateURL=self._fsx_ontap_template_url,
                TESTING_INFRA_INCLUDED=(
                    "true" if self._testing_infra_included else "false"
                ),
                ONTAP_AD_JOIN="true" if self._ontap_ad_join else "false",
                ADDnsIPs=self.node.try_get_context("ADDnsIPs") or "",
                ECR_REPOSITORY=ecr_repository_name,
                STAGING_BUCKET_NAME=staging_bucket_name,
                ECR_PUBLIC_REPOSITORY_NAME=ecr_public_repository_name,
                USE_BI_PARAMETERS_FROM_SSM=use_bi_parameters_from_ssm,
                PUBLISH_TEMPLATES="true" if self._publish_templates else "false",
                SKIP_ENV_UPDATE="true",
                PORTAL_DOMAIN_NAME=self._portal_domain_name,
                AWS_DEFAULT_REGION=self.region,
                VpcCIDR=self.node.try_get_context("VpcCIDR") or "",
                PublicSubnetId=self.node.try_get_context("PublicSubnetId") or "",
                **self.params.to_context(),
            ),
            install_commands=get_commands_for_scripts(install_commands),
            commands=get_commands_for_scripts(commands),
            role_policy_statements=additional_role_policies,
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
            resources=[
                f"arn:{self.partition}:route53:::hostedzone/*",
                f"arn:{self.partition}:route53:::change/*",
            ],
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

    def get_infra_host_integ_test_steps(
        self, integ_test_envs: list[str]
    ) -> list[pipelines.CodeBuildStep]:
        steps: list[pipelines.CodeBuildStep] = []
        clusteradmin_username = "clusteradmin"  # bootstrap user
        clusteradmin_password = "RESPassword1."  # fixed password for running tests

        for _env in integ_test_envs:
            _step = (
                IntegTestStepBuilder(_env, self.params.cluster_name, self.region, True)
                .test_specific_invoke_command_argument(
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

    def _session_test_infra_policy_statements(self) -> list[iam.PolicyStatement]:
        """Permissions for ALB setup/teardown, SSM connectivity, and Lambda config."""
        return [
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
                        "ssm:GetParameter",
                        "ssm:PutParameter",
                        "ssm:DeleteParameter",
                        "ssm:AddTagsToResource",
                        "ssm:ListTagsForResource",
                    ],
                    "Resource": [
                        f"arn:{self.partition}:ssm:{self.region}:{self.account}:parameter/res/integ-test/*",
                        f"arn:{self.partition}:ssm:{self.region}::parameter/aws/service/ami-amazon-linux-latest/*",
                    ],
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
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:GetFunctionConfiguration",
                        "lambda:UpdateFunctionConfiguration",
                    ],
                    "Resource": f"arn:{self.partition}:lambda:{self.region}:{self.account}:function:{self.params.cluster_name}-backend-lambda",
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": ["ec2:DescribeSecurityGroups"],
                    "Resource": "*",
                }
            ),
        ]

    def get_smoke_test_step(self) -> pipelines.CodeBuildStep:
        builder = IntegTestStepBuilder(
            "integ-tests.smoke",
            self.params.cluster_name,
            self.region,
            compute_type=codebuild.ComputeType.LARGE,
        ).test_specific_role_policy_statement(
            *self._session_test_infra_policy_statements(),
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
                        "dynamodb:GetItem",
                        "dynamodb:Scan",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                    ],
                    "Resource": [
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.cluster-settings",
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.ad-sync.distributed-lock",
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.ad-sync.status",
                    ],
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction",
                    ],
                    "Resource": f"arn:{self.partition}:lambda:{self.region}:{self.account}:function:{self.params.cluster_name}-cognito-sync-lambda",
                },
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecs:RunTask",
                        "ecs:StopTask",
                        "ecs:ListTasks",
                    ],
                    "Resource": "*",
                    "Condition": {
                        "ArnEquals": {
                            "ecs:cluster": f"arn:{self.partition}:ecs:{self.region}:{self.account}:cluster/{self.params.cluster_name}-ad-sync-cluster",
                        }
                    },
                },
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:PassRole",
                    ],
                    "Resource": f"arn:{self.partition}:iam::{self.account}:role/{self.params.cluster_name}-ad-sync-task-role",
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:DescribeSecurityGroups",
                        "ec2:DeregisterImage",
                        "ec2:DescribeInstances",
                    ],
                    "Resource": "*",
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                    ],
                    # Wildcard needed: DCV client credentials are stored under
                    # {cluster_name}/ prefix but secret name suffixes are
                    # auto-generated by CloudFormation and not predictable at
                    # pipeline-definition time.
                    "Resource": f"arn:{self.partition}:secretsmanager:{self.region}:{self.account}:secret:{self.params.cluster_name}/*",
                }
            ),
        )

        # This step runs only in the per-commit (dev) pipeline (see the caller), so it
        # always runs the single-OS (AL2023) smoke subset. nightly/release collect the
        # full smoke matrix via their suite step instead.
        builder.test_specific_invoke_option("--marker-expr smoke_subset")

        return builder.build()

    def _api_test_role_policy_statements(self) -> list[iam.PolicyStatement]:
        """
        IAM policy statements needed by the API integration tests. Shared by the
        api and dev test steps (the dev suite is a superset of the api tests).
        """
        return [
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
                        "ssm:GetParameter",
                        "ssm:PutParameter",
                        "ssm:DeleteParameter",
                        "ssm:AddTagsToResource",
                        "ssm:ListTagsForResource",
                    ],
                    "Resource": [
                        f"arn:{self.partition}:ssm:{self.region}:{self.account}:parameter/res/integ-test/*",
                        f"arn:{self.partition}:ssm:{self.region}::parameter/aws/service/ami-amazon-linux-latest/*",
                    ],
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
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:Scan",
                        "dynamodb:PutItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                    ],
                    "Resource": [
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.cluster-settings",
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.ad-sync.distributed-lock",
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.ad-sync.status",
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.vdc.controller.user-sessions",
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.vdc.controller.session-permissions",
                    ],
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction",
                    ],
                    "Resource": f"arn:{self.partition}:lambda:{self.region}:{self.account}:function:{self.params.cluster_name}-cognito-sync-lambda",
                },
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecs:RunTask",
                        "ecs:StopTask",
                        "ecs:ListTasks",
                    ],
                    "Resource": "*",
                    "Condition": {
                        "ArnEquals": {
                            "ecs:cluster": f"arn:{self.partition}:ecs:{self.region}:{self.account}:cluster/{self.params.cluster_name}-ad-sync-cluster",
                        }
                    },
                },
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:PassRole",
                    ],
                    "Resource": f"arn:{self.partition}:iam::{self.account}:role/{self.params.cluster_name}-ad-sync-task-role",
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:DescribeSecurityGroups",
                        "ec2:DeregisterImage",
                        "ec2:DescribeInstances",
                    ],
                    "Resource": "*",
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:GetFunctionConfiguration",
                        "lambda:UpdateFunctionConfiguration",
                    ],
                    "Resource": f"arn:{self.partition}:lambda:{self.region}:{self.account}:function:{self.params.cluster_name}-backend-lambda",
                }
            ),
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeImages",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "secretsmanager:ResourceTag/res:EnvironmentName": self.params.cluster_name,
                        "secretsmanager:ResourceTag/res:ModuleName": [
                            "cluster-manager",
                        ],
                    }
                },
            ),
        ]

    def _infra_validation_role_policy_statements(self) -> list[iam.PolicyStatement]:
        """
        Describe-only IAM policy statements for the Tier 0 infra_validation tests
        (resource tagging, S3 logging/SSL policy, DynamoDB PITR).
        """
        return [
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "tag:GetResources",
                        "s3:GetBucketLogging",
                        "s3:GetBucketPolicy",
                        "dynamodb:ListTables",
                        "dynamodb:DescribeContinuousBackups",
                    ],
                    "Resource": "*",
                }
            ),
        ]

    def _smoke_role_policy_statements(self) -> list[iam.PolicyStatement]:
        """
        IAM policy statements the smoke tests need beyond the API test set,
        required by the nightly/release suites that run the full smoke matrix.
        """
        return [
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:UpdateItem",
                    ],
                    "Resource": [
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.cluster-settings",
                    ],
                }
            ),
            # VDI idle/schedule tests need to create and delete schedule entries
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:DeleteItem",
                    ],
                    "Resource": [
                        f"arn:{self.partition}:dynamodb:{self.region}:{self.account}:table/{self.params.cluster_name}.vdc.controller.schedules",
                    ],
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
                        "secretsmanager:GetSecretValue",
                    ],
                    # Secret name suffixes are auto-generated by CloudFormation and
                    # not predictable at pipeline-definition time.
                    "Resource": f"arn:{self.partition}:secretsmanager:{self.region}:{self.account}:secret:{self.params.cluster_name}/*",
                }
            ),
            # Lambda invoke for VDI enforce-schedule test
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction",
                    ],
                    "Resource": f"arn:{self.partition}:lambda:{self.region}:{self.account}:function:{self.params.cluster_name}-vdc-scheduled-event-handler",
                }
            ),
            # S3 read/write for testing infra buckets (seed files, mount verification)
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:DeleteObject",
                    ],
                    "Resource": f"arn:{self.partition}:s3:::{self.params.cluster_name}-integ-test-s3-*/*",
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:ListBucket",
                    ],
                    "Resource": f"arn:{self.partition}:s3:::{self.params.cluster_name}-integ-test-s3-*",
                }
            ),
        ]

    def _cognito_fixture_role_policy_statements(self) -> list[iam.PolicyStatement]:
        """
        IAM permissions for the cognito_non_admin test fixture, which creates
        and deletes native Cognito pool users + triggers cognito_sync.
        """
        return [
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "cognito-idp:AdminCreateUser",
                        "cognito-idp:AdminSetUserPassword",
                        "cognito-idp:AdminDeleteUser",
                    ],
                    "Resource": f"arn:{self.partition}:cognito-idp:{self.region}:{self.account}:userpool/*",
                }
            ),
            iam.PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction",
                    ],
                    "Resource": f"arn:{self.partition}:lambda:{self.region}:{self.account}:function:{self.params.cluster_name}-cognito-sync-lambda",
                }
            ),
        ]

    def get_suite_test_step(self, suite: str) -> pipelines.CodeBuildStep:
        """
        Build the integration test step for the given suite (dev/nightly/release),
        invoking `integ-tests.<suite>`. All suites reuse the API test IAM policies.
        Per suite:
          - dev additionally needs describe-only permissions for its Tier 0
            infra_validation checks and Cognito fixture permissions.
          - nightly/release run the full smoke matrix (the standalone smoke step
            only runs in the per-commit dev pipeline), so they additionally need
            the smoke tests' write/SSM/secret permissions + Cognito fixture.
        """
        policy_statements = list(self._api_test_role_policy_statements())
        if suite == "dev":
            policy_statements += self._infra_validation_role_policy_statements()
            policy_statements += self._cognito_fixture_role_policy_statements()
        if suite in ("nightly", "release"):
            policy_statements += self._smoke_role_policy_statements()
            policy_statements += self._cognito_fixture_role_policy_statements()

        # nightly/release run Chrome-based smoke tests across 22 parallel workers;
        # LARGE matches the standalone smoke step's compute (Chrome OOMs on SMALL).
        compute = (
            codebuild.ComputeType.LARGE
            if suite in ("nightly", "release")
            else codebuild.ComputeType.SMALL
        )

        step = (
            IntegTestStepBuilder(
                f"integ-tests.{suite}",
                self.params.cluster_name,
                self.region,
                compute_type=compute,
            )
            .test_specific_role_policy_statement(*policy_statements)
            .build()
        )

        return step

    def get_ad_sync_integ_test_step(self) -> pipelines.CodeBuildStep:
        step = (
            IntegTestStepBuilder(
                "integ-tests.ad-sync",
                self.params.cluster_name,
                self.region,
                requires_alb=False,
            )
            .test_specific_install_command(
                *get_commands_for_scripts(
                    ["source/idea/ad-sync/tests/integration/scripts/run_slapd.sh"]
                ),
                # Allow communication with the local AD
                "echo '127.0.0.1       corp.res.com' | sudo tee -a /etc/hosts",
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

    @staticmethod
    def get_steps_for_unit_tests(test_env: list[str]) -> list[pipelines.CodeBuildStep]:
        steps: list[pipelines.CodeBuildStep] = []
        for _env in test_env:
            _step = pipelines.CodeBuildStep(
                _env,
                install_commands=get_commands_for_scripts(
                    [
                        "source/idea/pipeline/scripts/common/install_commands.sh",
                        "source/idea/pipeline/scripts/unit_tests/install_commands.sh",
                        "source/idea/pipeline/scripts/unit_tests/commands.sh",
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
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/Deploy-{TESTING_INFRA_STACK_NAME}/*",
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
                f"arn:{self.partition}:cloudformation:{self.region}:{self.account}:stack/Deploy-{TESTING_INFRA_STACK_NAME}/*",
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
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
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
                TESTING_INFRA_INCLUDED=(
                    "true" if self._testing_infra_included else "false"
                ),
                VPC_ID=self.params.vpc_id,
                INSTALL_STACK_NAME=INSTALL_STACK_NAME,
                BATTERIES_INCLUDED_STACK_NAME=f"Deploy-{BATTERIES_INCLUDED_STACK_NAME}",
                TESTING_INFRA_INCLUDED_STACK_NAME=f"Deploy-{TESTING_INFRA_STACK_NAME}",
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
        self, ecr_public_repository_name: str, staging_bucket_name: str
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
        staging_bucket_read_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObjectTagging",
                "s3:getBucketLocation",
                "s3:ListBucket",
                "s3:GetObject",
            ],
            resources=[
                f"arn:{self.partition}:s3:::{self.staging_bucket_name}",
                f"arn:{self.partition}:s3:::{self.staging_bucket_name}/*",
            ],
        )
        public_bucket_write_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:PutObject",
                "s3:GetObjectTagging",
                "s3:GetBucketLocation",
                "s3:ListBucket",
                "s3:GetObject",
            ],
            resources=[
                f"arn:{self.partition}:s3:::{ARTIFACTS_BUCKET_PREFIX_NAME}-*",
            ],
        )
        return pipelines.CodeBuildStep(
            "Publish templates and docker image",
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
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
                STAGING_BUCKET_NAME=staging_bucket_name,
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
                staging_bucket_read_access,
                public_bucket_write_access,
            ],
        )

    def get_latest_bucket_refresh_steps(self) -> pipelines.CodeBuildStep:
        codebuild_s3_all_access = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:PutObject",
                "s3:GetObjectTagging",
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
        parameters: Union[RESParameters, BIParameters, IsolatedVpcParameters],
        staging_bucket_name: str = "",
    ):
        super().__init__(scope, construct_id)
        ad_sync_registry_name = self.node.try_get_context("ad_sync_registry_name")

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
            parameters=parameters,  # type: ignore[arg-type]  # IsolatedVpcParameters is structurally compatible with RESParameters
            staging_bucket_name=staging_bucket_name,
            ad_sync_registry_name=ad_sync_registry_name,
        )
        if self.batteries_included_stack:
            self.install_stack.add_dependency(target=self.batteries_included_stack)

        # Isolated VPC infrastructure (endpoints + proxy server).
        # Testing infrastructure (storage systems for integration tests).
        # Only deployed when `-c testing_infra_included=true` is set.
        self.testing_infra_stack = None
        testing_infra_included = self.node.try_get_context("testing_infra_included")
        if testing_infra_included and str(testing_infra_included).lower() == "true":
            efs_template_url = self.node.try_get_context("AmazonEFSTemplateURL") or ""
            fsx_lustre_url = (
                self.node.try_get_context("AmazonFSxForLustreTemplateURL") or ""
            )
            fsx_ontap_url = (
                self.node.try_get_context("AmazonFSxForONTAPTemplateURL") or ""
            )

            template_urls = StorageTemplateUrls(
                efs=efs_template_url,
                fsx_lustre=fsx_lustre_url,
                fsx_ontap=fsx_ontap_url,
            )

            # Get AD parameters from BI stack if available (for ONTAP domain join)
            # AD join for ONTAP is gated behind `-c ontap_ad_join=true` because
            # it requires the AD controller SG to allow VPC traffic (manual step).
            ad_params = None
            ontap_ad_join = self.node.try_get_context("ontap_ad_join")
            if ontap_ad_join and str(ontap_ad_join).lower() == "true":
                if self.batteries_included_stack:
                    # Read AD params from BI stack outputs
                    bi = self.batteries_included_stack.bi_stack
                    ad_params = {
                        "ActiveDirectoryName": bi.get_att(
                            "Outputs.ActiveDirectoryName"
                        ).to_string(),
                        "DNSServerIPs": bi.get_att(
                            "Outputs.ActiveDirectoryDNSIPs"
                        ).to_string(),
                        "ServiceAccountCredentialsSecretArn": bi.get_att(
                            "Outputs.ServiceAccountCredentialsSecretArn"
                        ).to_string(),
                        "ComputersOU": bi.get_att("Outputs.ComputersOU").to_string(),
                    }
                else:
                    # Read AD params from pipeline parameters.
                    # If use_bi_parameters_from_ssm, all values resolve from SSM.
                    # Otherwise they're direct values and ADDnsIPs from context.
                    if use_bi_parameters_from_ssm:
                        dns_ips_ssm_path = (
                            f"/{parameters.cluster_name}/external/ADDnsIPs"
                        )
                        ad_params = {
                            "ActiveDirectoryName": f"{{{{resolve:ssm:{parameters.name}}}}}",
                            "DNSServerIPs": f"{{{{resolve:ssm:{dns_ips_ssm_path}}}}}",
                            "ServiceAccountCredentialsSecretArn": f"{{{{resolve:ssm:{parameters.service_account_credentials_secret_arn}}}}}",
                            "ComputersOU": f"{{{{resolve:ssm:{parameters.computers_ou}}}}}",
                        }
                    else:
                        ad_dns_ips = self.node.try_get_context("ADDnsIPs") or ""
                        ad_params = {
                            "ActiveDirectoryName": str(parameters.name),
                            "DNSServerIPs": ad_dns_ips,
                            "ServiceAccountCredentialsSecretArn": str(
                                parameters.service_account_credentials_secret_arn
                            ),
                            "ComputersOU": str(parameters.computers_ou),
                        }

            self.testing_infra_stack = TestingInfraStack(
                self,
                TESTING_INFRA_STACK_NAME,
                parameters=parameters,  # type: ignore[arg-type]  # IsolatedVpcParameters is structurally compatible with RESParameters
                template_urls=template_urls,
                ad_params=ad_params,
            )
            # Testing infra depends on install stack (needs VPC/SG to exist)
            self.testing_infra_stack.add_dependency(self.install_stack)
