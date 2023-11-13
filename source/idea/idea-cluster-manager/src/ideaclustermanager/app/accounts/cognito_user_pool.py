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
import logging

from ideadatamodel import (
    exceptions,
    errorcodes,
    constants,
    SocaBaseModel,
    InitiateAuthRequest,
    InitiateAuthResult,
    RespondToAuthChallengeRequest,
    RespondToAuthChallengeResult,
    AuthResult,
    CognitoUser,
    CognitoUserPoolPasswordPolicy
)
from ideasdk.utils import Utils
from ideasdk.context import SocaContext

from typing import Optional, Dict
import botocore.exceptions
import hmac
import hashlib
import base64


class CognitoUserPoolOptions(SocaBaseModel):
    user_pool_id: Optional[str]
    admin_group_name: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]


class CognitoUserPool:

    def __init__(self, context: SocaContext, options: CognitoUserPoolOptions):
        self._context = context
        self._logger = context.logger('user-pool')

        if Utils.is_empty(options.user_pool_id):
            raise exceptions.invalid_params('options.user_pool_id is required')
        if Utils.is_empty(options.admin_group_name):
            raise exceptions.invalid_params('options.admin_group_name is required')
        if Utils.is_empty(options.client_id):
            raise exceptions.invalid_params('options.client_id is required')
        if Utils.is_empty(options.client_secret):
            raise exceptions.invalid_params('options.client_secret is required')

        self.options = options

        self._sso_client_id: Optional[str] = None
        self._sso_client_secret: Optional[str] = None

    @property
    def user_pool_id(self) -> str:
        return self.options.user_pool_id

    @property
    def admin_group_name(self) -> str:
        return self.options.admin_group_name

    def get_client_id(self, sso: bool = False) -> str:
        if sso:
            return self._context.config().get_string('identity-provider.cognito.sso_client_id', required=True)
        else:
            return self.options.client_id

    def get_client_secret(self, sso: bool = False) -> str:
        if sso:
            if self._sso_client_secret is None:
                self._sso_client_secret = self._context.config().get_secret('identity-provider.cognito.sso_client_secret', required=True)
            return self._sso_client_secret
        else:
            return self.options.client_secret

    def is_activedirectory(self) -> bool:
        provider = self._context.config().get_string('directoryservice.provider', required=True)
        return provider in (constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY,
                            constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY)

    def get_secret_hash(self, username: str, sso: bool = False):

        client_id = self.get_client_id(sso)
        client_secret = self.get_client_secret(sso)

        # A keyed-hash message authentication code (HMAC) calculated using
        # the secret key of a user pool client and username plus the client
        # ID in the message.
        dig = hmac.new(
            key=Utils.to_bytes(client_secret),
            msg=Utils.to_bytes(f'{username}{client_id}'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()

    @staticmethod
    def build_user_cache_key(username: str) -> str:
        return f'cognito.user-pool.user.{username}'

    @staticmethod
    def build_auth_result(cognito_auth_result: Dict) -> AuthResult:
        access_token = Utils.get_value_as_string('AccessToken', cognito_auth_result)
        expires_in = Utils.get_value_as_int('ExpiresIn', cognito_auth_result)
        token_type = Utils.get_value_as_string('TokenType', cognito_auth_result)
        refresh_token = Utils.get_value_as_string('RefreshToken', cognito_auth_result)
        id_token = Utils.get_value_as_string('IdToken', cognito_auth_result)
        return AuthResult(
            access_token=access_token,
            expires_in=expires_in,
            token_type=token_type,
            refresh_token=refresh_token,
            id_token=id_token
        )

    def admin_get_user(self, username: str) -> Optional[CognitoUser]:
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        cache_key = self.build_user_cache_key(username)

        user = self._context.cache().short_term().get(cache_key)
        if user is not None:
            return user

        _api_query_start = Utils.current_time_ms()

        try:
            result = self._context.aws().cognito_idp().admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                return None
            else:
                raise e

        _api_query_end = Utils.current_time_ms()
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(f"Cognito-API query: {_api_query_end - _api_query_start}ms")

        user = CognitoUser(**result)
        self._context.cache().short_term().set(cache_key, user)
        return user

    def admin_create_user(self, username: str, email: str, password: Optional[str] = None, email_verified=False):

        if email_verified and Utils.is_empty(password):
            raise exceptions.invalid_params('password is required when email_verified=True')

        create_user_params = {
            'UserPoolId': self.user_pool_id,
            'Username': username,
            'UserAttributes': [
                {
                    'Name': 'email',
                    'Value': email
                },
                {
                    'Name': 'email_verified',
                    'Value': str(email_verified)
                },
                {
                    'Name': 'custom:cluster_name',
                    'Value': str(self._context.cluster_name())
                },
                {
                    'Name': 'custom:aws_region',
                    'Value': str(self._context.aws().aws_region())
                }
            ],
            'DesiredDeliveryMediums': ['EMAIL']
        }

        if email_verified:
            create_user_params['MessageAction'] = 'SUPPRESS'
        else:
            if Utils.is_not_empty(password):
                create_user_params['TemporaryPassword'] = password

        create_result = self._context.aws().cognito_idp().admin_create_user(**create_user_params)

        created_user = Utils.get_value_as_dict('User', create_result)
        status = Utils.get_value_as_string('UserStatus', created_user)
        self._logger.info(f'CreateUser: {username}, Status: {status}, EmailVerified: {email_verified}')

        if email_verified:
            self.admin_set_password(username, password, permanent=True)

    def admin_delete_user(self, username: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        try:
            self._context.aws().cognito_idp().admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                pass
            else:
                raise e
        self._context.cache().short_term().delete(self.build_user_cache_key(username))

    def admin_enable_user(self, username: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        self._context.aws().cognito_idp().admin_enable_user(
            UserPoolId=self.user_pool_id,
            Username=username
        )
        self._context.cache().short_term().delete(self.build_user_cache_key(username))

    def admin_disable_user(self, username: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        self._context.aws().cognito_idp().admin_disable_user(
            UserPoolId=self.user_pool_id,
            Username=username
        )
        self._context.cache().short_term().delete(self.build_user_cache_key(username))

    def admin_add_user_as_admin(self, username: str):
        self.admin_add_user_to_group(username=username, group_name=self.admin_group_name)

        # todo: Remove once use of RES specific groups is removed
        for admin_group in constants.RES_ADMIN_GROUPS:
            try:
                self._logger.info(f'Adding username {username} to RES_ADMIN_GROUP: {admin_group}')
                self._context.accounts.add_users_to_group([username], admin_group, bypass_active_user_check=True)
            except Exception as e:
                self._logger.debug(f"Could not add user {username} to RES_ADMIN_GROUP: {admin_group}")

    def admin_add_user_to_group(self, username: str, group_name: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('username is required')

        self._context.aws().cognito_idp().admin_add_user_to_group(
            UserPoolId=self.user_pool_id,
            Username=username,
            GroupName=group_name
        )

    def admin_link_idp_for_user(self, username: str, email: str):

        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        cluster_administrator = self._context.config().get_string('cluster.administrator_username', required=True)
        if username in cluster_administrator or username.startswith('clusteradmin'):
            self._logger.info(f'system administration user found: {username}. skip linking with IDP.')
            return

        provider_name = self._context.config().get_string('identity-provider.cognito.sso_idp_provider_name', required=True)
        provider_type = self._context.config().get_string('identity-provider.cognito.sso_idp_provider_type', required=True)
        if provider_type == constants.SSO_IDP_PROVIDER_OIDC:
            provider_email_attribute = 'email'
        else:
            provider_email_attribute = self._context.config().get_string('identity-provider.cognito.sso_idp_provider_email_attribute', required=True)

        self._context.aws().cognito_idp().admin_link_provider_for_user(
            UserPoolId=self.user_pool_id,
            DestinationUser={
                'ProviderName': 'Cognito',
                'ProviderAttributeName': 'cognito:username',
                'ProviderAttributeValue': username
            },
            SourceUser={
                'ProviderName': provider_name,
                'ProviderAttributeName': provider_email_attribute,
                'ProviderAttributeValue': email
            }
        )

    def admin_remove_user_as_admin(self, username: str):
        self.admin_remove_user_from_group(username=username, group_name=self.admin_group_name)

        # todo: Remove once use of RES specific groups is removed
        for admin_group in constants.RES_ADMIN_GROUPS:
            try:
                self._logger.info(f'Removing username {username} from RES_ADMIN_GROUP: {admin_group}')
                self._context.accounts.remove_users_from_group([username], admin_group)
            except Exception as e:
                self._logger.debug(f"Could not add user {username} to RES_ADMIN_GROUP: {admin_group}")

    def admin_remove_user_from_group(self, username: str, group_name: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        self._context.aws().cognito_idp().admin_remove_user_from_group(
            UserPoolId=self.user_pool_id,
            Username=username,
            GroupName=group_name
        )

    def password_updated(self, username: str):
        if not self.is_activedirectory():
            return

        password_max_age = self._context.config().get_int('directoryservice.password_max_age', required=True)
        self._context.aws().cognito_idp().admin_update_user_attributes(
            UserPoolId=self.user_pool_id,
            Username=username,
            UserAttributes=[
                {
                    'Name': 'custom:password_last_set',
                    'Value': str(Utils.current_time_ms())
                },
                {
                    'Name': 'custom:password_max_age',
                    'Value': str(password_max_age)
                }
            ]
        )

    def admin_set_password(self, username: str, password: str, permanent: bool = False):
        try:
            self._context.aws().cognito_idp().admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=username,
                Password=password,
                Permanent=permanent
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvalidPasswordException':
                self._logger.error(f"Username: {username} - Failed Cognito password policy. Deleting User..")
                self.admin_delete_user(username=username)
                raise exceptions.invalid_params('Password does not confirm to Cognito user pool policy')
            else:
                # Should we still delete the user with any other exception?
                raise e

        self.password_updated(username)

        self._context.cache().short_term().delete(self.build_user_cache_key(username))
        self._logger.info(f'SetPassword: {username}, Permanent: {permanent}')

    def admin_reset_password(self, username: str):
        self._context.aws().cognito_idp().admin_reset_user_password(
            UserPoolId=self.user_pool_id,
            Username=username,
        )
        self._context.cache().short_term().delete(self.build_user_cache_key(username))
        self._logger.info(f'ResetPassword: {username}')

    def admin_update_email(self, username: str, email: str, email_verified: bool = False):
        self._context.aws().cognito_idp().admin_update_user_attributes(
            UserPoolId=self.user_pool_id,
            Username=username,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                },
                {
                    'Name': 'email_verified',
                    'Value': str(email_verified)
                }
            ]
        )
        self._context.cache().short_term().delete(self.build_user_cache_key(username))

    def admin_set_email_verified(self, username: str):
        self._context.aws().cognito_idp().admin_update_user_attributes(
            UserPoolId=self.user_pool_id,
            Username=username,
            UserAttributes=[
                {
                    'Name': 'email_verified',
                    'Value': 'true'
                }
            ]
        )
        self._context.cache().short_term().delete(self.build_user_cache_key(username))

    def admin_global_sign_out(self, username: str):
        self._context.aws().cognito_idp().admin_user_global_sign_out(
            UserPoolId=self.user_pool_id,
            Username=username
        )

    def initiate_username_password_auth(self, request: InitiateAuthRequest) -> InitiateAuthResult:

        username = request.username
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required.')

        password = request.password
        if Utils.is_empty(password):
            raise exceptions.invalid_params('password is required.')

        # In SSO-enabled mode - local auth is not allowed except for clusteradmin
        cluster_admin_username = self._context.config().get_string('cluster.administrator_username', required=True)
        sso_enabled = self._context.config().get_bool('identity-provider.cognito.sso_enabled', required=True)
        if sso_enabled and (username != cluster_admin_username):
            self._logger.error(f"Ignoring local authentication request with SSO enabled. Username: {username}")
            raise exceptions.unauthorized_access(f"Ignoring local authentication request with SSO enabled. Username: {username}")
        try:
            cognito_result = self._context.aws().cognito_idp().admin_initiate_auth(
                AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                    'SECRET_HASH': self.get_secret_hash(username)
                },
                UserPoolId=self.user_pool_id,
                ClientId=self.get_client_id()
            )
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ('NotAuthorizedException', 'UserNotFoundException'):
                raise exceptions.unauthorized_access('Invalid username or password')
            elif error_code == 'PasswordResetRequiredException':
                raise exceptions.soca_exception(
                    error_code=errorcodes.AUTH_PASSWORD_RESET_REQUIRED,
                    message='Password reset required for the user'
                )
            else:
                raise e

        auth_result = None
        challenge_name = None
        challenge_params = None
        session = None

        cognito_auth_result = Utils.get_value_as_dict('AuthenticationResult', cognito_result)
        if cognito_auth_result is None:
            challenge_name = Utils.get_value_as_string('ChallengeName', cognito_result)
            challenge_params = Utils.get_value_as_dict('ChallengeParameters', cognito_result)
            session = Utils.get_value_as_string('Session', cognito_result)
        else:
            auth_result = self.build_auth_result(cognito_auth_result)

        return InitiateAuthResult(
            challenge_name=challenge_name,
            challenge_params=challenge_params,
            session=session,
            auth=auth_result
        )

    def respond_to_auth_challenge(self, request: RespondToAuthChallengeRequest) -> RespondToAuthChallengeResult:
        cognito_result = self._context.aws().cognito_idp().admin_respond_to_auth_challenge(
            UserPoolId=self.user_pool_id,
            ClientId=self.options.client_id,
            ChallengeName=request.challenge_name,
            Session=request.session,
            ChallengeResponses={
                'USERNAME': request.username,
                'NEW_PASSWORD': request.new_password,
                'SECRET_HASH': self.get_secret_hash(request.username)
            }
        )

        auth_result = None
        challenge_name = None
        challenge_params = None
        session = None

        cognito_auth_result = Utils.get_value_as_dict('AuthenticationResult', cognito_result)
        if cognito_auth_result is None:
            challenge_name = Utils.get_value_as_string('ChallengeName', cognito_result)
            challenge_params = Utils.get_value_as_dict('ChallengeParameters', cognito_result)
            session = Utils.get_value_as_string('Session', cognito_result)
        else:
            self.admin_set_email_verified(request.username)
            self.password_updated(request.username)
            auth_result = self.build_auth_result(cognito_auth_result)
            self._context.cache().short_term().delete(self.build_user_cache_key(request.username))

        return RespondToAuthChallengeResult(
            challenge_name=challenge_name,
            challenge_params=challenge_params,
            session=session,
            auth=auth_result
        )

    def initiate_refresh_token_auth(self, username: str, refresh_token: str, sso: bool = False):

        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required.')

        if Utils.is_empty(refresh_token):
            raise exceptions.invalid_params('refresh_token is required.')

        try:
            cognito_result = self._context.aws().cognito_idp().admin_initiate_auth(
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token,
                    'SECRET_HASH': self.get_secret_hash(username, sso)
                },
                UserPoolId=self.user_pool_id,
                ClientId=self.get_client_id(sso)
            )
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                raise exceptions.unauthorized_access('Refresh token invalid or expired')
            else:
                raise e

        cognito_auth_result = Utils.get_value_as_dict('AuthenticationResult', cognito_result)
        auth_result = self.build_auth_result(cognito_auth_result)
        return RespondToAuthChallengeResult(
            auth=auth_result
        )

    def forgot_password(self, username: str):
        try:
            self._context.aws().cognito_idp().forgot_password(
                ClientId=self.options.client_id,
                SecretHash=self.get_secret_hash(username),
                Username=username
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                # return success response even for user not found failures to mitigate user enumeration risks
                pass
            else:
                raise e

    def confirm_forgot_password(self, username: str, password: str, confirmation_code: str):
        self._context.aws().cognito_idp().confirm_forgot_password(
            ClientId=self.options.client_id,
            SecretHash=self.get_secret_hash(username),
            Username=username,
            Password=password,
            ConfirmationCode=confirmation_code
        )
        self.password_updated(username)
        self._context.cache().short_term().delete(self.build_user_cache_key(username))

    def change_password(self, username: str, access_token: str, old_password: str, new_password: str):
        self._context.aws().cognito_idp().change_password(
            AccessToken=access_token,
            PreviousPassword=old_password,
            ProposedPassword=new_password
        )
        self.password_updated(username)

    def describe_password_policy(self) -> CognitoUserPoolPasswordPolicy:
        try:
            describe_result = self._context.aws().cognito_idp().describe_user_pool(
                UserPoolId=self.user_pool_id
            )
        except botocore.exceptions.ClientError as e:
            raise e
        user_pool = Utils.get_value_as_dict('UserPool', describe_result)
        policies = Utils.get_value_as_dict('Policies', user_pool)
        password_policy = Utils.get_value_as_dict('PasswordPolicy', policies)
        minimum_length = Utils.get_value_as_int('MinimumLength', password_policy, 8)
        require_uppercase = Utils.get_value_as_bool('RequireUppercase', password_policy, True)
        require_lowercase = Utils.get_value_as_bool('RequireLowercase', password_policy, True)
        require_numbers = Utils.get_value_as_bool('RequireNumbers', password_policy, True)
        require_symbols = Utils.get_value_as_bool('RequireSymbols', password_policy, True)
        temporary_password_validity_days = Utils.get_value_as_int('TemporaryPasswordValidityDays', password_policy, 7)
        return CognitoUserPoolPasswordPolicy(
            minimum_length=minimum_length,
            require_uppercase=require_uppercase,
            require_lowercase=require_lowercase,
            require_numbers=require_numbers,
            require_symbols=require_symbols,
            temporary_password_validity_days=temporary_password_validity_days
        )
