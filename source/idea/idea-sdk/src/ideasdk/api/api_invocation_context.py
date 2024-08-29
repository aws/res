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
import urllib.parse

from ideasdk.protocols import SocaContextProtocol, ApiInvocationContextProtocol, SocaContextProtocolType
from ideasdk.auth import TokenService, ApiAuthorizationServiceBase
from ideadatamodel.api.api_model import ApiAuthorization, ApiAuthorizationType
from ideasdk.utils import Utils, GroupNameHelper
from ideadatamodel import constants, get_payload_as, SocaEnvelope, SocaPayload, exceptions, errorcodes

from typing import Optional, Dict, Mapping, Type, TypeVar, Union, List
import logging
import re

T = TypeVar('T')

PATTERN_NAMESPACE = r'^[A-Za-z0-9]+.{1}[A-Za-z0-9]+$'
PATTERN_REQUEST_ID = r'^[0-9a-zA-Z-_]+$'


class ApiInvocationContext(ApiInvocationContextProtocol):
    """
    API Invocation Context
    * wraps all applicable parameters / payload and  for a given API request and exposes functionality
    to perform authorization
    * exposes utilities for request / response flows

    A new instance of ApiInvocationContext is created for each API invocation by `SocaServer` -> `ApiInvocationHandler`
    """

    def __init__(self, context: SocaContextProtocol,
                 request: Union[Dict, SocaEnvelope],
                 http_headers: Optional[Mapping],
                 invocation_source: str,
                 group_name_helper: GroupNameHelper,
                 logger: logging.Logger,
                 token: Optional[Dict] = None,
                 token_service: Optional[TokenService] = None,
                 api_authorization_service: Optional[ApiAuthorizationServiceBase] = None):
        self._context = context
        self._request = request
        self._http_headers = http_headers
        self._invocation_source = invocation_source
        self._group_name_helper = group_name_helper
        self._logger = logger
        self._token = token
        self._token_service = token_service
        self._api_authorization_service = api_authorization_service

        self._start_time = Utils.current_time_ms()
        self._total_time: Optional[int] = None
        self._response: Optional[Dict] = None
        self._exception: Optional[BaseException] = None
        self._decoded_token: Optional[Dict] = None
        self._authorization: Optional[ApiAuthorization] = None

    @property
    def context(self) -> SocaContextProtocolType:
        return self._context

    @property
    def request(self) -> Dict:
        return self._request

    def get_request(self, deep_copy: bool = False) -> Dict:
        if deep_copy:
            return Utils.deep_copy(self._request)
        return self._request

    @property
    def response(self) -> Dict:
        return self._response

    def get_response(self, deep_copy: bool = False) -> Dict:
        if deep_copy:
            return Utils.deep_copy(self._response)
        return self._response

    @property
    def access_token(self) -> Optional[str]:
        token_type = Utils.get_value_as_string('token_type', self._token)
        if token_type != 'Bearer':
            return None
        return Utils.get_value_as_string('token', self._token)

    def is_access_token_expired(self) -> bool:
        access_token = self.access_token
        if Utils.is_empty(access_token):
            return True
        if self._token_service is None:
            return True
        return self._token_service.is_token_expired(token=access_token)

    def is_scope_authorized(self, scope: str) -> bool:
        access_token = self.access_token
        if Utils.is_empty(access_token):
            return False
        if not self._api_authorization_service or not self._token_service:
            return False
        decoded_token = self._token_service.decode_token(token=access_token)
        return self._api_authorization_service.is_scope_authorized(decoded_token=decoded_token, scope=scope)

    def is_unix_domain_socket_invocation(self) -> bool:
        """
        invocation source can be set by `SocaServer` during an api invocation

        the source of the request is set as 'unix-socket' when a user with sudo access
        performs operations via `resctl`
        """
        return self._invocation_source == 'unix-socket'

    def is_administrator(self, authorization: ApiAuthorization = None) -> bool:
        """
        check if user has "administrator" access
        """
        if not authorization:
            authorization = self.get_authorization()
        return authorization.type == ApiAuthorizationType.ADMINISTRATOR

    def is_authenticated_user(self, authorization: ApiAuthorization = None) -> bool:
        """
        allow any request as long as the token is issued to a valid user
        verify the token, but don't check for any scope access
        """
        if not authorization:
            authorization = self.get_authorization()
        return authorization.type in (
            ApiAuthorizationType.USER,
            ApiAuthorizationType.ADMINISTRATOR
        )

    def is_authenticated_app(self, authorization: ApiAuthorization = None) -> bool:
        """
        allow any request as long as the token is issued to a valid app
        verify the token, but don't check for any scope access
        """
        if not authorization:
            authorization = self.get_authorization()
        return authorization.type == ApiAuthorizationType.APP

    def is_authenticated(self) -> bool:
        """
        allow any request as long as the token is valid
        verify the token, but don't check for any groups or scope access
        """
        authorization = self.get_authorization()
        return True

    def is_authorized_user(self, authorization: ApiAuthorization = None, role_assignment_resource_key: Optional[str] = None, permission: Optional[str] = None) -> bool:
        """
        check if a user is authorized
        admins are implicitly authorized
        """

        if not authorization:
            authorization = self.get_authorization()

        # administrator with sudo access
        if self.is_administrator(authorization=authorization):
            return True

        # We delegate authorization check to API authorization service.
        # This will also check for role assignments, if needed based on the current API namespace
        return self._api_authorization_service.is_user_authorized(authorization=authorization, namespace=self.namespace, role_assignment_resource_key=role_assignment_resource_key, permission=permission)

    def is_authorized_app(self, authorization: ApiAuthorization = None) -> bool:
        if not authorization:
            authorization = self.get_authorization()
        if authorization.type != ApiAuthorizationType.APP:
            return False
        if authorization.scopes is None or len(authorization.scopes) == 0:
            return False

        # if any scope is granted to perform read/write operations for the module, return True
        # in the future, this can be refined further to create scopes per API, eg. <MODULE_ID>/<COMPONENT>-read
        module_read_scope = f'{self._context.module_id()}/read'
        module_write_scope = f'{self._context.module_id()}/write'
        for scope in authorization.scopes:
            if scope in (module_read_scope, module_write_scope):
                return True

        return False

    def is_authorized(self, elevated_access: bool, scopes: Optional[List[str]] = None, role_assignment_resource_key: Optional[str] = None, permission: Optional[str] = None):
        """
        method to check if the invocation is authorized
        this method combines check for both user + app authorizations to simplify and abstract
        authorization check implementation across all APIs

        although scopes can be passed to this method, user and app authorization are mutually exclusive:
        * `elevated_access` is applicable for user authorization when user has to be admin
        * `scopes` is applicable for app authorization
        * `role_assignment_resource_key` is applicable for user authorization when user need not be admin

        :param bool elevated_access: indicate if APIs need elevated access such as admin or manager.
        :param List[str] scopes: the applicable scopes to be checked
        :return:
        """
        authorization = self.get_authorization()
        if elevated_access:
            authorized_user = self.is_administrator(authorization=authorization)
        else:
            authorized_user = self.is_authorized_user(authorization=authorization, role_assignment_resource_key=role_assignment_resource_key, permission=permission)

        authorized_scopes = False
        if Utils.is_not_empty(scopes):
            authorized_app = self.is_authorized_app(authorization=authorization)
            if authorized_app:
                all_scopes_authorized = True
                for scope in scopes:
                    if not self.is_scope_authorized(scope):
                        all_scopes_authorized = False
                        break
                authorized_scopes = all_scopes_authorized

        return authorized_user or authorized_scopes

    def get_username(self) -> Optional[str]:
        """
        get username from the JWT access token
        should be used for all authenticated APIs to ensure username cannot be spoofed via any payload parameters
        """
        if not self._api_authorization_service :
            return None
        authorization = self.get_authorization()
        return authorization.username

    @response.setter
    def response(self, response: Union[SocaEnvelope, Dict]):
        if isinstance(response, SocaEnvelope):
            self._response = response.dict(exclude_none=True, by_alias=True)
        else:
            self._response = response

    def is_success(self) -> bool:
        response = self.response
        if Utils.is_empty(response):
            return False
        return Utils.get_value_as_bool('success', self.response, False)

    def success(self, payload: Union[SocaPayload, Dict] = None):
        if isinstance(payload, SocaPayload):
            payload_dict = payload.dict(exclude_none=True, by_alias=True)
        else:
            payload_dict = payload

        if self._response is None:
            self._response = {
                'header': self.header,
                'success': True,
                'payload': payload_dict
            }
        else:
            self._response['success'] = True
            self._response['payload'] = payload_dict

    def fail(self, error_code: str, message: str, payload: Union[SocaPayload, Dict] = None):

        payload_dict = None
        if payload is not None:
            if isinstance(payload, SocaPayload):
                payload_dict = payload.dict(exclude_none=True, by_alias=True)
            else:
                payload_dict = payload

        if self._response is None:
            self._response = {}

        self._response['header'] = self.header
        self._response['success'] = False
        self._response['error_code'] = error_code
        self._response['message'] = message
        self._response['payload'] = payload_dict

    def exception(self, e: BaseException):
        self._exception = e
        if isinstance(e, exceptions.SocaException):
            message = e.message
            error_code = e.error_code
            if e.ref is not None and isinstance(e.ref, Exception):
                message += f'(RootCause: {e.ref})'
        else:
            error_code = errorcodes.GENERAL_ERROR
            message = f'Unhandled Exception: {e}'
        self.fail(error_code, message)

    @property
    def exc(self) -> BaseException:
        return self._exception

    @property
    def header(self) -> Dict:
        header = Utils.get_value_as_dict('header', self.request)
        escaped_header = {}
        for key, value in header.items():
            # Replace special characters in string using the %xx escape. Encoding is using utf-8 and ignores safe URL characters /:?=& that are reserved as part of RFC 3986
            escaped_key = urllib.parse.quote_plus(key, safe='/:?=&') if isinstance(key, str) else key
            escaped_value = urllib.parse.quote_plus(value, safe='/:?=&') if isinstance(value, str) else value
            escaped_header[escaped_key] = escaped_value
        return escaped_header

    @property
    def namespace(self) -> str:
        return Utils.get_value_as_string('namespace', self.header)

    @property
    def request_id(self) -> str:
        return Utils.get_value_as_string('request_id', self.header)
    
    @property
    def request_payload(self) -> Dict:
        return Utils.get_value_as_dict('payload', self.request, default={})

    def get_request_payload_as(self, payload_type: Type[T]) -> T:
        return get_payload_as(payload=self.request_payload, payload_type=payload_type)

    @property
    def response_payload(self) -> Dict:
        return Utils.get_value_as_dict('payload', self.response)

    @property
    def error_code(self) -> Optional[str]:
        return Utils.get_value_as_string('error_code', self.response)

    def get_response_payload_as(self, payload_type: Type[T]):
        return get_payload_as(payload=self.response_payload, payload_type=payload_type)

    def has_access_token(self) -> bool:
        return Utils.is_not_empty(self.access_token)

    def get_decoded_token(self) -> Optional[Dict]:
        if self._decoded_token is not None:
            return self._decoded_token

        access_token = self.access_token
        if Utils.is_empty(access_token):
            return None

        self._decoded_token = self._token_service.decode_token(access_token)
        return self._decoded_token

    def get_authorization(self) -> ApiAuthorization:
        if self._authorization is not None:
            return self._authorization

        if self.is_unix_domain_socket_invocation():
            result = ApiAuthorization(
                username=self.context.config().get_string('cluster.administrator_username', required=True),
                type=ApiAuthorizationType.ADMINISTRATOR,
                invocation_source=constants.API_INVOCATION_SOURCE_UNIX_SOCKET
            )
        elif self.has_access_token():
            decoded_token = self.get_decoded_token()
            result = self._api_authorization_service.get_authorization(decoded_token)
            result.invocation_source = constants.API_INVOCATION_SOURCE_HTTP
        elif Utils.is_test_mode():
            username = Utils.get_value_as_string('X_RES_TEST_USERNAME', self._http_headers)
            self._logger.warning(f'User {username} is accessing API without a valid token; '
                                 'This is only possible because the environment variable RES_TEST_MODE is set to True.  '
                                 'If this is not intended, remove the environment variable RES_TEST_MODE and restart the server.')

            if not username:
                raise exceptions.unauthorized_access()
            user = self._api_authorization_service.get_user_from_token_username(token_username=username)
            result = ApiAuthorization(
                username=username,
                type=self._api_authorization_service.get_authorization_type(role=user.role),
                invocation_source=constants.API_INVOCATION_SOURCE_HTTP
            )
        else:
            raise exceptions.unauthorized_access()

        self._authorization = result
        return self._authorization

    def get_start_time_ms(self) -> int:
        return self._start_time

    def get_total_time_ms(self) -> int:
        if self._total_time is not None:
            return self._total_time
        self._total_time = Utils.current_time_ms() - self.get_start_time_ms()
        return self._total_time

    def validate_request(self):
        header = self.header
        if Utils.is_empty(header):
            raise exceptions.invalid_params('header is required')
        namespace = self.namespace
        if Utils.is_empty(namespace):
            raise exceptions.invalid_params('namespace is required')
        if not re.match(PATTERN_NAMESPACE, namespace):
            raise exceptions.invalid_params(f'namespace must satisfy regex: {PATTERN_NAMESPACE}')

        request_id = self.request_id
        if Utils.is_not_empty(request_id):
            if not re.match(PATTERN_REQUEST_ID, request_id):
                raise exceptions.invalid_params(f'request_id must satisfy regex: {PATTERN_REQUEST_ID}')

    def is_valid_request(self) -> bool:
        try:
            self.validate_request()
            return True
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.INVALID_PARAMS:
                return False
            else:
                raise e

    # begin: audit logging methods

    def is_payload_tracing_enabled(self) -> bool:
        return self._context.config().get_bool('cluster.logging.audit_logs.enable_payload_tracing', default=False)

    def get_log_tag(self) -> str:

        client_id = None
        invocation_source = None

        try:
            authorization = self.get_authorization()
            client_id = authorization.client_id
            authorization_type = authorization.type
            invocation_source = authorization.invocation_source
            if authorization_type == ApiAuthorizationType.APP:
                actor = 'app'
            else:
                actor = self.get_username()
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.UNAUTHORIZED_ACCESS:
                actor = 'unknown'
                authorization_type = 'public'
            else:
                raise e

        enabled_tags = self._context.config().get_list('cluster.logging.audit_logs.tags', default=[])

        tags = []

        if 'actor' in enabled_tags:
            tags.append(f'actor:{actor}')

        if 'auth_type' in enabled_tags:
            tags.append(f'auth:{authorization_type}')

        if 'client_id' in enabled_tags and Utils.is_not_empty(client_id):
            tags.append(f'client_id:{client_id}')

        if 'request_id' in enabled_tags and Utils.is_not_empty(self.request_id):
            tags.append(f'request_id:{self.request_id}')

        if 'protocol' in enabled_tags and Utils.is_not_empty(invocation_source):
            tags.append(f'protocol:{invocation_source}')

        return f'{"|".join(tags)}'

    def log_request(self, request: Optional[Dict] = None):
        if self.is_payload_tracing_enabled():
            if request is None:
                request = self.request
            self._logger.info(f'(req) [{self.get_log_tag()}] {Utils.to_json(request)}')
        else:
            self._logger.info(f'(req) [{self.get_log_tag()}] {self.namespace}')

    def log_response(self, response: Optional[Dict] = None):
        success = Utils.get_value_as_bool('success', self.response, False)
        if response is None:
            response = self.response

        if success:
            if self.is_payload_tracing_enabled():
                self._logger.info(f'(res) [{self.get_log_tag()}] {Utils.to_json(response)} ({self.get_total_time_ms()} ms)')
            else:
                self._logger.info(f'(res) [{self.get_log_tag()}] {self.namespace} ({self.get_total_time_ms()} ms) [OK]')
        else:
            if self.is_payload_tracing_enabled():
                self._logger.info(f'(res) [{self.get_log_tag()}] {Utils.to_json(response)} ({self.get_total_time_ms()} ms)')
            else:
                error_code = Utils.get_value_as_string('error_code', response)
                self._logger.info(f'(res) [{self.get_log_tag()}] {self.namespace} ({self.get_total_time_ms()} ms) [{error_code}]')

    def log_info(self, message: str):
        self._logger.info(f'[{self.get_log_tag()}] {message}')

    def log_error(self, message: str):
        self._logger.error(f'[{self.get_log_tag()}] {message}')

    def log_exception(self, message: str):
        self._logger.exception(f'[{self.get_log_tag()}] {message}')

    def log_debug(self, message: str):
        self._logger.debug(f'[{self.get_log_tag()}] {message}')

    # end: audit logging methods
