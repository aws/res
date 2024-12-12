#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import importlib.metadata
import os
import pathlib
import shutil
from typing import Any, List, Optional, Set, Union

import aws_cdk
from aws_cdk import Environment, IStackSynthesizer, Stack
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from constructs import Construct, DependencyGroup

import idea
from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import installer
from idea.infrastructure.install.backend import BastionHostCleanup
from idea.infrastructure.install.constants import (
    API_PROXY_LAMBDA_LAYER_NAME,
    RES_ADMINISTRATOR_LAMBDA_RUNTIME,
    RES_BACKEND_LAMBDA_RUNTIME,
    RES_COMMON_LAMBDA_RUNTIME,
    RES_ECR_REPO_NAME_SUFFIX,
    SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME,
)
from idea.infrastructure.install.handlers import ecr_images_handler
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import (
    AllRESParameterGroups,
    RESParameters,
)
from idea.infrastructure.install.stacks.ad_sync_stack import ADSyncStack
from idea.infrastructure.install.stacks.res_base_stack import ResBaseStack
from idea.infrastructure.install.stacks.res_finalizer_stack import ResFinalizerStack
from idea.infrastructure.install.utils import InfraUtils

PUBLIC_REGISTRY_NAME = (
    "public.ecr.aws/i4h1n0f0/idea-administrator:v3.0.0-pre-alpha-feature"
)


class InstallStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
        installer_registry_name: Optional[str] = None,
        ad_sync_registry_name: Optional[str] = None,
        env: Union[Environment, dict[str, Any], None] = None,
        synthesizer: Optional[IStackSynthesizer] = None,
    ):
        super().__init__(
            scope,
            stack_id,
            env=env,
            synthesizer=synthesizer,
            description=f"RES_{importlib.metadata.version(idea.__package__)}",
        )

        self.parameters = parameters
        self.parameters.generate(self)
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.template_options.metadata = AllRESParameterGroups.template_metadata()
        self.installer_registry_name = (
            installer_registry_name
            if installer_registry_name is not None
            else PUBLIC_REGISTRY_NAME
        )
        self.ad_sync_registry_name = (
            ad_sync_registry_name
            if ad_sync_registry_name is not None
            else PUBLIC_REGISTRY_NAME
        )
        self.lambda_layers = {}

        # Create a Lambda layer version from the local requirements file
        self.lambda_layers[API_PROXY_LAMBDA_LAYER_NAME] = lambda_.LayerVersion(
            self,
            id="ApiProxyDepsLayer",
            code=lambda_.Code.from_asset(
                "source/idea/infrastructure/install/lambda_layers",
                bundling=aws_cdk.BundlingOptions(
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output",
                    ],
                    image=RES_COMMON_LAMBDA_RUNTIME.bundling_image,
                    output_type=aws_cdk.BundlingOutput.AUTO_DISCOVER,
                ),
            ),
            compatible_runtimes=[RES_COMMON_LAMBDA_RUNTIME],
            description="Lambda layer with Python dependencies",
        )

        self.parameters.load_balancer_subnets_string = aws_cdk.Fn.join(
            ",", self.parameters.get(CommonKey.LOAD_BALANCER_SUBNETS).value_as_list
        )

        self.parameters.infrastructure_host_subnets_string = aws_cdk.Fn.join(
            ",",
            self.parameters.get(CommonKey.INFRASTRUCTURE_HOST_SUBNETS).value_as_list,
        )

        self.parameters.dcv_session_private_subnets_string = aws_cdk.Fn.join(
            ",", self.parameters.get(CommonKey.VDI_SUBNETS).value_as_list
        )

        # List parameters cannot be passed to nested stack
        # Transform them to String before parsing
        self.params_transformer = self.get_param_list_to_string_custom_resource()

        self.lambda_layers[SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME] = (
            self.create_shared_res_library_lambda_layer()
        )
        self.res_base_stack = ResBaseStack(
            self,
            self.lambda_layers[SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME],
            self.params_transformer,
            self.parameters,
        )
        self.res_base_stack.nested_stack.node.add_dependency(self.params_transformer)

        dependency_group = DependencyGroup()
        dependency_group.add(self.res_base_stack.nested_stack)
        dependency_group.add(self.lambda_layers[SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME])

        self.res_ecr_repo = self.create_res_ecr_repo()
        ecr_images_handler_lambda = self.create_ecr_images_handler()
        dependency_group.add(ecr_images_handler_lambda)

        self.ad_sync_stack = ADSyncStack(
            self,
            lambda_layer=self.lambda_layers[SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME],
            parameters=parameters,
            registry_name=self.get_private_registry_name(self.ad_sync_registry_name),
        )
        self.ad_sync_stack.nested_stack.node.add_dependency(ecr_images_handler_lambda)
        self.ad_sync_stack.nested_stack.node.add_dependency(
            self.res_base_stack.nested_stack
        )

        self.bastionHostCleanup = BastionHostCleanup(
            self,
            "remove-leftover-bastion-host-resource",
            parameters.get_str(CommonKey.CLUSTER_NAME),
        )
        self.bastionHostCleanup.node.add_dependency(self.res_base_stack)

        self.installer = installer.Installer(
            self,
            "Installer",
            registry_name=self.get_private_registry_name(self.installer_registry_name),
            params=self.parameters,
            dependency_group=dependency_group,
            lambda_layers=self.lambda_layers,
        )

        self.res_finalizer_stack = ResFinalizerStack(
            self,
            self.lambda_layers[SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME],
            self.parameters,
        )

        self.res_finalizer_stack.nested_stack.node.add_dependency(self.installer)
        self.attach_permission_boundaries()

    def create_shared_res_library_lambda_layer(self) -> lambda_.LayerVersion:
        # Copy requirements file and lambda library tar file to docker directory
        library_lib_tar_file = "library-lib.tar.gz"
        library_requirements_file = "requirements.txt"
        library_path = str(
            next(
                pathlib.Path("source")
                .parent.joinpath("dist")
                .glob("library*[!.tar.gz]"),
                "",
            )
        )
        file_path = os.path.realpath(__file__)
        dockerfile_path = str(
            pathlib.Path(file_path).parent.parent.joinpath("library_lambda_layer")
        )
        shutil.copyfile(
            library_path + "/" + library_lib_tar_file,
            dockerfile_path + "/" + library_lib_tar_file,
        )
        shutil.copyfile(
            library_path + "/" + library_requirements_file,
            dockerfile_path + "/" + library_requirements_file,
        )

        shared_library_layer = lambda_.LayerVersion(
            self,
            "RES-library",
            code=lambda_.Code.from_docker_build(
                path=dockerfile_path,
                build_args={
                    "LIBRARY_TAR_FILE": library_lib_tar_file,
                    "LIBRARY_REQUIREMENTS_FILE": library_requirements_file,
                },
            ),
            compatible_runtimes=[
                RES_ADMINISTRATOR_LAMBDA_RUNTIME,
                RES_COMMON_LAMBDA_RUNTIME,
                RES_BACKEND_LAMBDA_RUNTIME,
            ],
            description="Shared RES library for Lambda functions",
        )

        # Remove copied files
        os.remove(dockerfile_path + "/" + library_requirements_file)
        os.remove(dockerfile_path + "/" + library_lib_tar_file)

        return shared_library_layer

    def attach_permission_boundaries(self) -> None:
        # Determine if IAMPermissionBoundary ARN input was provided in CFN.
        permission_boundary_provided = aws_cdk.CfnCondition(
            self,
            "PermissionBoundaryProvided",
            expression=aws_cdk.Fn.condition_not(
                aws_cdk.Fn.condition_equals(
                    aws_cdk.Fn.ref(CommonKey.IAM_PERMISSION_BOUNDARY), ""
                )
            ),
        )
        permission_boundary_policy = iam.ManagedPolicy.from_managed_policy_arn(
            self,
            "PermissionBoundaryPolicy",
            aws_cdk.Fn.condition_if(
                permission_boundary_provided.logical_id,
                self.parameters.get(CommonKey.IAM_PERMISSION_BOUNDARY),
                aws_cdk.Aws.NO_VALUE,
            ).to_string(),
        )
        iam.PermissionsBoundary.of(self).apply(permission_boundary_policy)

    def create_res_ecr_repo(self) -> ecr.Repository:
        repository = ecr.Repository(
            self,
            "ResEcrRepo",
            repository_name=f"{self.cluster_name}{RES_ECR_REPO_NAME_SUFFIX}",
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )
        repository.grant_push(
            iam.Role(
                self,
                "ResEcrPush",
                assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            )
        )
        repository.grant_pull(
            iam.Role(
                self,
                "ResEcrPull",
                assumed_by=iam.ServicePrincipal("ecs.amazonaws.com"),
            )
        )

        return repository

    def create_ecr_images_handler(self) -> aws_cdk.CustomResource:
        project = self.create_ecr_image_duplication_project()

        ecr_image_handler_role = iam.Role(
            self,
            id="EcrImageHandlerRole",
            role_name=f"{self.parameters.get_str(CommonKey.CLUSTER_NAME)}-ecr-image-handler-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        ecr_image_handler_role_policy = iam.Policy(
            self,
            id="EcrImageHandlerRolePolicy",
            policy_name=f"{self.parameters.get_str(CommonKey.CLUSTER_NAME)}-custom-resource-ecr-image-handler-role-policy",
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
                        "codebuild:StartBuild",
                        "codebuild:BatchGetBuilds",
                    ],
                    resources=[project.project_arn],
                ),
                iam.PolicyStatement(
                    actions=[
                        "ecr:ListImages",
                        "ecr:BatchDeleteImage",
                    ],
                    resources=[self.res_ecr_repo.repository_arn],
                ),
            ],
        )
        ecr_image_handler_role.attach_inline_policy(ecr_image_handler_role_policy)

        event_handler = lambda_.Function(
            self,
            "EcrImageHandler",
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            timeout=aws_cdk.Duration.seconds(300),
            role=ecr_image_handler_role,
            description="Lambda to handle the code build events",
            **InfraUtils.get_handler_and_code_for_function(
                ecr_images_handler.handle_request
            ),
        )
        event_handler.node.add_dependency(ecr_image_handler_role_policy)
        event_handler.node.add_dependency(project)

        return aws_cdk.CustomResource(
            self,
            "CustomResourceEcrImageHandler",
            service_token=event_handler.function_arn,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::RES",
            properties={
                "ProjectName": project.project_name,
                "ResEcrRepositoryName": self.res_ecr_repo.repository_name,
                # Add the installer and AD Sync registry name to properties to make sure that
                # the custom resource can be triggered whenever the registry names are updated
                "InstallerRegistryName": self.installer_registry_name,
                "ADSyncRegistryName": self.ad_sync_registry_name,
            },
        )

    def create_ecr_image_duplication_project(self) -> codebuild.Project:
        commands: List[str] = []
        resources: Set[str] = {self.res_ecr_repo.repository_arn}
        self.process_ecr_image_duplication_request(
            self.installer_registry_name,
            "${DEST_INSTALLER_REGISTRY}",
            resources,
            commands,
        )
        self.process_ecr_image_duplication_request(
            self.ad_sync_registry_name,
            "${DEST_AD_SYNC_REGISTRY}",
            resources,
            commands,
        )

        project = codebuild.Project(
            self,
            "CopyImagesToRESEcr",
            project_name=aws_cdk.Fn.join(
                "-",
                [
                    self.cluster_name,
                    "copy-images-to-res-ecr",
                ],
            ),
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "build": {
                            "commands": [
                                *commands,
                            ]
                        }
                    },
                }
            ),
            environment_variables={
                "AWS_REGION": codebuild.BuildEnvironmentVariable(
                    value=aws_cdk.Aws.REGION
                ),
                "DEST_INSTALLER_REGISTRY": codebuild.BuildEnvironmentVariable(
                    value=self.get_private_registry_name(self.installer_registry_name)
                ),
                "DEST_AD_SYNC_REGISTRY": codebuild.BuildEnvironmentVariable(
                    value=self.get_private_registry_name(self.ad_sync_registry_name)
                ),
                "RES_REPO_URI": codebuild.BuildEnvironmentVariable(
                    value=self.res_ecr_repo.repository_uri
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
            resources=list(resources),
        )
        project.add_to_role_policy(access_policy)

        return project

    def process_ecr_image_duplication_request(
        self,
        source_registry_name: str,
        dest_registry_name: str,
        resources: Set[str],
        commands: List[str],
    ) -> None:
        source_repo_uri = source_registry_name.split(":")[0]

        if not source_registry_name.startswith("public"):
            resources.add(
                self.get_ecr_repo_arn_from_registry_name(source_registry_name)
            )
            commands.append(
                f"aws ecr get-login-password --region ${{AWS_REGION}} | docker login --username AWS --password-stdin {source_repo_uri}"
            )

        commands.extend(
            [
                f"docker pull {source_registry_name}",
                f"docker tag {source_registry_name} {dest_registry_name}",
                f"aws ecr get-login-password --region ${{AWS_REGION}} | docker login --username AWS --password-stdin ${{RES_REPO_URI}}",
                f"docker push {dest_registry_name}",
            ]
        )

    def get_private_registry_name(self, registry_name: str) -> str:
        """
        Get the registry name in the RES private ECR repository
        """
        return aws_cdk.Fn.join(
            ":",
            [self.res_ecr_repo.repository_uri, registry_name.split(":")[-1]],
        )

    def get_param_list_to_string_custom_resource(self) -> aws_cdk.CustomResource:
        """
        Create a lambda function to transform the parameters from list to string for the nested stacks
        """
        role = iam.Role(
            self,
            id="ParameterListToStringTransformLambdaRole",
            role_name=f"{self.cluster_name}-ParameterListToStringTransformLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        role_policy = iam.Policy(
            self,
            id="ParameterListToStringTransformLambdaRolePolicy",
            policy_name=f"{self.cluster_name}-ParameterListToStringTransformLambdaRolePolicy",
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
            ],
        )
        role.attach_inline_policy(role_policy)

        params_transformer_handler = lambda_.Function(
            self,
            id="ParameterListToStringTransformLambda",
            function_name=f"{self.cluster_name}-ParameterListToStringTransformLambda",
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            timeout=aws_cdk.Duration.seconds(300),
            role=role,
            handler="lambda_functions.custom_resource.parameter_list_to_string_transform_lambda.handler.handler",
            description="Lambda to transform the parameters from list to string for nested stack",
            code=lambda_.Code.from_asset(InfraUtils.resources_dir()),
            environment={
                "LOAD_BALANCER_SUBNETS": self.parameters.load_balancer_subnets_string
                or "",
                "INFRA_SUBNETS": self.parameters.infrastructure_host_subnets_string
                or "",
                "VDI_SUBNETS": self.parameters.dcv_session_private_subnets_string or "",
            },
        )

        custom_resource = aws_cdk.CustomResource(
            self,
            "CustomResourceParamsListToStringTransformer",
            service_token=params_transformer_handler.function_arn,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::ParamsListToStringTransformer",
        )
        return custom_resource

    @staticmethod
    def get_ecr_repo_arn_from_registry_name(registry_name: str) -> str:
        """
        Get the ECR repo ARN from the registry name
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
