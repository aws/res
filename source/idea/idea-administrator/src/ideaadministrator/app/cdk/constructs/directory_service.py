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

__all__ = (
    'DirectoryServiceCredentials',
    'ActiveDirectory',
    'UserPool',
    'OAuthClientIdAndSecret'
)

import json
import secrets
import string
from ideaadministrator.app.cdk.idea_code_asset import IdeaCodeAsset, SupportedLambdaPlatforms
from ideadatamodel import constants
from ideasdk.utils import Utils, GroupNameHelper

from ideaadministrator.app.cdk.constructs import SocaBaseConstruct, ExistingSocaCluster, DNSResolverEndpoint, DNSResolverRule, CustomResource, IdeaNagSuppression
from ideaadministrator.app_context import AdministratorContext

from typing import Optional, List

import constructs
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_directoryservice as ds,
    aws_secretsmanager as secretsmanager,
    aws_cognito as cognito
)


class DirectoryServiceCredentials(SocaBaseConstruct):
    """
    Directory Service Root User Credentials

    These credentials are initialized once during the initial cluster creation.
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 admin_username: str,
                 admin_password: Optional[str] = None):
        super().__init__(context, name)

        self.credentials_provided = self.context.config().get_bool('directoryservice.service_account_credentials_provided', default=False)

        if self.credentials_provided:
            return

        kms_key_id = self.context.config().get_string('cluster.secretsmanager.kms_key_id')

        ds_provider = self.context.config().get_string('directoryservice.provider', required=True)
        
        admin_credentials_key = f'{ds_provider}-admin-credentials'
        if Utils.is_empty(admin_password):
            admin_password = self.generate_random_password()
        self.admin_credentials = secretsmanager.CfnSecret(
            scope,
            admin_credentials_key,
            description=f'{ds_provider} Root Credentials, Cluster: {self.cluster_name}',
            kms_key_id=kms_key_id,
            name=self.build_resource_name(admin_credentials_key),
            secret_string=f'{{"{admin_username}":"{admin_password}"}}'
        )
        # access to the secret is restricted using tags.
        cdk.Tags.of(self.admin_credentials).add(constants.IDEA_TAG_MODULE_NAME, constants.MODULE_DIRECTORYSERVICE)

        suppressions = [
            IdeaNagSuppression(rule_id='AwsSolutions-SMG4', reason='Secret rotation not applicable for DirectoryService credentials.')
        ]
        self.add_nag_suppression(construct=self.admin_credentials, suppressions=suppressions)

    def generate_random_password(length=16, exclude_characters='$@;"\\\''):
        all_characters = string.ascii_letters + string.digits + string.punctuation
        character_set = ''.join(ch for ch in all_characters if ch not in exclude_characters)
        password = ''.join(secrets.choice(character_set) for _ in range(length))
        return password

    def get_credentials_secret_arn(self) -> str:
        if self.credentials_provided:
            return self.context.config().get_string('directoryservice.service_account_credentials_secret_arn', required=True)
        else:
            return self.admin_credentials.ref

class OAuthClientIdAndSecret(SocaBaseConstruct):
    """
    Create ClientId and ClientSecret in Secrets Manager
    """

    def __init__(self, context: AdministratorContext,
                 secret_name_prefix: str,
                 module_name: str,
                 scope: constructs.Construct,
                 client_id: str, client_secret: str):
        """
        :param context:
        :param secret_name_prefix is used to create the secret name.
            * <secret_name_prefix>-client-id
            * <secret_name_prefix>-client-secret
        :param module_name is used to tag the secret values.
            access to secrets is restricted by tag name in IAM roles
        :param scope: constructs.Construct
        :param client_id: the client_id
        :param client_secret: the client secret
        """
        super().__init__(context, secret_name_prefix)

        kms_key_id = self.context.config().get_string('cluster.secretsmanager.kms_key_id')

        client_id_key = f'{secret_name_prefix}-client-id'
        self.client_id = secretsmanager.CfnSecret(
            scope,
            client_id_key,
            description=f'{secret_name_prefix} ClientId, Cluster: {self.cluster_name}',
            kms_key_id=kms_key_id,
            name=self.build_resource_name(client_id_key),
            secret_string=client_id
        )
        self.client_id.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
        cdk.Tags.of(self.client_id).add(constants.IDEA_TAG_MODULE_NAME, module_name)

        client_secret_key = f'{secret_name_prefix}-client-secret'
        self.client_secret = secretsmanager.CfnSecret(
            scope,
            client_secret_key,
            description=f'{secret_name_prefix} ClientSecret, Cluster: {self.cluster_name}',
            kms_key_id=kms_key_id,
            name=self.build_resource_name(client_secret_key),
            secret_string=client_secret
        )
        self.client_secret.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
        cdk.Tags.of(self.client_secret).add(constants.IDEA_TAG_MODULE_NAME, module_name)

        suppressions = [
            IdeaNagSuppression(rule_id='AwsSolutions-SMG4', reason='Secret rotation not applicable for OAuth 2.0 ClientId/Secret')
        ]
        self.add_nag_suppression(construct=self.client_id, suppressions=suppressions)
        self.add_nag_suppression(construct=self.client_secret, suppressions=suppressions)


class ActiveDirectory(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 cluster: ExistingSocaCluster,
                 subnets: Optional[List[ec2.ISubnet]] = None,
                 enable_sso: Optional[bool] = False):
        super().__init__(context, name)

        self.scope = scope
        self.cluster = cluster
        self.enable_sso = enable_sso

        self.ad_admin_username = 'Admin'

        self.credentials = self.build_credentials(self.ad_admin_username)

        self.ad_name = self.context.config().get_string('directoryservice.name', required=True)
        self.ad_short_name = self.context.config().get_string('directoryservice.ad_short_name', required=True)
        self.ad_edition = self.context.config().get_string('directoryservice.ad_edition', required=True)

        self.launch_subnets = []
        if subnets is None:
            subnets = self.cluster.private_subnets

        for subnet in subnets:
            self.launch_subnets.append(subnet.subnet_id)
            if len(self.launch_subnets) == 2:
                break

        self.ad = self.build_ad()

        self.build_dns_resolver()

    def build_credentials(self, username: str) -> DirectoryServiceCredentials:
        return DirectoryServiceCredentials(
            self.context,
            'ds-activedirectory-credentials',
            self.scope,
            admin_username=username
        )

    def build_ad(self) -> ds.CfnMicrosoftAD:

        vpc_settings = ds.CfnMicrosoftAD.VpcSettingsProperty(
            subnet_ids=self.launch_subnets,
            vpc_id=self.cluster.vpc.vpc_id)
        
        secret_string = cdk.SecretValue.secrets_manager(self.credentials.get_credentials_secret_arn()).to_string()
        secret_dict = json.loads(secret_string)
        password_value = secret_dict[list(secret_dict.keys())[0]]
        ad = ds.CfnMicrosoftAD(
            self.scope,
            self.construct_id,
            name=self.ad_name,
            password=password_value,
            vpc_settings=vpc_settings,
            edition=self.ad_edition,
            enable_sso=self.enable_sso,
            short_name=self.ad_short_name)
        self.add_common_tags(ad)
        return ad

    def build_dns_resolver(self):

        get_ad_security_group_result = CustomResource(
            context=self.context,
            name='get-ad-security-group-id',
            scope=self.scope,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_custom_resource_get_ad_security_group',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            lambda_timeout_seconds=15,
            policy_template_name='custom-resource-get-ad-security-group.yml',
            resource_type='ADSecurityGroupId'
        ).invoke(
            name=self.resource_name,
            properties={
                'DirectoryId': self.ad.ref
            }
        )

        endpoint = DNSResolverEndpoint(
            context=self.context,
            name=f'{self.cluster_name}',
            scope=self.scope,
            vpc=self.cluster.vpc,
            subnet_ids=self.launch_subnets,
            security_group_ids=[get_ad_security_group_result.get_att_string('SecurityGroupId')]
        )

        DNSResolverRule(
            context=self.context,
            name=self.name,
            scope=self.scope,
            domain_name=self.ad_name,
            vpc=self.cluster.vpc,
            resolver_endpoint_id=endpoint.resolver_endpoint.attr_resolver_endpoint_id,
            ip_addresses=[
                cdk.Fn.select(0, self.ad.attr_dns_ip_addresses),
                cdk.Fn.select(1, self.ad.attr_dns_ip_addresses)
            ],
            port='53'
        )


class UserPool(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 props: cognito.UserPoolProps = None):
        super().__init__(context, name)
        self.scope = scope

        self.user_pool: Optional[cognito.UserPool] = None
        self.domain: Optional[cognito.UserPoolDomain] = None
        self.secrets: Optional[List[OAuthClientIdAndSecret]] = []
        self.props = props
        if self.props is None:
            self.props = cognito.UserPoolProps()

        self.build_user_pool(self.props)

    def build_user_pool(self, props: cognito.UserPoolProps):
        account_recovery = props.account_recovery
        if account_recovery is None:
            account_recovery = cognito.AccountRecovery.EMAIL_ONLY
        auto_verify = props.auto_verify
        if auto_verify is None:
            auto_verify = cognito.AutoVerifiedAttrs(email=True, phone=False)
        custom_attributes = props.custom_attributes
        if custom_attributes is None:
            custom_attributes = {
                'cluster_name': cognito.StringAttribute(mutable=True),
                'aws_region': cognito.StringAttribute(mutable=True),
                'password_last_set': cognito.NumberAttribute(mutable=True),
                'password_max_age': cognito.NumberAttribute(mutable=True)
            }
        mfa = props.mfa
        if mfa is None:
            mfa = cognito.Mfa.OPTIONAL
        mfa_second_factor = props.mfa_second_factor
        if mfa_second_factor is None:
            mfa_second_factor = cognito.MfaSecondFactor(otp=True, sms=False)

        password_policy = props.password_policy
        if password_policy is None:
            password_policy = cognito.PasswordPolicy(
                min_length=8,
                require_digits=True,
                require_lowercase=True,
                require_symbols=True,
                require_uppercase=True,
                temp_password_validity=cdk.Duration.days(7)
            )

        removal_policy = props.removal_policy
        if removal_policy is None:
            removal_policy = cdk.RemovalPolicy.DESTROY

        self_sign_up_enabled = props.self_sign_up_enabled
        if self_sign_up_enabled is None:
            self_sign_up_enabled = False

        sign_in_aliases = props.sign_in_aliases
        if sign_in_aliases is None:
            sign_in_aliases = cognito.SignInAliases(
                username=True,
                preferred_username=False,
                phone=False,
                email=True
            )

        sign_in_case_sensitive = props.sign_in_case_sensitive
        if sign_in_case_sensitive is None:
            sign_in_case_sensitive = False

        standard_attributes = props.standard_attributes
        if standard_attributes is None:
            standard_attributes = cognito.StandardAttributes(
                email=cognito.StandardAttribute(mutable=True, required=True)
            )
        user_invitation = props.user_invitation
        if user_invitation is None:
            user_invitation = cognito.UserInvitationConfig(
                email_subject=f'({self.cluster_name}) Your IDEA Account',
                email_body=f'''
                Hello <b>{{username}}</b>,
                <br/><br/>
                You have been invited to join the {self.cluster_name} cluster.
                <br/>
                Your temporary password is <b>{{####}}</b>
                '''
            )

        user_pool_name = props.user_pool_name
        if user_pool_name is None:
            user_pool_name = f'{self.cluster_name}-user-pool'

        advanced_security_mode = None

        if self.context.aws().aws_region() in Utils.get_value_as_list('COGNITO_ADVANCED_SECURITY_UNAVAIL_REGION_LIST', constants.CAVEATS):
            self.context.warning(f'Cognito Advanced security NOT SET - Not available in this region ({self.context.aws().aws_region()})')
            advanced_security_mode = None
        else:
            advanced_security_mode_cfg = self.context.config().get_string('identity-provider.cognito.advanced_security_mode', default='AUDIT')

            if advanced_security_mode_cfg.upper() == 'AUDIT':
                advanced_security_mode = cognito.AdvancedSecurityMode.AUDIT
            elif advanced_security_mode_cfg.upper() == 'ENFORCED':
                advanced_security_mode = cognito.AdvancedSecurityMode.ENFORCED
            else:
                advanced_security_mode = cognito.AdvancedSecurityMode.OFF

        self.user_pool = cognito.UserPool(
            scope=self.scope,
            id=user_pool_name,
            account_recovery=account_recovery,
            advanced_security_mode=advanced_security_mode,
            auto_verify=auto_verify,
            custom_attributes=custom_attributes,
            custom_sender_kms_key=props.custom_sender_kms_key,
            deletion_protection=True,
            device_tracking=props.device_tracking,
            email=props.email,
            enable_sms_role=props.enable_sms_role,
            lambda_triggers=props.lambda_triggers,
            mfa=mfa,
            mfa_message=props.mfa_message,
            mfa_second_factor=mfa_second_factor,
            password_policy=password_policy,
            removal_policy=removal_policy,
            self_sign_up_enabled=self_sign_up_enabled,
            sign_in_aliases=sign_in_aliases,
            sign_in_case_sensitive=sign_in_case_sensitive,
            sms_role=props.sms_role,
            sms_role_external_id=props.sms_role_external_id,
            standard_attributes=standard_attributes,
            user_invitation=user_invitation,
            user_pool_name=user_pool_name,
            user_verification=props.user_verification
        )
        self.add_common_tags(self.user_pool)

        # MFA
        self.add_nag_suppression(construct=self.user_pool, suppressions=[
            IdeaNagSuppression(rule_id='AwsSolutions-COG2', reason='Suppress MFA warning. MFA provided by customer IdP/SSO methods.')
        ])

        # advanced security mode suppression
        self.add_nag_suppression(construct=self.user_pool, suppressions=[
            IdeaNagSuppression(rule_id='AwsSolutions-COG3', reason='suppress advanced security rule 1/to save cost, 2/Not supported in GovCloud')
        ])

        domain_url = self.context.config().get_string('identity-provider.cognito.domain_url')
        if Utils.is_not_empty(domain_url):
            domain_prefix = domain_url.replace('https://', '').split('.')[0]
        else:
            domain_prefix = f'{self.cluster_name}-{Utils.uuid()}'

        self.domain = self.user_pool.add_domain(
            id='domain',
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=domain_prefix
            )
        )
