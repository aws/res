#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.
import os
from typing import Optional

from aws_cdk import Aws
import aws_cdk as cdk
import constructs
import ideaadministrator
from aws_cdk import aws_cognito as cognito
from aws_cdk import custom_resources as cr
from ideaadministrator import app_constants
from ideaadministrator.app.cdk.constructs import ExistingSocaCluster, LambdaFunction, Policy, Role, UserPool
from ideaadministrator.app.cdk.idea_code_asset import IdeaCodeAsset, SupportedLambdaPlatforms
from ideaadministrator.app.cdk.stacks import IdeaBaseStack
from ideasdk.utils import Utils

from ideadatamodel import constants, exceptions
from ideadatamodel import get_cognito_construct_params


class IdentityProviderStack(IdeaBaseStack):
    """
    Identity Provider Stack

    Based on selected identity provider, this stack provisions one of:
        * Cognito User Pool
        * Keycloak

    For Cognito IDP
    ---------------

    Below resources are provisioned:
      * User Pool
      * Custom Resource Lambda Function so that downstream modules can fetch OAuth2 ClientId/ClientSecret and save to AWS SecretsManager

    For Keycloak (TODO)
    ------------

    Below resources are provisioned:
      * ASG + LaunchTemplate + EC2 Instances
      * External ALB Endpoint
      * Internal ALB Endpoint
      * Multi-AZ RDS (Aurora)
      * SecretsManager Secrets
      * CDK Custom Resource as a shim for down stream modules to register OAuth2 clients, Resource Servers
    """

    def __init__(self, scope: constructs.Construct,
                 cluster_name: str,
                 aws_region: str,
                 aws_profile: str,
                 module_id: str,
                 deployment_id: str,
                 termination_protection: bool = True,
                 env: cdk.Environment = None):

        super().__init__(
            scope=scope,
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            module_id=module_id,
            deployment_id=deployment_id,
            termination_protection=termination_protection,
            description=f'ModuleId: {module_id}, Cluster: {cluster_name}, Version: {ideaadministrator.props.current_release_version}',
            tags={
                constants.IDEA_TAG_MODULE_ID: module_id,
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_IDENTITY_PROVIDER,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.cluster = ExistingSocaCluster(self.context, self.stack)

        self.user_pool: Optional[UserPool] = None
        self.oauth_credentials_lambda: Optional[LambdaFunction] = None
        self.vdi_client_id = ""

        provider = self.context.config().get_string('identity-provider.provider', required=True)
        if provider == constants.IDENTITY_PROVIDER_KEYCLOAK:

            raise exceptions.general_exception(f'identity provider: {provider} not supported (yet).')

        elif provider == constants.IDENTITY_PROVIDER_COGNITO_IDP:

            self.build_cognito_idp()
            self.build_cognito_cluster_settings()

        else:

            raise exceptions.general_exception(f'identity provider: {provider} not supported')

    def build_cognito_idp(self):

        removal_policy_value = self.context.config().get_string('identity-provider.cognito.removal_policy', required=True)
        removal_policy = cdk.RemovalPolicy(removal_policy_value)

        # Note: do not use the custom dns name, as the dns name might not have been configured during initial deployment.
        # admins must manually update the email invitation template via AWS Console after the stack is deployed.
        external_alb_dns = self.context.config().get_string('cluster.load_balancers.external_alb.load_balancer_dns_name', required=True)

        # do not touch the user pool invitation emails after the initial cluster creation.
        # if the user pool is already created, read the existing values and set them again to avoid replacing the values
        # during cdk stack update
        user_pool_id = self.context.config().get_string('identity-provider.cognito.user_pool_id')

        cognito_params = get_cognito_construct_params(self.cluster_name, external_alb_dns)

        advanced_security_mode = None if self.aws_region in constants.CAVEATS['COGNITO_ADVANCED_SECURITY_UNAVAIL_REGION_LIST'] else cognito.AdvancedSecurityMode(cognito_params.advanced_security_mode)

        self.user_pool = UserPool(
            context=self.context,
            name=f'{self.cluster_name}-user-pool',
            scope=self.stack,
            props=cognito.UserPoolProps(
                removal_policy=removal_policy,
                user_invitation=cognito.UserInvitationConfig(
                    email_subject=cognito_params.user_invitation_email_subject,
                    email_body=cognito_params.user_invitation_email_body
                ),
                self_sign_up_enabled=True,
                auto_verify=cognito.AutoVerifiedAttrs(email="email" in cognito_params.auto_verified_attributes, phone="phone" in cognito_params.auto_verified_attributes),
                advanced_security_mode=advanced_security_mode,
            )
        )

        # add app client for vdi to authenticate with cognito
        client = self.user_pool.user_pool.add_client(
            id='vdi-client',
            auth_flows=cognito.AuthFlow(
                admin_user_password=True
            ),
            prevent_user_existence_errors=True,
            read_attributes= cdk.aws_cognito.ClientAttributes().with_custom_attributes("uid"),
            write_attributes= cdk.aws_cognito.ClientAttributes().with_standard_attributes(email=True),
            user_pool_client_name="vdi",
            disable_o_auth=True
        )
        self.vdi_client_id = client.user_pool_client_id

        # build lambda function in cluster stack to retrieve the client secret
        # the clientId and client secret is saved in secrets manager for each module
        # since we do not want to create a lambda function for each module, we create this lambda function during
        # cluster stack creation, save the lambda function arn in cluster config, and
        # then invoke it as a custom resource during individual module stack creation

        lambda_name = 'oauth-credentials'
        oauth_credentials_lambda_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            description=f'Role for auth credentials Lambda function for Cluster: {self.cluster_name}',
            assumed_by=['lambda'])

        oauth_credentials_lambda_role.attach_inline_policy(Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='custom-resource-get-user-pool-client-secret.yml'
        ))
        self.oauth_credentials_lambda = LambdaFunction(
            context=self.context,
            name=lambda_name,
            scope=self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_custom_resource_get_user_pool_client_secret',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            description='Get OAuth Credentials for a ClientId in UserPool',
            timeout_seconds=180,
            role=oauth_credentials_lambda_role,
            log_retention_role=self.cluster.get_role(app_constants.LOG_RETENTION_ROLE_NAME)
        )
        self.oauth_credentials_lambda.node.add_dependency(oauth_credentials_lambda_role)

    def build_cognito_cluster_settings(self):

        cluster_settings = {
            'deployment_id': self.deployment_id,
            'cognito.user_pool_id': self.user_pool.user_pool.user_pool_id,
            'cognito.vdi_client_id': self.vdi_client_id,
            'cognito.provider_url': self.user_pool.user_pool.user_pool_provider_url,
            'cognito.domain_url': self.user_pool.domain.base_url(fips=True if self.aws_region in Utils.get_value_as_list('COGNITO_REQUIRE_FIPS_ENDPOINT_REGION_LIST', constants.CAVEATS, []) else False),
            'cognito.oauth_credentials_lambda_arn': self.oauth_credentials_lambda.function_arn
        }

        self.update_cluster_settings(cluster_settings)
