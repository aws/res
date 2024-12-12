#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Any, Optional, Union

from aws_cdk import (
    Aws,
    Duration,
    Environment,
    IStackSynthesizer,
    RemovalPolicy,
    Stack,
    aws_iam,
)
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as lambda_event_sources
from aws_cdk import aws_sqs as sqs
from aws_cdk import custom_resources as cr
from constructs import Construct

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import (
    cognito_trigger_workflow_post_auth_handler,
    cognito_trigger_workflow_uid_handler,
)
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.utils import InfraUtils
from ideadatamodel import (  # type: ignore
    CognitoConstructParams,
    SocaBaseModel,
    constants,
    get_cognito_construct_params,
)

cognito_trigger_workflow_lambda_security_group_name = (
    "cognito-trigger-workflow-lambda-security-group"
)
cognito_trigger_workflow_lambda_name = "cognito-trigger-workflow-lambda"


class CognitoTriggerWorkflow(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        cluster_name: str,
        params: Union[RESParameters, BIParameters],
    ):
        super().__init__(scope, id)
        # Get existing resource
        self.params = params
        self.apply_permission_boundary = InfraUtils.create_permission_boundary_applier(
            self.params
        )

        user_pool_id = InfraUtils.get_cluster_setting_string(
            self, "identity-provider.cognito.user_pool_id", cluster_name
        )

        alb_security_group_id = InfraUtils.get_cluster_setting_string(
            self, "cluster.network.security_groups.external-load-balancer", cluster_name
        )
        vpc_id = InfraUtils.get_cluster_setting_string(
            self, "cluster.network.vpc_id", cluster_name
        )
        subnet_ids = InfraUtils.get_cluster_setting_array(
            self, "cluster.network.private_subnets", cluster_name
        )
        cognito_user_pool_arn = f"arn:{Aws.PARTITION}:cognito-idp:{Aws.REGION}:{Aws.ACCOUNT_ID}:userpool/{user_pool_id}"

        # CREATE NEW RESOURCES
        # SQS queue
        sqs_visibility_timeout = Duration.minutes(5)
        queue = self.create_sqs_queue(scope, cluster_name, sqs_visibility_timeout)

        complete_uid_security_group_name = (
            f"{cluster_name}_uid_{cognito_trigger_workflow_lambda_security_group_name}"
        )
        uid_security_group_id = InfraUtils.create_security_group(
            self, alb_security_group_id, vpc_id, complete_uid_security_group_name, "uid"
        )
        complete_post_auth_security_group_name = f"{cluster_name}_post_auth_{cognito_trigger_workflow_lambda_security_group_name}"
        post_auth_security_group_id = InfraUtils.create_security_group(
            self,
            alb_security_group_id,
            vpc_id,
            complete_post_auth_security_group_name,
            "postauth",
        )

        # POST AUTH LAMBDA
        post_auth_lambda = self.create_post_auth_lambda(
            cluster_name, cognito_user_pool_arn, queue.queue_url, queue.queue_arn
        )

        InfraUtils.add_vpc_config_to_lambda(
            self,
            post_auth_lambda,
            [post_auth_security_group_id],
            subnet_ids,
        )

        self.add_lambdas_as_cognito_trigger(
            cluster_name,
            post_auth_lambda,
            user_pool_id,
        )

        # UID LAMBDA
        uid_lambda = self.create_uid_lambda(
            cluster_name,
            user_pool_id,
            cognito_user_pool_arn,
            queue,
            sqs_visibility_timeout,
        )

        InfraUtils.add_vpc_config_to_lambda(
            self,
            uid_lambda,
            [uid_security_group_id],
            subnet_ids,
            "vpc-config-uid-lambda",
        )

        # Remove SG on CFN delete
        self.remove_ingress_rule_for_alb_sg_on_delete(
            post_auth_security_group_id, alb_security_group_id, "postauth"
        )
        self.remove_ingress_rule_for_alb_sg_on_delete(
            uid_security_group_id, alb_security_group_id, "uid"
        )

    def create_sqs_queue(
        self, scope: Construct, cluster_name: str, visibility_timeout: Duration
    ) -> sqs.Queue:
        dead_letter_queue = sqs.DeadLetterQueue(
            max_receive_count=2,
            queue=sqs.Queue(
                scope,
                "cognito-post-auth-sqs-queue-dlq",
                queue_name=f"{cluster_name}-cognito-post-auth-dlq.fifo",
                fifo=True,
                content_based_deduplication=True,
                encryption=sqs.QueueEncryption.KMS_MANAGED,
            ),
        )

        post_auth_queue = sqs.Queue(
            scope,
            "cognito-post-auth-sqs-queue",
            queue_name=f"{cluster_name}-cognito-post-auth.fifo",
            fifo=True,
            content_based_deduplication=True,
            visibility_timeout=visibility_timeout,
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            dead_letter_queue=dead_letter_queue,
        )

        return post_auth_queue

    def remove_ingress_rule_for_alb_sg_on_delete(
        self, security_group_id: str, alb_security_group_id: str, suffix: str
    ) -> cr.AwsCustomResource:
        remove_ingress_rule = cr.AwsCustomResource(
            self,
            f"RemoveIngressRuleOnALB{suffix}",
            on_delete=cr.AwsSdkCall(
                service="EC2",
                action="revokeSecurityGroupIngress",
                parameters={
                    "GroupId": security_group_id,
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 443,
                            "ToPort": 443,
                            "UserIdGroupPairs": [{"GroupId": alb_security_group_id}],
                        }
                    ],
                },
                physical_resource_id=cr.PhysicalResourceId.of(
                    f"{security_group_id}-specific-ingress-removal"
                ),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    aws_iam.PolicyStatement(
                        actions=["ec2:RevokeSecurityGroupIngress"],
                        resources=["*"],
                    )
                ]
            ),
        )

        return remove_ingress_rule

    def create_uid_lambda(
        self,
        cluster_name: str,
        user_pool_id: str,
        cognito_user_pool_arn: str,
        queue: sqs.Queue,
        sqs_visibility_timeout: Duration,
    ) -> lambda_.Function:
        execution_role = InfraUtils.create_execution_role(self, "uid-lambda-role")

        uid_lambda = lambda_.Function(
            self,
            "generate-uid",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=sqs_visibility_timeout,  # SQS lambda trigger timeout must be the same as SQS visibility timeout
            function_name=f"{cluster_name}_uid_{cognito_trigger_workflow_lambda_name}",
            role=execution_role,
            description="Add uuid for users that don't have one. Add uid to Cognito and DDB",
            **InfraUtils.get_handler_and_code_for_function(
                cognito_trigger_workflow_uid_handler.handle_event
            ),
            reserved_concurrent_executions=1,
            environment={
                "CUSTOM_UID_ATTRIBUTE": f"custom:{constants.COGNITO_UID_ATTRIBUTE}",
                "COGNITO_MIN_ID_INCLUSIVE": str(constants.COGNITO_MIN_ID_INCLUSIVE),
                "COGNITO_MAX_ID_INCLUSIVE": str(constants.COGNITO_MAX_ID_INCLUSIVE),
                "USER_POOL_ID": user_pool_id,
                "CLUSTER_NAME": cluster_name,
                "HTTP_PROXY": self.params.get_str(InternetProxyKey.HTTP_PROXY),
                "HTTPS_PROXY": self.params.get_str(InternetProxyKey.HTTPS_PROXY),
                "NO_PROXY": self.params.get_str(InternetProxyKey.NO_PROXY),
            },
        )

        ddb_user_table_arn = f"arn:{Aws.PARTITION}:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{cluster_name}.accounts.users"

        uid_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                ],
                resources=[
                    ddb_user_table_arn,
                ],
            )
        )
        uid_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "cognito-idp:ListUsers",
                    "cognito-idp:AdminUpdateUserAttributes",
                ],
                resources=[cognito_user_pool_arn],
            )
        )
        uid_lambda.apply_removal_policy(RemovalPolicy.RETAIN)

        uid_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(
                queue, batch_size=10, report_batch_item_failures=True
            )
        )
        return uid_lambda

    def create_post_auth_lambda(
        self,
        cluster_name: str,
        cognito_user_pool_arn: str,
        queue_url: str,
        queue_arn: str,
    ) -> lambda_.Function:
        execution_role = InfraUtils.create_execution_role(self, "post-auth-lambda-role")
        cognito_post_auth_lambda = lambda_.Function(
            self,
            "cognito-post-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            function_name=f"{cluster_name}_post_auth_{cognito_trigger_workflow_lambda_name}",
            timeout=Duration.seconds(5),
            role=execution_role,
            description="Add user event to post auth SQS queue for users that don't have UID",
            **InfraUtils.get_handler_and_code_for_function(
                cognito_trigger_workflow_post_auth_handler.handle_event
            ),
            environment={
                "COGNITO_USER_IDP_TYPE": constants.COGNITO_USER_IDP_TYPE,
                "CLUSTER_NAME": cluster_name,
                "QUEUE_URL": queue_url,
            },
        )

        ddb_user_table_arn = f"arn:{Aws.PARTITION}:dynamodb:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/{cluster_name}.accounts.users"

        cognito_post_auth_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                ],
                resources=[
                    ddb_user_table_arn,
                ],
            )
        )
        cognito_post_auth_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "cognito-idp:ListUsers",
                ],
                resources=[cognito_user_pool_arn],
            )
        )
        cognito_post_auth_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "sqs:SendMessage",
                ],
                resources=[queue_arn],
            )
        )
        cognito_post_auth_lambda.apply_removal_policy(RemovalPolicy.RETAIN)
        return cognito_post_auth_lambda

    def add_lambdas_as_cognito_trigger(
        self,
        cluster_name: str,
        post_auth_lambda: lambda_.Function,
        user_pool_id: str,
    ) -> None:
        cognito_user_pool_arn = f"arn:{Aws.PARTITION}:cognito-idp:{Aws.REGION}:{Aws.ACCOUNT_ID}:userpool/{user_pool_id}"
        external_alb_dns = InfraUtils.get_cluster_setting_string(
            self,
            "cluster.load_balancers.external_alb.load_balancer_dns_name",
            cluster_name,
        )
        cognito_params = get_cognito_construct_params(cluster_name, external_alb_dns)

        update_user_pool = cr.AwsSdkCall(
            service="CognitoIdentityServiceProvider",
            action="updateUserPool",
            parameters={
                "UserPoolId": user_pool_id,
                "LambdaConfig": {
                    "PostAuthentication": post_auth_lambda.function_arn,
                },
                "AdminCreateUserConfig": {
                    "InviteMessageTemplate": {
                        "EmailMessage": cognito_params.user_invitation_email_body,
                        "EmailSubject": cognito_params.user_invitation_email_subject,
                    }
                },
                "AutoVerifiedAttributes": cognito_params.auto_verified_attributes,
            },
            physical_resource_id=cr.PhysicalResourceId.of("update-user-pool-action"),
        )

        cr.AwsCustomResource(
            self,
            "update-user-pool",
            on_update=update_user_pool,
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=[cognito_user_pool_arn]
            ),
        )

        post_auth_lambda.add_permission(
            "invoke-post-auth-permission",
            principal=aws_iam.ServicePrincipal("cognito-idp.amazonaws.com"),
            source_arn=cognito_user_pool_arn,
        )


class CognitoTriggerWorkflowStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        cluster_name: str,
        params: Union[RESParameters, BIParameters],
        synthesizer: Optional[IStackSynthesizer] = None,
        env: Union[Environment, dict[str, Any], None] = None,
    ):
        super().__init__(
            scope,
            stack_id,
            env=env,
            synthesizer=synthesizer,
            description="RES Cognito Trigger workflow",
        )
        self.CognitoTriggerWorkflow = CognitoTriggerWorkflow(
            self, "cognito-trigger-workflow", cluster_name, params
        )
