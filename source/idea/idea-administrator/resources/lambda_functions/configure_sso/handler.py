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

from typing import Optional, Dict, List, Any
import base64
import boto3
import botocore.exceptions
import time
import io
import re
import os
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DEFAULT_USER_POOL_CLIENT_NAME = 'single-sign-on-client'
DEFAULT_IDENTITY_PROVIDER_IDENTIFIER = 'single-sign-on-identity-provider'
MODULE_IDENTITY_PROVIDER = 'identity-provider'
SSO_SOURCE_PROVIDER_NAME_REGEX = "^(?!^Cognito$)[\\w._:/-]{1,128}$"
SSO_SOURCE_PROVIDER_NAME_ERROR_MESSAGE = "Only use word character or a single character in the list [\".\", \"_\", \":\", \"/\", \"-\"] for SSO source provider name. " +\
    "Must be between 1 and 128 characters long." +\
    "SourceProviderName may not be Cognito"

class ClientProvider:
    def cognito(self):
        return boto3.client('cognito-idp')

    def secrets_manager(self):
        return boto3.client('secretsmanager')

    def dynamodb_resource(self):
        return boto3.resource('dynamodb')

class ClusterConfigDB():
    def __init__(self, cluster_name):
        self.table_name = f"{cluster_name}.cluster-settings"
        self.ddb_resource  = ClientProvider().dynamodb_resource()
        self.cluster_settings_table = self.ddb_resource.Table(self.table_name)

    def put_item(self, key: str, value: Any):
        self.cluster_settings_table.put_item(
            Item={
                'key': key,
                'value': value
            }
        )

    def update_item(self, key: str, value: Any):
        self.cluster_settings_table.update_item(
            Key={
                'key': key,
            },
            UpdateExpression='SET #value=:value, #source=:source ADD #version :version',
            ExpressionAttributeNames={
                '#value': 'value',
                '#version': 'version',
                '#source': 'source'
            },
            ExpressionAttributeValues={
                ':value': value,
                ':source': 'None',
                ':version': 1
            }
        )

    def get_item(self, key: str):
        result = self.cluster_settings_table.get_item(
            Key={
                'key': key,
            }
        )
        if result and result.get('Item'):
            return result.get('Item').get('value')

class SingleSignOnHelper:
    """
    Configures Single Sign-On for the Cluster

    Multiple Identity Providers for the cluster is NOT supported. Identity Provider must support SAMLv2 or OIDC.
    Disabling Single-Sign On is NOT supported.

    Helps with:
    1. Initializing the Identity Provider in the Cluster's Cognito User Pool
    2. Initializing the Cognito User Pool Client to be used for Communicating with IDP
    """
    def __init__(self, cluster_name):
        self.cluster_name = cluster_name
        client_provider = ClientProvider()
        self.cognito_client = client_provider.cognito()
        self.secretsmanager_client = client_provider.secrets_manager()
        self.config: ClusterConfigDB = ClusterConfigDB(cluster_name=cluster_name)

    def _update_config_entry(self, key: str, value: Any):
        module_id  = MODULE_IDENTITY_PROVIDER
        ddb_key = f'{module_id}.{key}'
        self.config.update_item(f'{module_id}.{key}', value)

    def get_callback_logout_urls(self) -> (List[str], List[str]):
        """
        Build the callback URLs to be configured in the User Pool's OAuth 2.0 Client used for communicating with IDP.
        Since custom domain name can be added at a later point in time, callback urls for both the default load balancer domain name
        and the custom domain name (if available) are returned.

        The `create_or_update_user_pool_client` method can be called multiple times and will update the callback urls returned by this method.
        """
        load_balancer_dns_name = self.config.get_item('cluster.load_balancers.external_alb.load_balancer_dns_name')

        custom_dns_name = self.config.get_item('cluster.load_balancers.external_alb.certificates.custom_dns_name')
        if not custom_dns_name:
            custom_dns_name = self.config.get_item('cluster.load_balancers.external_alb.custom_dns_name')

        cluster_manager_web_context_path = self.config.get_item('cluster-manager.server.web_resources_context_path')
        
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
        if custom_dns_name:
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

        user_pool_id = self.config.get_item('identity-provider.cognito.user_pool_id')
        sso_client_id = self.config.get_item('identity-provider.cognito.sso_client_id')
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

        if sso_client_id:
            user_pool_client_request['ClientId'] = sso_client_id
            update_user_pool_client_result = self.cognito_client.update_user_pool_client(**user_pool_client_request)
            return update_user_pool_client_result['UserPoolClient']

        user_pool_client_request['GenerateSecret'] = True
        create_user_pool_client_result = self.cognito_client.create_user_pool_client(**user_pool_client_request)
        user_pool_client = create_user_pool_client_result['UserPoolClient']

        # get custom kms key id for secrets manager if configured
        # and add kms key id to request if available. else boto client throws validation exception for None
        kms_key_id = self.config.get_item('cluster.secretsmanager.kms_key_id')
        tags = [
            {
                'Key': 'res:EnvironmentName',
                'Value': self.cluster_name
            },
            {
                'Key': 'res:ModuleName',
                'Value': 'cluster-manager'
            }
        ]

        secret_name = f'{self.cluster_name}-sso-client-secret'
        try:
            describe_secret_result = self.secretsmanager_client.describe_secret(
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
            if kms_key_id:
                create_secret_client_secret_request['KmsKeyId'] = kms_key_id
            create_secret_client_secret_result = self.secretsmanager_client.create_secret(**create_secret_client_secret_request)
            secret_arn = create_secret_client_secret_result['ARN']
        else:
            update_secret_client_secret_request = {
                'SecretId': describe_secret_result['ARN'],
                'SecretString': user_pool_client['ClientSecret']
            }
            if kms_key_id:
                update_secret_client_secret_request['KmsKeyId'] = kms_key_id
            update_secret_client_secret_result = self.secretsmanager_client.update_secret(**update_secret_client_secret_request)
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
        saml_metadata_url = request.get('saml_metadata_url')
        saml_metadata_file = request.get('saml_metadata_file')
        if not saml_metadata_url and not saml_metadata_file:
            raise Exception('Either one of [saml_metadata_url, saml_metadata_file] is required, when provider_type = SAML')

        if saml_metadata_file:
            decoded_saml_metadata_file = self.base_64_decode_saml(saml_metadata_file)
            provider_details['MetadataFile'] = decoded_saml_metadata_file
        else:
            provider_details['MetadataURL'] = saml_metadata_url

        provider_details['IDPSignout'] = "true"
        return provider_details


    def base_64_decode_saml(self, value: str):
        DEFAULT_ENCODING = 'utf-8'
        encoded_value = value.encode(DEFAULT_ENCODING)
        decoded_value = base64.b64decode(encoded_value)
        return str(decoded_value, DEFAULT_ENCODING)

        
    def get_oidc_provider_details(self, request) -> Dict:
        """
        build the OIDC provider details based on user input.

        refer to below link for more details:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html#CognitoIdentityProvider.Client.create_identity_provider
        """

        provider_details = {}
        oidc_client_id = request.get('oidc_client_id')
        oidc_client_secret = request.get('oidc_client_secret')
        oidc_issuer = request.get('oidc_issuer')
        oidc_attributes_request_method = request.get('oidc_attributes_request_method')
        oidc_authorize_scopes = request.get('oidc_authorize_scopes')
        oidc_authorize_url = request.get('oidc_authorize_url')
        oidc_token_url = request.get('oidc_token_url')
        oidc_attributes_url = request.get('oidc_attributes_url')
        oidc_jwks_uri = request.get('oidc_jwks_uri')

        if not oidc_client_id:
            raise Exception('oidc_client_id is required')
        if not oidc_client_secret:
            raise Exception('oidc_client_secret is required')
        if not oidc_issuer:
            raise Exception('oidc_issuer is required')

        provider_details['client_id'] = oidc_client_id
        provider_details['client_secret'] = oidc_client_secret
        provider_details['attributes_request_method'] = oidc_attributes_request_method
        provider_details['authorize_scopes'] = oidc_authorize_scopes
        provider_details['oidc_issuer'] = oidc_issuer
        if oidc_authorize_url:
            provider_details['authorize_url'] = oidc_authorize_url
        if oidc_token_url:
            provider_details['token_url'] = oidc_token_url
        if oidc_attributes_url:
            provider_details['attributes_url'] = oidc_attributes_url
        if oidc_jwks_uri:
            provider_details['jwks_uri'] = oidc_jwks_uri

        return provider_details

    def get_identity_provider(self) -> Optional[Dict]:
        """
        method to check if SSO identity provider is already created to ensure only a single IDP is created for the cluster.
        The `identity-provider.cognito.sso_idp_identifier` config entry value is used as the identifier. if the entry does not exist,
        value of `DEFAULT_IDENTITY_PROVIDER_IDENTIFIER` is used.
        """
        user_pool_id = self.config.get_item('identity-provider.cognito.user_pool_id')
        sso_idp_identifier = self.config.get_item('identity-provider.cognito.sso_idp_identifier')
        if not sso_idp_identifier:
            sso_idp_identifier = DEFAULT_IDENTITY_PROVIDER_IDENTIFIER
        try:
            result = self.cognito_client.get_identity_provider_by_identifier(
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

        if not request.get('provider_name'):
            raise Exception('provider_name is required')
        
        if not re.match(SSO_SOURCE_PROVIDER_NAME_REGEX, request.get('provider_name')):
            raise Exception(SSO_SOURCE_PROVIDER_NAME_ERROR_MESSAGE)
        if not request.get('provider_type'):
            raise Exception('provider_type is required')
        if not request.get('provider_email_attribute'):
            raise Exception('provider_email_attribute is required')

        if request.get('provider_type') == 'SAML':
            provider_details = self.get_saml_provider_details(request)
        elif request.get('provider_type') == 'OIDC':
            provider_details = self.get_oidc_provider_details(request)
        else:
            raise Exception('provider type must be one of: SAML or OIDC')

        user_pool_id = self.config.get_item('identity-provider.cognito.user_pool_id')

        existing_identity_provider = self.get_identity_provider()
        sso_idp_identifier = self.config.get_item('identity-provider.cognito.sso_idp_identifier')
        if not sso_idp_identifier:
            sso_idp_identifier = DEFAULT_IDENTITY_PROVIDER_IDENTIFIER

        should_update_identity_provider = (existing_identity_provider is not None
                                            and existing_identity_provider['ProviderName'] == request.get('provider_name')
                                            and existing_identity_provider['ProviderType'] == request.get('provider_type'))

        if should_update_identity_provider:
            self.cognito_client.update_identity_provider(
                UserPoolId=user_pool_id,
                ProviderName=request.get('provider_name'),
                ProviderDetails=provider_details,
                AttributeMapping={
                    'email': request.get('provider_email_attribute')
                },
                IdpIdentifiers=[
                    sso_idp_identifier
                ]
            )
        else:
            if existing_identity_provider is not None:
                self.cognito_client.delete_identity_provider(
                    UserPoolId=user_pool_id,
                    ProviderName=existing_identity_provider['ProviderName']
                )

            self.cognito_client.create_identity_provider(
                UserPoolId=user_pool_id,
                ProviderName=request.get('provider_name'),
                ProviderType=request.get('provider_type'),
                ProviderDetails=provider_details,
                AttributeMapping={
                    'email': request.get('provider_email_attribute')
                },
                IdpIdentifiers=[
                    sso_idp_identifier
                ]
            )

        self._update_config_entry('cognito.sso_idp_provider_name', request.get('provider_name'))
        self._update_config_entry('cognito.sso_idp_provider_type', request.get('provider_type'))
        self._update_config_entry('cognito.sso_idp_identifier', sso_idp_identifier)
        self._update_config_entry('cognito.sso_idp_provider_email_attribute', request.get('provider_email_attribute'))

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
                provider_name=request.get('provider_name'),
                refresh_token_validity_hours= request.get('refresh_token_validity_hours')
        )

        # update cluster settings - this must be last step in the pipeline.
        self._update_config_entry('cognito.sso_enabled', True)

def handler(event, context):
    logger.info(f'ReceivedEvent: {event}')
    try:
        cluster_name = os.environ.get('CLUSTER_NAME')
        configure_sso_request = event.get('configure_sso_request')
        if not configure_sso_request:
            raise Exception('Configure sso input is empty')
        sso_helper = SingleSignOnHelper(cluster_name=cluster_name)
        sso_helper.configure_sso(configure_sso_request)
        return True
    except Exception as e:
        logger.exception(f'Failed to configure sso. {e}')
        raise e
