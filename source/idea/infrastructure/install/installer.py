#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from typing import Dict, TypedDict, Union

import aws_cdk
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks
from constructs import Construct, DependencyGroup

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import tasks
from idea.infrastructure.install.constants import (
    API_PROXY_LAMBDA_LAYER_NAME,
    INSTALLER_ECR_REPO_NAME_SUFFIX,
    RES_COMMON_LAMBDA_RUNTIME,
    SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME,
)
from idea.infrastructure.install.handlers import installer_handlers
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.proxy import (
    LambdaAndSecurityGroupCleanup,
    Proxy,
    proxy_lambda_name,
    proxy_lambda_security_group_name,
)
from idea.infrastructure.install.utils import InfraUtils

LAMBDA_RUNTIME = lambda_.Runtime.PYTHON_3_11


class LambdaCodeParams(TypedDict):
    handler: str
    code: lambda_.Code


class Installer(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        registry_name: str,
        params: Union[RESParameters, BIParameters],
        dependency_group: DependencyGroup,
        lambda_layers: Dict[str, lambda_.LayerVersion],
    ):
        super().__init__(scope, id)
        self.params = params
        self.registry_name = registry_name
        self.installer_ecr_repo = self.create_installer_ecr_repo()
        installer_registry_name = self.get_installer_registry_name()
        self.installer_ecr_repo.grant_push(
            iam.Role(
                self,
                "InstallerEcrPush",
                assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            )
        )
        self.installer_ecr_repo.grant_pull(
            iam.Role(
                self,
                "InstallerEcrPull",
                assumed_by=iam.ServicePrincipal("ecs.amazonaws.com"),
            )
        )
        event_handler = lambda_.Function(
            self,
            "CustomResourceEventHandler",
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            timeout=aws_cdk.Duration.seconds(10),
            description="Lambda to handle the CFN custom resource events",
            **InfraUtils.get_handler_and_code_for_function(
                installer_handlers.handle_custom_resource_lifecycle_event
            ),
        )
        wait_condition_handle = aws_cdk.CfnWaitConditionHandle(
            self, f"InstallerWaitConditionHandle{self.get_wait_condition_suffix()}"
        )

        self.params.load_balancer_subnets_string = aws_cdk.Fn.join(
            ",", self.params.get(CommonKey.LOAD_BALANCER_SUBNETS).value_as_list
        )

        self.params.infrastructure_host_subnets_string = aws_cdk.Fn.join(
            ",", self.params.get(CommonKey.INFRASTRUCTURE_HOST_SUBNETS).value_as_list
        )

        self.params.dcv_session_private_subnets_string = aws_cdk.Fn.join(
            ",", self.params.get(CommonKey.VDI_SUBNETS).value_as_list
        )

        cluster_name = self.params.get_str(CommonKey.CLUSTER_NAME)
        self.proxyConstructCleanup = LambdaAndSecurityGroupCleanup(
            self,
            "remove-leftover-proxy-resource",
            self.params.get_str(CommonKey.VPC_ID),
            [f"{cluster_name}_{proxy_lambda_name}"],
            [f"{cluster_name}_{proxy_lambda_security_group_name}"],
        )

        installer = aws_cdk.CustomResource(
            self,
            "Installer",
            service_token=event_handler.function_arn,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::RES",
            properties={
                installer_handlers.EnvKeys.CALLBACK_URL: wait_condition_handle.ref,
                installer_handlers.EnvKeys.INSTALLER_ECR_REPO_NAME: aws_cdk.Fn.join(
                    "",
                    [
                        self.params.get_str(CommonKey.CLUSTER_NAME),
                        INSTALLER_ECR_REPO_NAME_SUFFIX,
                    ],
                ),
                installer_handlers.EnvKeys.ENVIRONMENT_NAME: self.params.get_str(
                    CommonKey.CLUSTER_NAME
                ),
            },
        )

        # This ensures clean up is done after the installer finishes at stack deletion
        # which gives Lambda more time to clean up the left over ENIs
        installer.node.add_dependency(self.proxyConstructCleanup)

        wait_condition = aws_cdk.CfnWaitCondition(
            self,
            f"InstallerWaitCondition{self.get_wait_condition_suffix()}",
            count=1,
            timeout=str(aws_cdk.Duration.hours(2).to_seconds()),
            handle=wait_condition_handle.ref,
        )
        wait_condition.node.add_dependency(installer)

        self.proxyLambda = Proxy(
            self,
            "AWSProxy",
            {
                "target_group_priority": 101,
                "ddb_users_table_name": f"{cluster_name}.accounts.users",
                "ddb_groups_table_name": f"{cluster_name}.accounts.groups",
                "ddb_cluster_settings_table_name": f"{cluster_name}.cluster-settings",
                "cluster_name": cluster_name,
            },
            lambda_layer=lambda_layers[API_PROXY_LAMBDA_LAYER_NAME],
        )
        # Add wait condition as dependency ensures it deploys after ECS deployment is completed
        self.proxyLambda.node.add_dependency(wait_condition)

        self.tasks = tasks.Tasks(
            self,
            "Tasks",
            registry_name=self.registry_name,
            installer_registry_name=installer_registry_name,
            params=params,
            dependency_group=dependency_group,
            lambda_layer_arn=lambda_layers[
                SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME
            ].layer_version_arn,
        )

        state_machine = self.get_state_machine()
        state_machine.node.add_dependency(self.installer_ecr_repo)
        state_machine.grant_start_execution(event_handler)
        event_handler.add_environment(
            key=installer_handlers.EnvKeys.SFN_ARN,
            value=state_machine.state_machine_arn,
        )

        dependency_group.add(state_machine)
        installer.node.add_dependency(dependency_group)

    def get_installer_registry_name(self) -> str:
        """
        Provided resitry name of the format: public.ecr.aws/<text1>/<text2>:<image_tag>

        Use the same image_tag for the installer repository:
            If the installer repository URI is of the form  <account>.dkr.ecr.<region>.amazonaws.com/<installer-repo-name>
            Image would be <account>.dkr.ecr.<region>.amazonaws.com/<installer-repo-name>:<image_tag>
        """
        return aws_cdk.Fn.join(
            ":",
            [self.installer_ecr_repo.repository_uri, self.registry_name.split(":")[-1]],
        )

    def create_installer_ecr_repo(self) -> ecr.Repository:
        return ecr.Repository(
            self,
            "InstallerEcrRepo",
            repository_name=f"{self.params.get_str(CommonKey.CLUSTER_NAME)}{INSTALLER_ECR_REPO_NAME_SUFFIX}",
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
        )

    def get_wait_condition_suffix(self) -> str:
        return str(int(datetime.now().timestamp()))

    def get_state_machine(self) -> sfn.StateMachine:
        request_type_choice = sfn.Choice(self, "SwitchByEventType")

        resource_signaler = lambda_.Function(
            self,
            "WaitConditionResponseSender",
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            timeout=aws_cdk.Duration.seconds(10),
            description="Lambda to send response using the wait condition callback",
            **InfraUtils.get_handler_and_code_for_function(
                installer_handlers.send_wait_condition_response
            ),
        )

        send_cfn_response_task = sfn_tasks.LambdaInvoke(
            self,
            "SendCfnResponse",
            lambda_function=resource_signaler,
            payload_response_only=True,
        )

        send_cfn_response_task.add_retry()

        codebuild_task = self.tasks.get_installer_ecr_pull_image_task()
        create_task = self.tasks.get_create_task()
        update_task = self.tasks.get_update_task()
        delete_task = self.tasks.get_delete_task()
        cognito_unprotect_task = self.tasks.get_cognito_user_pool_unprotect_task()
        installer_ecr_images_delete_task = (
            self.tasks.get_installer_ecr_images_delete_task()
        )

        for task in (
            codebuild_task,
            create_task,
            update_task,
            delete_task,
            installer_ecr_images_delete_task,
            cognito_unprotect_task,
        ):
            task.add_catch(
                handler=send_cfn_response_task,
                result_path=f"$.{installer_handlers.EnvKeys.ERROR}",
            )

        request_type_choice.when(
            sfn.Condition.string_equals(
                "$.RequestType", installer_handlers.RequestType.CREATE
            ),
            codebuild_task,
        ).when(
            sfn.Condition.string_equals(
                "$.RequestType", installer_handlers.RequestType.UPDATE
            ),
            codebuild_task,
        ).when(
            sfn.Condition.string_equals(
                "$.RequestType", installer_handlers.RequestType.DELETE
            ),
            cognito_unprotect_task,
        ).otherwise(
            sfn.Fail(self, "UnknownRequestType")
        )

        request_type_choice_post_codebuild = sfn.Choice(
            self, "SwitchByEventTypePostCodeBuild"
        )
        request_type_choice_post_codebuild.when(
            sfn.Condition.string_equals(
                "$.RequestType", installer_handlers.RequestType.CREATE
            ),
            create_task,
        ).when(
            sfn.Condition.string_equals(
                "$.RequestType", installer_handlers.RequestType.UPDATE
            ),
            update_task,
        ).otherwise(
            sfn.Fail(self, "UnknownRequestTypePostCodebuild")
        )
        cognito_unprotect_task.next(delete_task)
        codebuild_task.next(request_type_choice_post_codebuild)
        create_task.next(send_cfn_response_task)
        update_task.next(send_cfn_response_task)
        delete_task.next(installer_ecr_images_delete_task)
        installer_ecr_images_delete_task.next(send_cfn_response_task)

        return sfn.StateMachine(
            self,
            "InstallerStateMachine",
            definition=sfn.Chain.start(request_type_choice),
        )
