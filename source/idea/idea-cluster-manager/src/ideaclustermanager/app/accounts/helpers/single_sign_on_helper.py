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

from ideasdk.utils import ApiUtils, Utils
from ideadatamodel import exceptions, constants
from ideasdk.config.cluster_config import ClusterConfig
from ideasdk.context import SocaContext

from typing import Optional, Dict, List, Any
import botocore.exceptions
import time
import io

DEFAULT_USER_POOL_CLIENT_NAME = 'single-sign-on-client'
DEFAULT_IDENTITY_PROVIDER_IDENTIFIER = 'single-sign-on-identity-provider'


class SingleSignOnHelper:
    """
    Configures Single Sign-On for the Cluster

    Multiple Identity Providers for the cluster is NOT supported. Identity Provider must support SAMLv2 or OIDC.
    Disabling Single-Sign On is NOT supported.

    Helps with:
    1. Initializing the Identity Provider in the Cluster's Cognito User Pool
    2. Initializing the Cognito User Pool Client to be used for Communicating with IDP
    3. Linking existing non-system users with IDP
    """

    def __init__(self, context: SocaContext):
        self.context = context
        self.cluster_name = self.context._options.cluster_name
        self.aws_region =self.context._options.aws_region
        self.config: ClusterConfig = context._config
        self.logger = context.logger(name=f'{context.module_id()}-sso-helper')

    def _update_config_entry(self, key: str, value: Any):
        module_id = self.config.get_module_id(constants.MODULE_IDENTITY_PROVIDER)
        self.config.db.set_config_entry(f'{module_id}.{key}', value)
        self.config.put(f'{module_id}.{key}', value)

    def get_callback_logout_urls(self) -> (List[str], List[str]):
        """
        Build the callback URLs to be configured in the User Pool's OAuth 2.0 Client used for communicating with IDP.
        Since custom domain name can be added at a later point in time, callback urls for both the default load balancer domain name
        and the custom domain name (if available) are returned.

        The `create_or_update_user_pool_client` method can be called multiple times and will update the callback urls returned by this method.
        """
        load_balancer_dns_name = self.context.config().get_string('cluster.load_balancers.external_alb.load_balancer_dns_name', required=True)

        custom_dns_name = self.context.config().get_string('cluster.load_balancers.external_alb.certificates.custom_dns_name')
        if Utils.is_empty(custom_dns_name):
            custom_dns_name = self.context.config().get_string('cluster.load_balancers.external_alb.custom_dns_name')

        cluster_manager_web_context_path = self.context.config().get_string('cluster-manager.server.web_resources_context_path', required=True)
        if cluster_manager_web_context_path == '/':
            sso_auth_callback_path = '/sso/oauth2/callback'
        else:
            sso_auth_callback_path = f'{cluster_manager_web_context_path}/oauth2/callback'

        if not sso_auth_callback_path.startswith('/'):
            sso_auth_callback_path = f'/{sso_auth_callback_path}'

        callback_urls = [
            f'https://{load_balancer_dns_name}{sso_auth_callback_path}'
        ]

        if len(cluster_manager_web_context_path) > 0 and cluster_manager_web_context_path[-1] == '/':
            cluster_manager_web_context_path = cluster_manager_web_context_path[:-1]

        if len(cluster_manager_web_context_path) > 0 and not cluster_manager_web_context_path.startswith('/'):
            cluster_manager_web_context_path = f'/{cluster_manager_web_context_path}'

        logout_urls = [
            f'https://{load_balancer_dns_name}{cluster_manager_web_context_path}'
        ]
        if Utils.is_not_empty(custom_dns_name):
            callback_urls.append(f'https://{custom_dns_name}{sso_auth_callback_path}')
            logout_urls.append(f'https://{custom_dns_name}{cluster_manager_web_context_path}')
        return callback_urls, logout_urls

    def create_or_update_user_pool_client(self, provider_name: str, refresh_token_validity_hours: int = None) -> Dict:
        """
        setup the user pool client used for communicating with the IDP.

        the ClientId and ClientSecret are saved to cluster configuration and secrets manager.
        cluster configuration with clientId and secret arn is updated only once during creation.

        method can be invoked multiple times to update the user pool client if it already exists to support updating
        the callback urls
        """

        user_pool_id = self.context.config().get_string('identity-provider.cognito.user_pool_id', required=True)
        sso_client_id = self.context.config().get_string('identity-provider.cognito.sso_client_id')
        if refresh_token_validity_hours is None or refresh_token_validity_hours <= 0 or refresh_token_validity_hours > 87600:
            refresh_token_validity_hours = 12

        callback_urls, logout_urls = self.get_callback_logout_urls()
        user_pool_client_request = {
            'UserPoolId': user_pool_id,
            'ClientName': DEFAULT_USER_POOL_CLIENT_NAME,
            'AccessTokenValidity': 1,
            'IdTokenValidity': 1,
            'RefreshTokenValidity': refresh_token_validity_hours,
            'TokenValidityUnits': {
                'AccessToken': 'hours',
                'IdToken': 'hours',
                'RefreshToken': 'hours'
            },
            'ReadAttributes': [
                'address',
                'birthdate',
                'custom:aws_region',
                'custom:cluster_name',
                'custom:password_last_set',
                'custom:password_max_age',
                'email',
                'email_verified',
                'family_name',
                'gender',
                'given_name',
                'locale',
                'middle_name',
                'name',
                'nickname',
                'phone_number',
                'phone_number_verified',
                'picture',
                'preferred_username',
                'profile',
                'updated_at',
                'website',
                'zoneinfo'
            ],
            'AllowedOAuthFlows': [
                'code'
            ],
            'AllowedOAuthScopes': [
                'email',
                'openid',
                'aws.cognito.signin.user.admin'
            ],
            'CallbackURLs': callback_urls,
            'LogoutURLs': logout_urls,
            'SupportedIdentityProviders': [provider_name],
            'AllowedOAuthFlowsUserPoolClient': True
        }

        if Utils.is_not_empty(sso_client_id):
            user_pool_client_request['ClientId'] = sso_client_id
            update_user_pool_client_result = self.context.aws().cognito_idp().update_user_pool_client(**user_pool_client_request)
            return update_user_pool_client_result['UserPoolClient']

        user_pool_client_request['GenerateSecret'] = True
        create_user_pool_client_result = self.context.aws().cognito_idp().create_user_pool_client(**user_pool_client_request)
        user_pool_client = create_user_pool_client_result['UserPoolClient']

        # get custom kms key id for secrets manager if configured
        # and add kms key id to request if available. else boto client throws validation exception for None
        kms_key_id = self.config.get_string('cluster.secretsmanager.kms_key_id')

        tags = [
            {
                'Key': constants.IDEA_TAG_ENVIRONMENT_NAME,
                'Value': self.cluster_name
            },
            {
                'Key': constants.IDEA_TAG_MODULE_NAME,
                'Value': constants.MODULE_CLUSTER_MANAGER
            }
        ]

        secret_name = f'{self.cluster_name}-sso-client-secret'
        try:
            describe_secret_result = self.context.aws().secretsmanager().describe_secret(
                SecretId=secret_name
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                describe_secret_result = None
            else:
                raise e

        if describe_secret_result is None:
            create_secret_client_secret_request = {
                'Name': f'{self.cluster_name}-sso-client-secret',
                'Description': f'Single Sign-On OAuth2 Client Secret for Cluster: {self.cluster_name}',
                'Tags': tags,
                'SecretString': user_pool_client['ClientSecret']
            }
            if Utils.is_not_empty(kms_key_id):
                create_secret_client_secret_request['KmsKeyId'] = kms_key_id
            create_secret_client_secret_result = self.context.aws().secretsmanager().create_secret(**create_secret_client_secret_request)
            secret_arn = create_secret_client_secret_result['ARN']
        else:
            update_secret_client_secret_request = {
                'SecretId': describe_secret_result['ARN'],
                'SecretString': user_pool_client['ClientSecret']
            }
            if Utils.is_not_empty(kms_key_id):
                update_secret_client_secret_request['KmsKeyId'] = kms_key_id
            update_secret_client_secret_result = self.context.aws().secretsmanager().update_secret(**update_secret_client_secret_request)
            secret_arn = update_secret_client_secret_result['ARN']

        self._update_config_entry('cognito.sso_client_id', user_pool_client['ClientId'])
        self._update_config_entry('cognito.sso_client_secret', secret_arn)
        return user_pool_client

    def get_saml_provider_details(self, request) -> Dict:
        """
        build the SAML provider details based on user input
        the `saml_metadata_file` must be a path to the file on local file system, which is read and contents are sent to boto API.

        refer to below link for more details:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html#CognitoIdentityProvider.Client.create_identity_provider
        """
        provider_details = {}
        saml_metadata_url = request.saml_metadata_url
        saml_metadata_file = request.saml_metadata_file
        if Utils.are_empty(saml_metadata_url, saml_metadata_file):
            raise exceptions.invalid_params('Either one of [saml_metadata_url, saml_metadata_file] is required, when provider_type = SAML')

        if Utils.is_not_empty(saml_metadata_file):
            decoded_saml_metadata_file = Utils.base64_decode(saml_metadata_file)
            provider_details['MetadataFile'] = decoded_saml_metadata_file
        else:
            provider_details['MetadataURL'] = saml_metadata_url

        provider_details['IDPSignout'] = "true"
        return provider_details

    def get_oidc_provider_details(self, request) -> Dict:
        """
        build the OIDC provider details based on user input.

        refer to below link for more details:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html#CognitoIdentityProvider.Client.create_identity_provider
        """

        provider_details = {}
        oidc_client_id = request.oidc_client_id
        oidc_client_secret = request.oidc_client_secret
        oidc_issuer = request.oidc_issuer
        oidc_attributes_request_method = request.oidc_attributes_request_method
        oidc_authorize_scopes = request.oidc_authorize_scopes
        oidc_authorize_url = request.oidc_authorize_url
        oidc_token_url = request.oidc_token_url
        oidc_attributes_url = request.oidc_attributes_url
        oidc_jwks_uri = request.oidc_jwks_uri

        if Utils.is_empty(oidc_client_id):
            raise exceptions.invalid_params('oidc_client_id is required')
        if Utils.is_empty(oidc_client_secret):
            raise exceptions.invalid_params('oidc_client_secret is required')
        if Utils.is_empty(oidc_issuer):
            raise exceptions.invalid_params('oidc_issuer is required')

        provider_details['client_id'] = oidc_client_id
        provider_details['client_secret'] = oidc_client_secret
        provider_details['attributes_request_method'] = oidc_attributes_request_method
        provider_details['authorize_scopes'] = oidc_authorize_scopes
        provider_details['oidc_issuer'] = oidc_issuer
        if Utils.is_not_empty(oidc_authorize_url):
            provider_details['authorize_url'] = oidc_authorize_url
        if Utils.is_not_empty(oidc_token_url):
            provider_details['token_url'] = oidc_token_url
        if Utils.is_not_empty(oidc_attributes_url):
            provider_details['attributes_url'] = oidc_attributes_url
        if Utils.is_not_empty(oidc_jwks_uri):
            provider_details['jwks_uri'] = oidc_jwks_uri

        return provider_details

    def get_identity_provider(self) -> Optional[Dict]:
        """
        method to check if SSO identity provider is already created to ensure only a single IDP is created for the cluster.
        The `identity-provider.cognito.sso_idp_identifier` config entry value is used as the identifier. if the entry does not exist,
        value of `DEFAULT_IDENTITY_PROVIDER_IDENTIFIER` is used.
        """
        user_pool_id = self.context.config().get_string('identity-provider.cognito.user_pool_id', required=True)
        sso_idp_identifier = self.context.config().get_string('identity-provider.cognito.sso_idp_identifier', DEFAULT_IDENTITY_PROVIDER_IDENTIFIER)
        try:
            result = self.context.aws().cognito_idp().get_identity_provider_by_identifier(
                UserPoolId=user_pool_id,
                IdpIdentifier=sso_idp_identifier
            )
            return result['IdentityProvider']
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            else:
                raise e

    def create_or_update_identity_provider(self, request):
        """
        setup the Identity Provider for the Cognito User Pool.
        at the moment, only OIDC and SAML provider types are supported.

        provider details are built using the `get_saml_provider_details` for SAML and `get_oidc_provider_details` for OIDC.

        Important:
        `identity-provider.cognito.sso_idp_provider_name` config entry is updated with the name of the IDP provider.
        changing this value will result in adding multiple IDPs for the cluster and will result in broken SSO functionality.
        as part of AccountsService during user creation, if SSO is enabled, the new user will be linked with the IDP Provider name
         specified in `identity-provider.cognito.sso_idp_provider_name`
        """

        if Utils.is_empty(request.provider_name):
            raise exceptions.invalid_params('provider_name is required')
        ApiUtils.validate_input(request.provider_name,
                                constants.SSO_SOURCE_PROVIDER_NAME_REGEX,
                                constants.SSO_SOURCE_PROVIDER_NAME_ERROR_MESSAGE)
        if Utils.is_empty(request.provider_type):
            raise exceptions.invalid_params('provider_type is required')
        if Utils.is_empty(request.provider_email_attribute):
            raise exceptions.invalid_params('provider_email_attribute is required')

        if request.provider_type == constants.SSO_IDP_PROVIDER_SAML:
            provider_details = self.get_saml_provider_details(request)
        elif request.provider_type == constants.SSO_IDP_PROVIDER_OIDC:
            provider_details = self.get_oidc_provider_details(request)
        else:
            raise exceptions.invalid_params('provider type must be one of: SAML or OIDC')

        user_pool_id = self.context.config().get_string('identity-provider.cognito.user_pool_id', required=True)

        existing_identity_provider = self.get_identity_provider()
        sso_idp_identifier = self.context.config().get_string('identity-provider.cognito.sso_idp_identifier', DEFAULT_IDENTITY_PROVIDER_IDENTIFIER)

        should_update_identity_provider = (existing_identity_provider is not None
                                           and existing_identity_provider['ProviderName'] == request.provider_name
                                           and existing_identity_provider['ProviderType'] == request.provider_type)

        if should_update_identity_provider:
            self.context.aws().cognito_idp().update_identity_provider(
                UserPoolId=user_pool_id,
                ProviderName=request.provider_name,
                ProviderDetails=provider_details,
                AttributeMapping={
                    'email': request.provider_email_attribute
                },
                IdpIdentifiers=[
                    sso_idp_identifier
                ]
            )
        else:
            if existing_identity_provider is not None:
                self.context.aws().cognito_idp().delete_identity_provider(
                    UserPoolId=user_pool_id,
                    ProviderName=existing_identity_provider['ProviderName']
                )

            self.context.aws().cognito_idp().create_identity_provider(
                UserPoolId=user_pool_id,
                ProviderName=request.provider_name,
                ProviderType=request.provider_type,
                ProviderDetails=provider_details,
                AttributeMapping={
                    'email': request.provider_email_attribute
                },
                IdpIdentifiers=[
                    sso_idp_identifier
                ]
            )

        self._update_config_entry('cognito.sso_idp_provider_name', request.provider_name)
        self._update_config_entry('cognito.sso_idp_provider_type', request.provider_type)
        self._update_config_entry('cognito.sso_idp_identifier', sso_idp_identifier)
        self._update_config_entry('cognito.sso_idp_provider_email_attribute', request.provider_email_attribute)

    def link_existing_users(self):
        """
        if there are existing users in the user pool, added prior to enabling SSO, link all the existing users with IDP.
        this ensures SSO works for existing users that were created before enabling IDP.

        system administration users such as clusteradmin are not linked with IDP with an assumption that no such users will exist
        in corporate directory service.

        when SSO is enabled, accessing the cluster endpoint will result in signing-in automatically.
        to ensure clusteradmin user can sign-in, a special query parameter can be provided:
        `sso=False`
        sending this parameter as part of query string will not trigger the sso flow from the web portal.
        """
        user_pool_id = self.context.config().get_string('identity-provider.cognito.user_pool_id', required=True)
        provider_name = self.context.config().get_string('identity-provider.cognito.sso_idp_provider_name', required=True)
        provider_type = self.context.config().get_string('identity-provider.cognito.sso_idp_provider_type', required=True)
        cluster_admin_username = self.context.config().get_string('cluster.administrator_username', required=True)

        if provider_type == constants.SSO_IDP_PROVIDER_OIDC:
            provider_email_attribute = 'email'
        else:
            provider_email_attribute = self.context.config().get_string('identity-provider.cognito.sso_idp_provider_email_attribute', required=True)

        while True:
            list_users_result = self.context.aws().cognito_idp().list_users(
                UserPoolId=user_pool_id
            )
            users = list_users_result['Users']
            for user in users:
                try:
                    if user['UserStatus'] == 'EXTERNAL_PROVIDER':
                        continue

                    username = user['Username']

                    # exclude system administration users
                    if username in cluster_admin_username or username.startswith('clusteradmin'):
                        self.logger.info(f'system administration user found: {username}. skip linking with IDP.')
                        continue

                    email = None
                    already_linked = False
                    user_attributes = Utils.get_value_as_list('Attributes', user, [])
                    for user_attribute in user_attributes:
                        name = user_attribute['Name']
                        if name == 'email':
                            email = Utils.get_value_as_string('Value', user_attribute)
                        elif name == 'identities':
                            identities = Utils.get_value_as_list('Value', user_attribute, [])
                            for identity in identities:
                                if identity['providerName'] == provider_name:
                                    already_linked = True
                    if Utils.is_empty(email):
                        continue
                    if already_linked:
                        self.logger.info(f'user: {username}, email: {email} already linked. skip.')
                        continue

                    self.logger.info(f'linking user: {username}, email: {email} ...')

                    def admin_link_provider_for_user(**kwargs):
                        self.logger.info(f'link request: {Utils.to_json(kwargs)}')
                        self.context.aws().cognito_idp().admin_link_provider_for_user(**kwargs)

                    admin_link_provider_for_user(
                        UserPoolId=user_pool_id,
                        DestinationUser={
                            'ProviderName': 'Cognito',
                            'ProviderAttributeName': 'cognito:username',
                            'ProviderAttributeValue': user['Username']
                        },
                        SourceUser={
                            'ProviderName': provider_name,
                            'ProviderAttributeName': provider_email_attribute,
                            'ProviderAttributeValue': email
                        }
                    )
                    # sleep for a while to avoid flooding aws with these requests.
                    time.sleep(0.2)
                except Exception as e:
                    self.logger.error(f'failed to link user: {user} with IDP: {provider_name} - {e}')

            pagination_token = Utils.get_value_as_string('PaginationToken', list_users_result)
            if Utils.is_empty(pagination_token):
                break

    def configure_sso(self, request):
        """
        execute series of steps to configure Single Sign-On for the cluster.

        `identity-provider.cognito.sso_enabled` boolean config entry is set to True at the end of the flow.
        this config entry is the single place in the cluster to indicate SSO is enabled.
        """
        # reset sso status
        self._update_config_entry('cognito.sso_enabled', False)

        # identity provider
        self.create_or_update_identity_provider(request)

        # user pool client
        self.create_or_update_user_pool_client(
                provider_name=request.provider_name,
                refresh_token_validity_hours=Utils.get_value_as_int('refresh_token_validity_hours', request, default=None)
        )

        # link existing users
        self.link_existing_users()

        # update cluster settings - this must be last step in the pipeline.
        self._update_config_entry('cognito.sso_enabled', True)
