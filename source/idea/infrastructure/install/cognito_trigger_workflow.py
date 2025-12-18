#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Union

import res.constants as res_constants  # type: ignore
from aws_cdk import Aws, CfnResource, Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam, aws_lambda
from aws_cdk import aws_lambda_event_sources as lambda_event_sources
from aws_cdk import aws_sqs as sqs
from aws_cdk import custom_resources as cr
from constructs import Construct

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs import lambda_
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import (
    CognitoTriggerWorkflowCreatePostAuthPolicy,
    CognitoTriggerWorkflowCreateUidPolicy,
)
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.install.stacks.identity_stack import IdentityStack
from idea.infrastructure.resources.lambda_functions.cognito_trigger_workflow_lambda import (
    cognito_trigger_workflow_post_auth_handler,
    cognito_trigger_workflow_uid_handler,
)
from ideadatamodel import (  # type: ignore
    CognitoConstructParams,
    SocaBaseModel,
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
        cluster_stack: ClusterStack,
        identity_stack: IdentityStack,
        params: Union[RESParameters, BIParameters],
    ):
        super().__init__(scope, id)
        # Get existing resource
        cluster_name = params.get_str(CommonKey.CLUSTER_NAME)
        self.cluster_stack = cluster_stack
        cluster_settings = ClusterSettings(cluster_name, self)
        self.arn_builder = ArnBuilder(cluster_name, cluster_settings, parameters=params)
        self.params = params
        self.apply_permission_boundary = InfraUtils.create_permission_boundary_applier(
            self.params
        )

        vpc_id = params.get_str(CommonKey.VPC_ID)
        alb_security_group_id = cluster_stack.security_groups[
            "external-load-balancer"
        ].security_group_id

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
            cluster_name,
            queue.queue_url,
            cluster_stack.vpc,
            [post_auth_security_group_id],
            cluster_stack.cluster_settings.infrastructure_host_subnets,  # type: ignore
        )

        self.add_lambdas_as_cognito_trigger(
            cluster_name,
            post_auth_lambda,
            identity_stack.user_pool.user_pool_id,
        )

        # UID LAMBDA
        uid_lambda = self.create_uid_lambda(
            cluster_name,
            identity_stack.user_pool.user_pool_id,
            queue,
            sqs_visibility_timeout,
            cluster_stack.vpc,
            [uid_security_group_id],
            cluster_stack.cluster_settings.infrastructure_host_subnets,  # type: ignore
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
        queue: sqs.Queue,
        sqs_visibility_timeout: Duration,
        vpc: ec2.IVpc,
        security_group_ids: list[str],
        subnet_ids: list[str],
    ) -> lambda_.Function:
        uid_lambda = lambda_.Function(
            self,
            f"uid-{cognito_trigger_workflow_lambda_name}",
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Add uuid for users that don't have one. Add uid to Cognito and DDB",  # type: ignore
            timeout=sqs_visibility_timeout,  # type: ignore
            reserved_concurrent_executions=1,  # type: ignore
            handler=cognito_trigger_workflow_uid_handler.handle_event,
            initial_policy=CognitoTriggerWorkflowCreateUidPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.params,
            environment={
                "CUSTOM_UID_ATTRIBUTE": f"custom:{res_constants.COGNITO_UID_ATTRIBUTE}",
                "COGNITO_MIN_ID_INCLUSIVE": str(res_constants.COGNITO_MIN_ID_INCLUSIVE),
                "COGNITO_MAX_ID_INCLUSIVE": str(res_constants.COGNITO_MAX_ID_INCLUSIVE),
                "USER_POOL_ID": user_pool_id,
                "CLUSTER_NAME": cluster_name,
                "HTTP_PROXY": self.params.get_str(InternetProxyKey.HTTP_PROXY),
                "HTTPS_PROXY": self.params.get_str(InternetProxyKey.HTTPS_PROXY),
                "NO_PROXY": self.params.get_str(InternetProxyKey.NO_PROXY),
            },
            vpc=vpc,  # type: ignore
            security_groups=[  # type: ignore
                ec2.SecurityGroup.from_security_group_id(
                    self, f"uid-lambda-sg-{i}", security_group_id
                )
                for i, security_group_id in enumerate(security_group_ids)
            ],
        )
        cfn_uid_lambda: aws_lambda.CfnFunction = (
            uid_lambda.node.default_child  # type: ignore
        )
        cfn_uid_lambda.add_property_override(
            "VpcConfig.SubnetIds",
            subnet_ids,
        )
        uid_lambda.role.add_managed_policy(  # type: ignore
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )

        uid_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(
                queue, batch_size=10, report_batch_item_failures=True
            )
        )

        # Prevent event source mapping from inheriting stack tags
        # Tags will be applied manually via the tag_resources_handler
        for child in uid_lambda.node.children:
            if (
                hasattr(child, "node")
                and res_constants.EVENT_SOURCE_MAPPING_RESOURCE_TYPE in child.node.id
            ):
                cfn_event_source = child.node.default_child
                if cfn_event_source and isinstance(cfn_event_source, CfnResource):
                    cfn_event_source.add_property_override("Tags", [])

        return uid_lambda

    def create_post_auth_lambda(
        self,
        cluster_name: str,
        queue_url: str,
        vpc: ec2.IVpc,
        security_group_ids: list[str],
        subnet_ids: list[str],
    ) -> lambda_.Function:
        cognito_post_auth_lambda = lambda_.Function(
            self,
            f"post-auth-{cognito_trigger_workflow_lambda_name}",
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Add user event to post auth SQS queue for users that don't have UID",  # type: ignore
            timeout=Duration.seconds(5),  # type: ignore
            handler=cognito_trigger_workflow_post_auth_handler.handle_event,
            initial_policy=CognitoTriggerWorkflowCreatePostAuthPolicy.create_policy_statements(self.arn_builder),  # type: ignore
            parameters=self.params,
            environment={
                "COGNITO_USER_IDP_TYPE": res_constants.COGNITO_USER_IDP_TYPE,
                "CLUSTER_NAME": cluster_name,
                "QUEUE_URL": queue_url,
            },
            vpc=vpc,  # type: ignore
            security_groups=[  # type: ignore
                ec2.SecurityGroup.from_security_group_id(
                    self, f"post-auth-lambda-sg-{i}", security_group_id
                )
                for i, security_group_id in enumerate(security_group_ids)
            ],
        )
        cfn_post_auth_lambda: aws_lambda.CfnFunction = (
            cognito_post_auth_lambda.node.default_child  # type: ignore
        )
        cfn_post_auth_lambda.add_property_override(
            "VpcConfig.SubnetIds",
            subnet_ids,
        )
        cognito_post_auth_lambda.role.add_managed_policy(  # type: ignore
            aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaVPCAccessExecutionRole"
            )
        )

        return cognito_post_auth_lambda

    def add_lambdas_as_cognito_trigger(
        self,
        cluster_name: str,
        post_auth_lambda: lambda_.Function,
        user_pool_id: str,
    ) -> None:
        cognito_user_pool_arn = f"arn:{Aws.PARTITION}:cognito-idp:{Aws.REGION}:{Aws.ACCOUNT_ID}:userpool/{user_pool_id}"
        external_alb_dns = self.cluster_stack.external_alb.attr_dns_name  # type: ignore
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
