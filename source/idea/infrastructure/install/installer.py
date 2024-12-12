#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from datetime import datetime
from typing import Dict, TypedDict, Union

import aws_cdk
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks
from constructs import Construct, DependencyGroup

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import tasks
from idea.infrastructure.install.backend import (
    BackendLambda,
    backend_lambda_name,
    backend_lambda_security_group_name,
)
from idea.infrastructure.install.cognito_sync_lambda import (
    CognitoSyncLambda,
    cognito_sync_lambda_name,
    cognito_sync_lambda_security_group_name,
)
from idea.infrastructure.install.cognito_trigger_workflow import (
    CognitoTriggerWorkflow,
    cognito_trigger_workflow_lambda_name,
    cognito_trigger_workflow_lambda_security_group_name,
)
from idea.infrastructure.install.constants import (
    API_PROXY_LAMBDA_LAYER_NAME,
    RES_COMMON_LAMBDA_RUNTIME,
    RES_ECR_REPO_NAME_SUFFIX,
    SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME,
)
from idea.infrastructure.install.handlers import installer_handlers
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
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

        cluster_name = self.params.get_str(CommonKey.CLUSTER_NAME)

        self.lambdaConstructCleanup = LambdaAndSecurityGroupCleanup(
            self,
            "remove-leftover-lambda-and-sg-resources",
            self.params.get_str(CommonKey.VPC_ID),
            [
                f"{cluster_name}_{proxy_lambda_name}",
                f"{cluster_name}_{backend_lambda_name}",
                f"{cluster_name}_{cognito_sync_lambda_name}",
                f"{cluster_name}_uid_{cognito_trigger_workflow_lambda_name}",
                f"{cluster_name}_post_auth_{cognito_trigger_workflow_lambda_name}",
            ],
            [
                f"{cluster_name}_{proxy_lambda_security_group_name}",
                f"{cluster_name}_{backend_lambda_security_group_name}",
                f"{cluster_name}_{cognito_sync_lambda_security_group_name}",
                f"{cluster_name}_uid_{cognito_trigger_workflow_lambda_security_group_name}",
                f"{cluster_name}_post_auth_{cognito_trigger_workflow_lambda_security_group_name}",
            ],
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
                        RES_ECR_REPO_NAME_SUFFIX,
                    ],
                ),
                installer_handlers.EnvKeys.ENVIRONMENT_NAME: self.params.get_str(
                    CommonKey.CLUSTER_NAME
                ),
            },
        )

        # This ensures clean up is done after the installer finishes at stack deletion
        # which gives Lambda more time to clean up the left over ENIs
        installer.node.add_dependency(self.lambdaConstructCleanup)

        wait_condition = aws_cdk.CfnWaitCondition(
            self,
            f"InstallerWaitCondition{self.get_wait_condition_suffix()}",
            count=1,
            timeout=str(aws_cdk.Duration.hours(2).to_seconds()),
            handle=wait_condition_handle.ref,
        )
        wait_condition.node.add_dependency(installer)

        http_proxy = self.params.get_str(InternetProxyKey.HTTP_PROXY)
        https_proxy = self.params.get_str(InternetProxyKey.HTTPS_PROXY)
        no_proxy = self.params.get_str(InternetProxyKey.NO_PROXY)

        self.cognito_sync_lambda = CognitoSyncLambda(
            self,
            "cognito-sync-lambda",
            params,
        )
        self.cognito_sync_lambda.node.add_dependency(wait_condition)

        self.cognito_trigger_workflow = CognitoTriggerWorkflow(
            self, "cognito-trigger-workflow", cluster_name, params
        )
        self.cognito_trigger_workflow.node.add_dependency(wait_condition)

        self.proxyLambda = Proxy(
            self,
            "AWSProxy",
            {
                "target_group_priority": 101,
                "ddb_users_table_name": f"{cluster_name}.accounts.users",
                "ddb_groups_table_name": f"{cluster_name}.accounts.groups",
                "ddb_cluster_settings_table_name": f"{cluster_name}.cluster-settings",
                "cluster_name": cluster_name,
                "http_proxy": http_proxy,
                "https_proxy": https_proxy,
                "no_proxy": no_proxy,
            },
            lambda_layer=lambda_layers[API_PROXY_LAMBDA_LAYER_NAME],
        )
        # Add wait condition as dependency ensures it deploys after ECS deployment is completed
        self.proxyLambda.node.add_dependency(wait_condition)

        self.backendLambda = BackendLambda(
            self,
            "BackendLambda",
            {
                "target_group_priority": 102,
                "cluster_name": self.params.get_str(CommonKey.CLUSTER_NAME),
                "http_proxy": http_proxy,
                "https_proxy": https_proxy,
                "no_proxy": no_proxy,
            },
            lambda_layer=lambda_layers[SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME],
        )
        # Add wait condition as dependency ensures it deploys after ECS deployment is completed
        self.backendLambda.node.add_dependency(wait_condition)

        self.tasks = tasks.Tasks(
            self,
            "Tasks",
            installer_registry_name=self.registry_name,
            params=params,
            dependency_group=dependency_group,
            lambda_layer_arn=lambda_layers[
                SHARED_RES_LIBRARY_LAMBDA_LAYER_NAME
            ].layer_version_arn,
        )

        state_machine = self.get_state_machine()

        state_machine.grant_start_execution(event_handler)
        event_handler.add_environment(
            key=installer_handlers.EnvKeys.SFN_ARN,
            value=state_machine.state_machine_arn,
        )

        dependency_group.add(state_machine)
        installer.node.add_dependency(dependency_group)

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

        create_task = self.tasks.get_create_task()
        update_task = self.tasks.get_update_task()
        delete_task = self.tasks.get_delete_task()
        cognito_unprotect_task = self.tasks.get_cognito_user_pool_unprotect_task()

        for task in (
            create_task,
            update_task,
            delete_task,
            cognito_unprotect_task,
        ):
            task.add_catch(
                handler=send_cfn_response_task,
                result_path=f"$.{installer_handlers.EnvKeys.ERROR}",
            )

        request_type_choice.when(
            sfn.Condition.string_equals(
                "$.RequestType", installer_handlers.RequestType.DELETE
            ),
            cognito_unprotect_task,
        ).when(
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
            sfn.Fail(self, "UnknownRequestType")
        )
        cognito_unprotect_task.next(delete_task)

        create_task.next(send_cfn_response_task)
        update_task.next(send_cfn_response_task)
        delete_task.next(send_cfn_response_task)

        return sfn.StateMachine(
            self,
            "InstallerStateMachine",
            definition=sfn.Chain.start(request_type_choice),
        )
