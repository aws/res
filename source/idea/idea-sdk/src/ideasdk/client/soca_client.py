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

from ideasdk.protocols import SocaContextProtocol
from ideasdk.utils import Utils
from ideadatamodel import exceptions, errorcodes, SocaBaseModel, SocaEnvelope, SocaHeader, SocaAnyPayload

from typing import Optional, TypeVar, Type, Any, Union
import requests
import requests.adapters
import requests_unixsocket.adapters
import urllib.parse
import requests.exceptions
import warnings
import urllib3.exceptions

T = TypeVar('T')

DEFAULT_CLIENT_TIMEOUT = 60

DEFAULT_POOL_CONNECTIONS = 1
DEFAULT_POOL_MAX_SIZE = 8
DEFAULT_POOL_BLOCK = False
DEFAULT_POOL_TIMEOUT = None
DEFAULT_MAX_RETRIES = 0
DEFAULT_TIMEOUT_SECONDS = 10

SCHEME_HTTP = 'http://'  # noqa
SCHEME_HTTPS = 'https://'
SCHEME_UNIX_HTTP = 'unix+http://'  # noqa
SCHEME_UNIX_HTTPS = 'unix+https://'


class SocaClientOptions(SocaBaseModel):
    enable_logging: Optional[bool]
    endpoint: Optional[str]
    unix_socket: Optional[str]
    timeout: Optional[float]
    pool_connections: Optional[int]
    pool_max_size: Optional[int]
    pool_block: Optional[bool]
    max_retries: Optional[int]
    verify_ssl: Optional[bool]


class SocaClient:

    def __init__(self, context: SocaContextProtocol, options: SocaClientOptions, logger=None):
        self._context = context
        if logger is None:
            self._logger = context.logger('http-client')
        else:
            self._logger = logger

        self.options = options

        pool_connections = Utils.get_as_int(options.pool_connections, DEFAULT_POOL_CONNECTIONS)
        pool_max_size = Utils.get_as_int(options.pool_max_size, DEFAULT_POOL_MAX_SIZE)
        max_retries = Utils.get_as_int(options.max_retries, DEFAULT_MAX_RETRIES)
        pool_block = Utils.get_as_bool(options.pool_block, DEFAULT_POOL_BLOCK)
        timeout = Utils.get_as_int(options.timeout, DEFAULT_CLIENT_TIMEOUT)

        session = requests.Session()
        if self.is_unix_socket():
            adapter = requests_unixsocket.UnixAdapter(
                timeout=timeout,
                pool_connections=pool_connections,
                pool_maxsize=pool_max_size,
                max_retries=max_retries,
                pool_block=pool_block
            )
        else:
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=pool_connections,
                pool_maxsize=pool_max_size,
                max_retries=max_retries,
                pool_block=pool_block
            )

        session.mount(self.get_scheme(), adapter)
        self.session = session

    def is_unix_socket(self) -> bool:
        return Utils.is_not_empty(self.options.unix_socket)

    @property
    def unix_socket(self) -> str:
        return self.options.unix_socket

    def get_scheme(self) -> str:
        endpoint = self.options.endpoint
        unix_socket = self.options.unix_socket
        if endpoint.startswith(SCHEME_HTTPS):
            if Utils.is_empty(unix_socket):
                return SCHEME_HTTPS
            else:
                return SCHEME_UNIX_HTTPS
        elif endpoint.startswith(SCHEME_HTTP):
            if Utils.is_empty(unix_socket):
                return SCHEME_HTTP
            else:
                return SCHEME_UNIX_HTTP

    @property
    def endpoint(self) -> str:
        endpoint = self.options.endpoint
        if self.is_unix_socket():
            quoted = self.unix_socket.replace('/', '%2F')
            path = urllib.parse.urlparse(endpoint).path
            return f'{self.get_scheme()}{quoted}{path}'
        else:
            return endpoint

    @property
    def is_enable_logging(self) -> bool:
        return Utils.get_as_bool(self.options.enable_logging, True)

    @property
    def timeout(self) -> float:
        return Utils.get_as_float(self.options.timeout, DEFAULT_TIMEOUT_SECONDS)

    def invoke(self, request: SocaEnvelope, result_as: Optional[Type[T]] = SocaAnyPayload, access_token: str = None) -> T:
        try:
            header = request.header
            request_id = header.request_id
            if Utils.is_empty(request_id):
                header.request_id = Utils.uuid()

            request_data = Utils.to_json(request)

            if self.is_enable_logging:
                self._logger.info(f'(req) {request_data}')

            headers = {
                'Content-Type': 'application/json'
            }
            if access_token is not None:
                headers['Authorization'] = f'Bearer {access_token}'

            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                http_response = self.session.post(
                    url=self.endpoint,
                    timeout=self.timeout,
                    headers=headers,
                    data=request_data,
                    verify=self.options.verify_ssl
                )

            response_data = http_response.text
            if self.is_enable_logging:
                self._logger.info(f'(res) {response_data}')

            response = Utils.from_json(response_data)

            success = Utils.get_value_as_bool('success', response, False)
            if not success:
                error_code = Utils.get_value_as_string('error_code', response, errorcodes.GENERAL_ERROR)
                message = Utils.get_value_as_string('message', response, 'Unknown')
                raise exceptions.soca_exception(
                    error_code=error_code,
                    message=message
                )

            payload = Utils.get_value_as_dict('payload', response)
            if payload is None:
                payload = {}

            if result_as:
                return result_as(**payload)

            return SocaAnyPayload(**payload)

        except requests.exceptions.Timeout as e:
            raise exceptions.soca_exception(
                error_code=errorcodes.SOCKET_TIMEOUT,
                message=f'Connection Timeout: {e}'
            )
        except requests.exceptions.ConnectionError as e:
            raise exceptions.soca_exception(
                error_code=errorcodes.CONNECTION_ERROR,
                message=f'Connection Error: {e}'
            )

    def invoke_alt(self, namespace: str, payload: Optional[Any],
                   result_as: Optional[Type[T]] = SocaAnyPayload,
                   access_token: str = None) -> T:
        request = SocaEnvelope(
            header=SocaHeader(
                namespace=namespace,
                request_id=Utils.uuid()
            ),
            payload=payload
        )
        return self.invoke(request, result_as, access_token)

    def invoke_json(self, json_request: str,
                    result_as: Optional[Type[T]] = SocaAnyPayload,
                    access_token: str = None) -> T:
        request = Utils.from_json(json_request)
        soca_request = SocaEnvelope(**request)
        return self.invoke(soca_request, result_as, access_token)

    def close(self):
        self.session.close()
