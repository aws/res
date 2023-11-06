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
    'TokenServiceOptions',
    'ApiAuthorization',
    'ApiAuthorizationType',
    'TokenService'
)

from ideasdk.protocols import SocaContextProtocol, TokenServiceProtocol
from ideadatamodel import SocaBaseModel, AuthResult, exceptions, errorcodes
from ideasdk.utils import Utils

from typing import Optional, Dict, List
import jwt
from jwt import PyJWKClient
import requests
from threading import RLock
from enum import Enum

DEFAULT_JWK_CACHE_KEYS = True
DEFAULT_JWK_MAX_CACHED_KEYS = 16
DEFAULT_KEY_ALGORITHM = 'RS256'


class TokenServiceOptions(SocaBaseModel):
    # provider_url is of format: https://cognito-idp.us-east-1.amazonaws.com/[user-pool-id]
    # this is used to construct .well-known/jwks.json url
    cognito_user_pool_provider_url: Optional[str]

    # domain_url is used to access OAuth2 based services such as /oauth2/token to fetch an access token
    # domain url is of the format: https://[domain-name].auth.[aws-region].amazoncognito.com
    cognito_user_pool_domain_url: Optional[str]

    jwk_cache_keys: Optional[bool]
    jwk_max_cached_keys: Optional[int]
    key_algorithm: Optional[str]

    client_id: Optional[str]
    client_secret: Optional[str]
    client_credentials_scope: Optional[List[str]]

    refresh_token: Optional[str]

    administrators_group_name: Optional[str]
    managers_group_name: Optional[str]


class ApiAuthorizationType(str, Enum):
    ADMINISTRATOR = 'admin'
    MANAGER = 'manager'
    USER = 'user'
    APP = 'app'


class ApiAuthorization(SocaBaseModel):
    type: ApiAuthorizationType
    username: Optional[str]  # will not exist for APP authorizations
    client_id: Optional[str]
    groups: Optional[List[str]]  # list of all groups user is part of
    scopes: Optional[List[str]]  # list of allowed oauth scopes
    invocation_source: Optional[str]


class TokenService(TokenServiceProtocol):

    def __init__(self, context: SocaContextProtocol, options: TokenServiceOptions):
        self._context = context
        self._logger = context.logger('token-service')

        self.validate_options(options)
        self.options = options

        self._client_id = options.client_id
        self._client_secret = options.client_secret

        self._jwk: Optional[PyJWKClient] = PyJWKClient(
            uri=self.cognito_well_known_url,
            cache_keys=Utils.get_as_bool(options.jwk_cache_keys, DEFAULT_JWK_CACHE_KEYS),
            max_cached_keys=Utils.get_as_int(options.jwk_max_cached_keys, DEFAULT_JWK_MAX_CACHED_KEYS)
        )

        self._client_credentials_grant: Optional[AuthResult] = None
        self._client_credentials_lock = RLock()

        self._refresh_token_grant: Optional[AuthResult] = None
        self._refresh_token_lock = RLock()

        self._sso_client_id: Optional[str] = None
        self._sso_client_secret: Optional[str] = None

    @staticmethod
    def validate_options(options: TokenServiceOptions):
        if Utils.is_empty(options.cognito_user_pool_provider_url):
            raise exceptions.soca_exception(
                error_code=errorcodes.CONFIG_ERROR,
                message='options.cognito_user_pool_provider_url is required. '
            )

        if Utils.is_empty(options.cognito_user_pool_domain_url):
            raise exceptions.soca_exception(
                error_code=errorcodes.CONFIG_ERROR,
                message='options.cognito_user_pool_domain_url is required'
            )

    @property
    def key_algorithm(self) -> str:
        return Utils.get_as_string(self.options.key_algorithm, DEFAULT_KEY_ALGORITHM)

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def client_secret(self) -> str:
        return self._client_secret

    @property
    def cognito_well_known_url(self) -> str:
        return f'{self.options.cognito_user_pool_provider_url}/.well-known/jwks.json'

    @property
    def cognito_user_pool_domain_url(self) -> str:
        return self.options.cognito_user_pool_domain_url

    @property
    def oauth2_access_token_url(self) -> str:
        return f'{self.cognito_user_pool_domain_url}/oauth2/token'

    @property
    def oauth2_revoke_url(self) -> str:
        return f'{self.cognito_user_pool_domain_url}/oauth2/revoke'

    @property
    def client_credentials_scope(self) -> str:
        return ' '.join(self.options.client_credentials_scope)

    def get_access_token_using_client_credentials(self, force_renewal=True) -> AuthResult:
        """
        fetches the access token using client_credentials grant type.

        this method should be used by soca apps such as scheduler, virtualdesktop to communicate with dependent services such
        as authentication.

        Refer to: https://aws.amazon.com/blogs/mobile/understanding-amazon-cognito-user-pool-oauth-2-0-grants/ -> Client credentials grant
        to know more about OAuth 2.0 client_credentials grant.

        :param force_renewal: force renew the token instead of returning the cached AuthResult
        :return: AuthResult
        """

        client_id = self.client_id
        client_secret = self.client_secret

        if Utils.is_any_empty(client_id, client_secret):
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message='options.client_id and options.client_secret is required.'
            )

        if Utils.is_empty(self.options.client_credentials_scope):
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message='options.client_credentials_scope is required'
            )

        def get_cached_grant() -> Optional[AuthResult]:
            if force_renewal:
                return None
            if self._client_credentials_grant is None:
                return None
            access_token_ = self._client_credentials_grant.access_token
            if self.is_token_expired(access_token_):
                return None
            return self._client_credentials_grant

        access_token = get_cached_grant()
        if access_token is not None:
            return access_token

        with self._client_credentials_lock:

            # check again
            access_token = get_cached_grant()
            if access_token is not None:
                return access_token

            access_token_url = self.oauth2_access_token_url
            basic_auth = Utils.encode_basic_auth(client_id, client_secret)
            scope = self.client_credentials_scope

            response = requests.post(
                url=access_token_url,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': f'Basic {basic_auth}'
                },
                data={
                    'grant_type': 'client_credentials',
                    'scope': scope
                }
            )
            result = response.json()

            self._client_credentials_grant = AuthResult(
                access_token=Utils.get_value_as_string('access_token', result),
                expires_in=Utils.get_value_as_int('expires_in', result),
                token_type=Utils.get_value_as_string('token_type', result)
            )
            return self._client_credentials_grant

    def get_access_token_using_refresh_token(self, force_renewal=True) -> AuthResult:
        """
        renew the cached access token if expired, or return a new AuthResult using refresh token
        :param force_renewal: force renew the token instead of returning the cached AuthResult
        :return:
        """
        if Utils.is_empty(self.options.refresh_token):
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message='options.refresh_token is required.'
            )

        def get_cached_grant() -> Optional[AuthResult]:
            if force_renewal:
                return None
            if self._refresh_token_grant is None:
                return None
            access_token_ = self._refresh_token_grant.access_token
            if self.is_token_expired(access_token_):
                return None
            return self._refresh_token_grant

        auth_result = get_cached_grant()
        if auth_result is not None:
            return auth_result

        with self._refresh_token_lock:

            # check again
            access_token = get_cached_grant()
            if access_token is not None:
                return access_token

            access_token_url = self.oauth2_access_token_url

            response = requests.post(
                url=access_token_url,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.options.refresh_token
                }
            )
            result = response.json()

            self._refresh_token_grant = AuthResult(
                access_token=Utils.get_value_as_string('access_token', result),
                expires_in=Utils.get_value_as_int('expires_in', result),
                token_type=Utils.get_value_as_string('token_type', result)
            )
            return self._refresh_token_grant

    def decode_token(self, token: str, verify_exp: Optional[bool] = True) -> Dict:
        """
        decodes the JWT token and verifies signature and expiration.

        should be used by all daemon services that expose a public API to validate tokens and authorize API resources using scope or
        additional metadata from the token.

        :param token: the JWT token.
        :param verify_exp: indicates if expiration time should be verified. useful in scenarios where the token could be expired, but
        service needs to extract other information from the token.
        :return: A dict object of decoded token.
        :raises AUTH_TOKEN_EXPIRED if token is expired.
        :raises UNAUTHORIZED_ACCESS if token is invalid
        """
        try:

            if Utils.is_empty(token):
                raise exceptions.unauthorized_access()

            signing_key = self._jwk.get_signing_key_from_jwt(token)
            decoded_token = jwt.decode(
                token,
                signing_key.key,
                algorithms=[self.key_algorithm],
                options={
                    'verify_exp': verify_exp
                }
            )
            return decoded_token
        except jwt.ExpiredSignatureError:
            # these are normal errors, and will occur during everyday operations
            # clients should renew the access token upon receiving this error code.
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_TOKEN_EXPIRED,
                message=f'Token Expired'
            )
        except jwt.InvalidTokenError as e:
            # this is not normal, and log entries should be monitored to check why tokens are invalid.
            self._logger.error(f'Invalid Token: {e}')
            raise exceptions.unauthorized_access(f'Invalid Token - {e}')

    def is_token_expired(self, token: str) -> bool:
        """
        check if the token is expired
        :param token: token can be idToken, accessToken or any valid JWT Token
        :return:
        """
        try:
            self.decode_token(token)
            return False
        except jwt.ExpiredSignatureError:
            return True

    def get_authorization(self, decoded_token: Optional[Dict]) -> ApiAuthorization:
        username = Utils.get_value_as_string('username', decoded_token)
        groups = Utils.get_value_as_list('cognito:groups', decoded_token, [])
        token_scope = Utils.get_value_as_string('scope', decoded_token)
        client_id = Utils.get_value_as_string('client_id', decoded_token)
        scopes = None
        if Utils.is_not_empty(token_scope):
            scopes = token_scope.split(' ')

        authorization_type = None
        if Utils.is_not_empty(self.options.administrators_group_name) and self.options.administrators_group_name in groups:
            authorization_type = ApiAuthorizationType.ADMINISTRATOR
        elif Utils.is_not_empty(self.options.administrators_group_name) and self.options.managers_group_name in groups:
            authorization_type = ApiAuthorizationType.MANAGER

        if Utils.is_empty(username):
            authorization_type = ApiAuthorizationType.APP

        if authorization_type is None:
            authorization_type = ApiAuthorizationType.USER

        return ApiAuthorization(
            type=authorization_type,
            username=username,
            scopes=scopes,
            groups=groups,
            client_id=client_id
        )

    def is_scope_authorized(self, access_token: str, scope: str, verify_exp=True) -> bool:
        access_token = access_token
        if Utils.is_empty(access_token):
            return False
        if Utils.is_empty(scope):
            return False

        decoded_token = self.decode_token(access_token, verify_exp=verify_exp)
        authorization = self.get_authorization(decoded_token)
        if authorization.type != ApiAuthorizationType.APP:
            return False
        return Utils.is_not_empty(authorization.scopes) and scope in authorization.scopes

    def is_administrator(self, access_token: str, verify_exp=True) -> bool:
        access_token = access_token
        if Utils.is_empty(access_token):
            return False
        administrators_group_name = self.options.administrators_group_name
        if Utils.is_empty(administrators_group_name):
            return False
        decoded_token = self.decode_token(access_token, verify_exp=verify_exp)
        authorization = self.get_authorization(decoded_token)
        return authorization.type == ApiAuthorizationType.ADMINISTRATOR

    def is_manager(self, access_token: str, verify_exp=True) -> bool:
        access_token = access_token
        if Utils.is_empty(access_token):
            return False
        managers_group_name = self.options.managers_group_name
        if Utils.is_empty(managers_group_name):
            return False

        decoded_token = self.decode_token(access_token, verify_exp=verify_exp)
        authorization = self.get_authorization(decoded_token)
        return authorization.type == ApiAuthorizationType.MANAGER

    def get_username(self, access_token: str, verify_exp=True) -> Optional[str]:
        if Utils.is_empty(access_token):
            return None
        decoded_token = self.decode_token(access_token, verify_exp=verify_exp)
        return Utils.get_value_as_string('username', decoded_token)

    def get_access_token(self, force_renewal=True) -> Optional[str]:
        auth_result = None

        if Utils.is_not_empty(self.options.refresh_token):
            auth_result = self.get_access_token_using_refresh_token(force_renewal)
        if not Utils.are_empty(self.client_id, self.client_secret):
            auth_result = self.get_access_token_using_client_credentials(force_renewal)

        if auth_result is None:
            return None

        return auth_result.access_token

    def get_access_token_using_sso_auth_code(self, authorization_code: str, redirect_uri: str) -> AuthResult:
        if Utils.is_empty(authorization_code):
            raise exceptions.invalid_params('authorization_code is required')
        if Utils.is_empty(redirect_uri):
            raise exceptions.invalid_params('redirect_uri is required')

        if self._sso_client_id is None or self._sso_client_secret is None:
            client_id = self._context.config().get_string('identity-provider.cognito.sso_client_id', required=True)
            client_secret = self._context.config().get_secret('identity-provider.cognito.sso_client_secret', required=True)
            self._sso_client_id = client_id
            self._sso_client_secret = client_secret

        self._logger.debug(f'sso client_id: {self._sso_client_id}, client_secret: {self._sso_client_secret}')
        basic_auth = Utils.encode_basic_auth(self._sso_client_id, self._sso_client_secret)

        response = requests.post(
            url=self.oauth2_access_token_url,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {basic_auth}'
            },
            data={
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'client_id': self._sso_client_id,
                'redirect_uri': redirect_uri
            }
        )
        result = response.json()

        error = Utils.get_value_as_string('error', result)
        if Utils.is_not_empty(error):
            raise exceptions.unauthorized_access(f'sso authentication failed: {error}')

        self._logger.debug(f'sso access token: {Utils.to_json(result)}')

        return AuthResult(
            access_token=Utils.get_value_as_string('access_token', result),
            refresh_token=Utils.get_value_as_string('refresh_token', result),
            id_token=Utils.get_value_as_string('id_token', result),
            expires_in=Utils.get_value_as_int('expires_in', result),
            token_type=Utils.get_value_as_string('token_type', result)
        )

    def revoke_authorization(self, refresh_token: str, sso_auth: bool = False):

        if Utils.is_empty(refresh_token):
            raise exceptions.invalid_params('refresh_token is required')

        if sso_auth:
            if Utils.is_empty(self._sso_client_id) or Utils.is_empty(self._sso_client_secret) is None:
                self._sso_client_id = self._context.config().get_string('identity-provider.cognito.sso_client_id', required=True)
                self._sso_client_secret = self._context.config().get_secret('identity-provider.cognito.sso_client_secret', required=True)
            client_id = self._sso_client_id
            client_secret = self._sso_client_secret
        else:
            client_id = self.client_id
            client_secret = self.client_secret

        if Utils.is_any_empty(client_id, client_secret):
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message='options.client_id and options.client_secret is required.'
            )

        basic_auth = Utils.encode_basic_auth(client_id, client_secret)

        result = requests.post(
            url=self.oauth2_revoke_url,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {basic_auth}'
            },
            data={
                'token': refresh_token,
                'client_id': client_id
            }
        )

        if result.status_code != 200:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_TOKEN_REVOCATION_FAILED,
                message=f'failed to revoke token: {result.text}'
            )
