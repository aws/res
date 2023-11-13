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

from ideadatamodel import constants

from ideasdk.protocols import SocaContextProtocol, ApiInvokerProtocol
from ideasdk.service import SocaService
from ideasdk.metrics import BaseMetrics
from ideadatamodel import exceptions, errorcodes, SocaBaseModel
from ideasdk.utils import Utils, EnvironmentUtils, GroupNameHelper, Jinja2Utils
from ideasdk.api import ApiInvocationContext

from ideasdk.server.sanic_config import SANIC_LOGGING_CONFIG, SANIC_APP_CONFIG
from ideasdk.server.cors import add_cors_headers
from ideasdk.server.options import create_ssl_context, setup_options
from ideasdk.filesystem.filesystem_helper import FileSystemHelper

from typing import Optional, Dict, List, Iterable
import asyncio
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Thread, Event
import pathlib
import os
import sanic
from sanic.server import AsyncioServer, serve as create_server, HttpProtocol
from sanic.server.protocols.websocket_protocol import WebSocketProtocol
import sanic.config
import sanic.signals
import sanic.router
from sanic.models.handler_types import RouteHandler
import socket
from prometheus_client import generate_latest

DEFAULT_ENABLE_HTTP = True
DEFAULT_ENABLE_HTTP_FILE_UPLOAD = False
DEFAULT_ENABLE_OPENAPI_SPEC = True
DEFAULT_ENABLE_TLS = False
DEFAULT_ENABLE_WEBSOCKETS = False
DEFAULT_HOSTNAME = 'localhost'
DEFAULT_HTTP_PORT = 8080
DEFAULT_HTTPS_PORT = 8443
DEFAULT_METRICS_PORT = 8081
DEFAULT_UNIX_SOCKET_FILE = '/run/idea.sock'
DEFAULT_MAX_WORKERS = 16
DEFAULT_GRACEFUL_SHUTDOWN_TIMEOUT = 10
DEFAULT_ENABLE_AUDIT_LOGS = True

# these are never used to serve content but used to serve http content over Unix Domain Sockets
DUMMY_HOSTNAME = 'localhost'
DUMMY_PORT = 9999


class SocaServerOptions(SocaBaseModel):
    enable_http: Optional[bool]
    hostname: Optional[str]
    port: Optional[int]
    enable_unix_socket: Optional[bool]
    unix_socket_file: Optional[str]
    max_workers: Optional[int]
    enable_metrics: Optional[bool]
    enable_tls: Optional[bool]
    tls_certificate_file: Optional[str]
    tls_key_file: Optional[str]
    graceful_shutdown_timeout: Optional[float]
    enable_web_sockets: Optional[bool]
    api_path_prefixes: Optional[List[str]]
    enable_http_file_upload: Optional[bool]
    enable_openapi_spec: Optional[bool]
    openapi_spec_file: Optional[str]
    enable_audit_logs: Optional[bool]

    @staticmethod
    def default() -> 'SocaServerOptions':
        return SocaServerOptions(
            enable_http=None,
            hostname=None,
            port=None,
            enable_unix_socket=None,
            unix_socket_file=None,
            max_workers=None,
            enable_metrics=None,
            enable_tls=None,
            tls_certificate_file=None,
            tls_key_file=None,
            graceful_shutdown_timeout=None,
            enable_web_sockets=None,
            api_path_prefixes=None,
            enable_http_file_upload=None,
            enable_openapi_spec=None,
            openapi_spec_file=None,
            enable_audit_logs=None
        )


class ServerOptionsProvider:
    def __init__(self, context: SocaContextProtocol, options: SocaServerOptions = None):
        self.context = context
        if options is None:
            self.options = SocaServerOptions.default()
        else:
            self.options = options

        self._is_running_in_ec2 = None

    def is_running_in_ec2(self) -> bool:
        if self._is_running_in_ec2 is not None:
            return self._is_running_in_ec2
        if self.context.aws() is not None:
            self._is_running_in_ec2 = self.context.aws().is_running_in_ec2()
        else:
            self._is_running_in_ec2 = False
        return Utils.get_as_bool(self._is_running_in_ec2, False)

    @property
    def enable_http(self) -> bool:
        if self.options.enable_http is not None:
            return self.options.enable_http
        return self.context.config().get_bool(f'{self.context.module_name()}.server.enable_http', DEFAULT_ENABLE_HTTP,
                                              module_id=self.context.module_id())

    @property
    def enable_http_file_upload(self) -> bool:
        if self.options.enable_http_file_upload is not None:
            return self.options.enable_http_file_upload
        return self.context.config().get_bool(f'{self.context.module_name()}.server.enable_http_file_upload', DEFAULT_ENABLE_HTTP_FILE_UPLOAD,
                                              module_id=self.context.module_id())

    @property
    def enable_tls(self) -> bool:
        if self.options.enable_tls is not None:
            return self.options.enable_tls
        return self.context.config().get_bool(f'{self.context.module_name()}.server.enable_tls', DEFAULT_ENABLE_TLS,
                                              module_id=self.context.module_id())

    @property
    def enable_web_sockets(self) -> bool:
        if self.options.enable_web_sockets is not None:
            return self.options.enable_web_sockets
        return self.context.config().get_bool(f'{self.context.module_name()}.server.enable_web_sockets', DEFAULT_ENABLE_WEBSOCKETS,
                                              module_id=self.context.module_id())

    @property
    def enable_metrics(self) -> bool:
        if self.options.enable_metrics is not None:
            return self.options.enable_metrics
        enable_metrics = self.context.config().get_bool(f'{self.context.module_name()}.server.enable_metrics',
                                                        module_id=self.context.module_id())
        if enable_metrics is not None:
            return enable_metrics
        if self.is_running_in_ec2() and Utils.is_linux():
            return True
        return False

    @property
    def enable_unix_socket(self) -> bool:
        if self.options.enable_unix_socket is not None:
            return self.options.enable_unix_socket
        enable_unix_socket = self.context.config().get_bool(f'{self.context.module_name()}.server.enable_unix_socket',
                                                            module_id=self.context.module_id())
        if enable_unix_socket is not None:
            return enable_unix_socket
        if self.is_running_in_ec2() and Utils.is_linux():
            return True
        return False

    @property
    def hostname(self) -> str:
        if Utils.is_not_empty(self.options.hostname):
            return self.options.hostname
        hostname = self.context.config().get_string(f'{self.context.module_name()}.server.hostname',
                                                    module_id=self.context.module_id())
        if Utils.is_not_empty(hostname):
            return hostname
        if self.is_running_in_ec2():
            return self.context.aws().instance_metadata().get_instance_identity_document().privateIp
        return DEFAULT_HOSTNAME

    @property
    def port(self) -> int:
        if self.options.port is not None:
            return self.options.port
        port = self.context.config().get_int(f'{self.context.module_name()}.server.port',
                                             module_id=self.context.module_id())
        if port is not None:
            return port
        if self.enable_tls:
            return DEFAULT_HTTPS_PORT
        else:
            return DEFAULT_HTTP_PORT

    @property
    def tls_certificate_file(self) -> Optional[str]:
        if not self.enable_tls:
            return None
        if Utils.is_not_empty(self.options.tls_certificate_file):
            return self.options.tls_certificate_file
        tls_certificate_file = self.context.config().get_string(f'{self.context.module_name()}.server.tls_certificate_file',
                                                                module_id=self.context.module_id())
        if Utils.is_not_empty(tls_certificate_file):
            return tls_certificate_file
        return os.path.join(EnvironmentUtils.idea_app_deploy_dir(), 'certs', 'server.crt')

    @property
    def tls_key_file(self) -> Optional[str]:
        if not self.enable_tls:
            return None
        if Utils.is_not_empty(self.options.tls_key_file):
            return self.options.tls_key_file
        tls_key_file = self.context.config().get_string(f'{self.context.module_name()}.server.tls_key_file',
                                                        module_id=self.context.module_id())
        if Utils.is_not_empty(tls_key_file):
            return tls_key_file
        return os.path.join(EnvironmentUtils.idea_app_deploy_dir(), 'certs', 'server.key')

    @property
    def unix_socket_file(self) -> Optional[str]:
        if not self.enable_unix_socket:
            return None
        if Utils.is_not_empty(self.options.unix_socket_file):
            return self.options.unix_socket_file
        unix_socket_file = self.context.config().get_string(f'{self.context.module_name()}.server.unix_socket_file',
                                                            module_id=self.context.module_id())
        if Utils.is_not_empty(unix_socket_file):
            return unix_socket_file
        return DEFAULT_UNIX_SOCKET_FILE

    @property
    def max_workers(self) -> int:
        if self.options.max_workers is not None:
            return self.options.max_workers
        max_workers = self.context.config().get_int(f'{self.context.module_name()}.server.max_workers',
                                                    module_id=self.context.module_id())
        if max_workers is not None:
            return max_workers
        return DEFAULT_MAX_WORKERS

    @property
    def graceful_shutdown_timeout(self) -> float:
        if self.options.graceful_shutdown_timeout is not None:
            return self.options.graceful_shutdown_timeout
        graceful_shutdown_timeout = self.context.config().get_float(f'{self.context.module_name()}.server.graceful_shutdown_timeout',
                                                                    module_id=self.context.module_id())
        if graceful_shutdown_timeout is not None:
            return graceful_shutdown_timeout
        return DEFAULT_GRACEFUL_SHUTDOWN_TIMEOUT

    @property
    def api_path_prefixes(self) -> List[str]:
        if Utils.is_not_empty(self.options.api_path_prefixes):
            return self.options.api_path_prefixes
        api_path_prefixes = self.context.config().get_list(f'{self.context.module_name()}.server.api_path_prefixes',
                                                           module_id=self.context.module_id())
        if Utils.is_not_empty(api_path_prefixes):
            return api_path_prefixes
        return api_path_prefixes

    @property
    def protocol(self) -> str:
        if self.enable_tls:
            return 'https'
        else:
            return 'http'

    @property
    def enable_openapi_spec(self) -> bool:
        if self.options.enable_openapi_spec is not None:
            return self.options.enable_openapi_spec
        return self.context.config().get_bool(f'{self.context.module_name()}.server.enable_openapi_spec', DEFAULT_ENABLE_OPENAPI_SPEC, module_id=self.context.module_id())

    @property
    def openapi_spec_file(self) -> Optional[str]:
        if not self.enable_openapi_spec:
            return None
        if Utils.is_not_empty(self.options.openapi_spec_file):
            return self.options.openapi_spec_file
        openapi_spec_file = self.context.config().get_string(f'{self.context.module_name()}.server.openapi_spec_file', module_id=self.context.module_id())
        if Utils.is_not_empty(openapi_spec_file):
            return openapi_spec_file
        return os.path.join(EnvironmentUtils.idea_app_deploy_dir(required=True), self.context.module_name(), 'resources', 'api', 'openapi.yml')

    @property
    def enable_audit_logs(self) -> bool:
        if self.options.enable_audit_logs is not None:
            return self.options.enable_audit_logs
        return self.context.config().get_bool(f'{self.context.module_name()}.server.enable_audit_logs', DEFAULT_ENABLE_AUDIT_LOGS, module_id=self.context.module_id())

    def build(self) -> SocaServerOptions:
        return SocaServerOptions(
            enable_http=self.enable_http,
            hostname=self.hostname,
            port=self.port,
            enable_unix_socket=self.enable_unix_socket,
            unix_socket_file=self.unix_socket_file,
            max_workers=self.max_workers,
            enable_metrics=self.enable_metrics,
            enable_tls=self.enable_tls,
            tls_certificate_file=self.tls_certificate_file,
            tls_key_file=self.tls_key_file,
            graceful_shutdown_timeout=self.graceful_shutdown_timeout,
            enable_web_sockets=self.enable_web_sockets,
            enable_openapi_spec=self.enable_openapi_spec,
            openapi_spec_file=self.openapi_spec_file,
            enable_audit_logs=self.enable_audit_logs
        )

    def validate(self):

        if self.enable_http:
            if Utils.is_empty(self.hostname):
                raise exceptions.invalid_params('options.hostname is required')
            if Utils.is_empty(self.port):
                raise exceptions.invalid_params('options.port is required')

        if self.enable_unix_socket:
            if Utils.is_empty(self.unix_socket_file):
                raise exceptions.invalid_params('options.unix_socket_file is required')

        if not self.enable_http and not self.enable_unix_socket:
            raise exceptions.invalid_params('either enable_http or enable_unix_socket or both must be enabled.')

        if self.enable_tls:
            if Utils.is_empty(self.tls_certificate_file):
                raise exceptions.invalid_params('options.tls_certificate_file is required')
            if not Utils.is_file(self.tls_certificate_file):
                raise exceptions.file_not_found(self.tls_certificate_file)
            if Utils.is_empty(self.tls_key_file):
                raise exceptions.invalid_params('options.tls_key_file is required')
            if not Utils.is_file(self.tls_key_file):
                raise exceptions.file_not_found(self.tls_key_file)

        if self.enable_openapi_spec:
            openapi_spec_file = self.openapi_spec_file
            if not Utils.is_file(openapi_spec_file):
                raise exceptions.file_not_found(openapi_spec_file)


class ApiInvocationHandler:

    def __init__(self, context: SocaContextProtocol,
                 server: 'SocaServer',
                 api_invoker: ApiInvokerProtocol,
                 group_name_helper: GroupNameHelper):
        self.context = context
        self.logger = context.logger('api')
        self.api_invoker = api_invoker
        self.server = server
        self.group_name_helper = group_name_helper

    @staticmethod
    def get_namespace(payload: Dict) -> str:
        header = Utils.get_value_as_dict('header', payload)
        return Utils.get_value_as_string('namespace', header, 'Unknown')

    @staticmethod
    def get_error_code(response: Dict) -> str:
        return Utils.get_value_as_string('error_code', response, errorcodes.GENERAL_ERROR)

    def publish_metrics(self, context: ApiInvocationContext):
        if not self.server.options.enable_metrics:
            return

        metrics_provider = self.context.config().get_string('metrics.provider')
        if Utils.is_empty(metrics_provider):
            return

        namespace = context.namespace
        success = context.is_success()

        BaseMetrics(
            context=self.context
        ).with_required_dimension(
            name='api', value=namespace
        ).invocation(MetricName='api_invocations', Value=context.get_total_time_ms())

        if not success:
            error_code = context.error_code
            if Utils.is_empty(error_code):
                error_code = 'UNKNOWN_ERROR'
            BaseMetrics(
                context=self.context
            ).with_required_dimension(
                name='api', value=namespace
            ).with_required_dimension(
                name='error_code', value=error_code
            ).count(MetricName='count')

    def check_is_running(self):
        if not self.server.is_running():
            raise exceptions.soca_exception(
                error_code=errorcodes.SERVER_IS_SHUTTING_DOWN,
                message='server is shutting down'
            )

    @staticmethod
    def validate_and_preprocess_request(request: Dict):
        header = Utils.get_value_as_dict('header', request)

        if header is None:
            raise exceptions.invalid_params('header is required')

        namespace = Utils.get_value_as_string('namespace', header)
        if Utils.is_empty(namespace):
            raise exceptions.invalid_params('header.namespace is required')

        request_id = Utils.get_value_as_string('request_id', header)
        if Utils.is_empty(request_id):
            request_id = Utils.uuid()
            header['request_id'] = request_id

    def get_token(self, http_request) -> Optional[Dict]:
        token = Utils.get_value_as_list('token', http_request.args)
        if Utils.is_not_empty(token):
            return {
                'token_type': 'Bearer',
                'token': Utils.get_first(token)
            }

        return self.server.get_authorization_header(http_request)

    def is_authenticated_request(self, http_request) -> bool:
        username = self.get_username(http_request)
        return Utils.is_not_empty(username)

    def get_username(self, http_request) -> Optional[str]:
        try:
            token_service = self.api_invoker.get_token_service()
            if token_service is None:
                return None
            token = self.get_token(http_request)
            token_type = Utils.get_value_as_string('token_type', token)
            if Utils.is_empty(token_type):
                return None
            if token_type != 'Bearer':
                return None
            access_token = Utils.get_value_as_string('token', token)
            return token_service.get_username(access_token)
        except Exception:  # noqa
            return None

    def _invoke(self, http_request) -> Dict:

        request = http_request.json
        request_logged = False

        invocation_context: Optional[ApiInvocationContext] = None

        try:

            if http_request.socket is None:
                invocation_source = constants.API_INVOCATION_SOURCE_UNIX_SOCKET
            else:
                invocation_source = constants.API_INVOCATION_SOURCE_HTTP

            invocation_context = ApiInvocationContext(
                context=self.context,
                request=request,
                invocation_source=invocation_source,
                group_name_helper=self.group_name_helper,
                logger=self.logger,
                token=self.get_token(http_request),
                token_service=self.api_invoker.get_token_service(),
            )

            # validate request prior to logging
            invocation_context.validate_request()

            tracing_request = self.api_invoker.get_request_logging_payload(invocation_context)

            invocation_context.log_request(tracing_request)
            request_logged = True

            self.validate_and_preprocess_request(request)

            self.check_is_running()

            self.api_invoker.invoke(invocation_context)

            response = invocation_context.response

            if response is None:
                raise exceptions.soca_exception(
                    error_code=errorcodes.NOT_SUPPORTED,
                    message=f'namespace: {invocation_context.namespace} not supported'
                )

        except exceptions.SocaException as e:

            message = e.message
            if e.ref is not None and isinstance(e.ref, Exception):
                message += f' (RootCause: {str(e.ref)})'
            invocation_context.fail(error_code=e.error_code, message=message)

        except Exception as e:

            message = f'{e}'
            self.logger.exception(message)
            invocation_context.fail(error_code=errorcodes.GENERAL_ERROR, message=message)

        finally:

            if not request_logged:
                invocation_context.log_request()

            tracing_response = self.api_invoker.get_response_logging_payload(invocation_context)
            invocation_context.log_response(tracing_response)

        # publish metrics
        self.publish_metrics(context=invocation_context)

        return invocation_context.response

    def invoke(self, http_request) -> Dict:
        try:
            return self._invoke(http_request)
        except BaseException as e:
            message = f'Critical exception: {e}'
            self.logger.exception(message)
            return {
                'header': {
                    'namespace': 'ErrorResponse',
                    'request_id': Utils.uuid()
                },
                'success': False,
                'message': message
            }


class SocaServer(SocaService):
    """
    IDEA Server
    """

    def __init__(self, context: SocaContextProtocol, api_invoker: ApiInvokerProtocol, options: SocaServerOptions):

        if Utils.is_empty(api_invoker):
            raise exceptions.invalid_params('api_invoker is required')

        super().__init__(context)
        self._context = context
        self._logger = context.logger('server')
        self._group_name_helper = GroupNameHelper(context)

        self.options = ServerOptionsProvider(context, options)
        self.options.validate()

        self._api_invocation_handler = ApiInvocationHandler(
            context=self._context,
            server=self,
            api_invoker=api_invoker,
            group_name_helper=self._group_name_helper
        )

        self._server_loop: Optional[asyncio.AbstractEventLoop] = None
        self._server_thread: Optional[Thread] = None
        self._executor = ThreadPoolExecutor(
            max_workers=self.options.max_workers,
            thread_name_prefix=f'{self._context.module_id()}-server-worker'
        )
        self._is_running = Event()

        self._sanic_config: Optional[sanic.config.Config] = None
        self._sanic_router: Optional[sanic.router.Router] = None
        self._sanic_signal_router: Optional[sanic.signals.SignalRouter] = None

        self._unix_app: Optional[sanic.Sanic] = None
        self._unix_server: Optional[AsyncioServer] = None

        self._http_app: Optional[sanic.Sanic] = None
        self._http_server: Optional[AsyncioServer] = None

        self._is_started_future = Future()

        self.metrics_api_token_file = '/root/metrics_api_token.txt'
        self.metrics_api_token = None

    @staticmethod
    def is_another_instance_running(hostname: str, port: int) -> bool:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((hostname, port))
            return result == 0
        finally:
            if sock is not None:
                sock.close()

    @property
    def sanic_router(self) -> sanic.router.Router:
        if self._sanic_router is not None:
            return self._sanic_router
        self._sanic_router = sanic.router.Router()
        return self._sanic_router

    @property
    def sanic_signal_router(self) -> sanic.signals.SignalRouter:
        if self._sanic_signal_router is not None:
            return self._sanic_signal_router
        self._sanic_signal_router = sanic.signals.SignalRouter()
        return self._sanic_signal_router

    @property
    def http_app(self) -> sanic.Sanic:
        if self._http_app is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message='Server is not yet initialized.'
            )
        return self._http_app

    @property
    def unix_app(self) -> sanic.Sanic:
        if self._unix_app is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message='Server is not yet initialized.'
            )
        return self._unix_app

    def add_route(self, handler: RouteHandler,
                  uri: str,
                  methods: Iterable[str] = frozenset({"GET"}),
                  name: str = None):
        if self.options.enable_http:
            for path_prefix in self.options.api_path_prefixes:
                self.http_app.add_route(handler, f'{path_prefix}{uri}', methods, name=f'{path_prefix}{name or ""}{uri}')
        else:
            for path_prefix in self.options.api_path_prefixes:
                self.unix_app.add_route(handler, f'{path_prefix}{uri}', methods, name=f'{path_prefix}{name or ""}{uri}')

    def initialize(self):

        if self.options.enable_http:
            self._http_app = sanic.Sanic(
                name='http-server',
                config=SANIC_APP_CONFIG,
                router=self.sanic_router,
                signal_router=self.sanic_signal_router,
                log_config=SANIC_LOGGING_CONFIG,
            )

        if self.options.enable_unix_socket:
            unix_socket_parent = str(pathlib.Path(self.options.unix_socket_file).parent)
            if not os.path.isdir(unix_socket_parent):
                os.makedirs(unix_socket_parent, exist_ok=True)

            self._unix_app = sanic.Sanic(
                name='unix-server',
                config=SANIC_APP_CONFIG,
                router=self.sanic_router,
                signal_router=self.sanic_signal_router,
                log_config=SANIC_LOGGING_CONFIG
            )

        if self.options.enable_metrics:
            if not Utils.is_file(self.metrics_api_token_file):
                with open(self.metrics_api_token_file, 'w') as f:
                    f.write(Utils.uuid())
            with open(self.metrics_api_token_file, 'r') as f:
                self.metrics_api_token = f.read()

        if self.options.enable_http:
            self.http_app.register_listener(setup_options, "before_server_start")
            self.http_app.register_middleware(add_cors_headers, "response")

            # health check routes
            self.http_app.add_route(self.health_check_route, '/healthcheck', name="healthcheck", methods=['GET'])
            self.add_route(self.health_check_route, '/healthcheck', methods=['GET'])

            # file transfer routes
            if self.options.enable_http_file_upload:
                self.add_route(self.file_upload_route, '/api/v1/upload', methods=['PUT'])
                self.add_route(self.file_upload_route, '/api/v1/<namespace:str>', methods=['PUT'], name='NamespaceUpload')
                self.add_route(self.file_download_route, '/api/v1/download', methods=['GET'])
                self.add_route(self.file_download_route, '/api/v1/<namespace:str>', methods=['GET'], name='NamespaceDownload')

            # metrics routes
            if self.options.enable_metrics:
                self.add_route(self.metrics_route, '/metrics', methods=['GET'])

            # open api spec routes
            if self.options.enable_openapi_spec:
                self.add_route(self.openapi_spec_route, '/api/v1/openapi.yml', methods=['GET'])

        self.add_route(self.api_route, '/api/v1', methods=['POST'])
        self.add_route(self.api_route, '/api/v1/<namespace:str>', methods=['POST'], name='NamespaceAPI')

    async def invoke_api_task(self, http_request):
        result = self._executor.submit(
            lambda http_request_: self._api_invocation_handler.invoke(http_request_),
            http_request
        )
        return await asyncio.wrap_future(result)

    @staticmethod
    async def health_check_route(_):
        return sanic.response.json({
            'success': True
        }, dumps=Utils.to_json)

    @staticmethod
    def unauthorized_access():
        return sanic.response.json({
            'success': False,
            'error_code': errorcodes.UNAUTHORIZED_ACCESS
        }, dumps=Utils.to_json)

    async def metrics_route(self, http_request):
        authorization = self.get_authorization_header(http_request)
        if Utils.is_empty(authorization):
            return self.unauthorized_access()
        token_type = Utils.get_value_as_string('token_type', authorization)
        token = Utils.get_value_as_string('token', authorization)
        if Utils.is_any_empty(token_type, token):
            return self.unauthorized_access()
        if token_type != 'Bearer':
            return self.unauthorized_access()
        if token != self.metrics_api_token:
            return self.unauthorized_access()
        # todo - enable gzip if accepted
        output = generate_latest()
        return sanic.response.text(Utils.from_bytes(output))

    async def api_route(self, http_request, **_):
        response = await self.invoke_api_task(http_request)
        return sanic.response.json(response, dumps=Utils.to_json)

    async def openapi_spec_route(self, _):
        openapi_spec_file = pathlib.Path(self.options.openapi_spec_file)

        spec_template_env = Jinja2Utils.env_using_file_system_loader(search_path=str(openapi_spec_file.parent))
        spec_template = spec_template_env.get_template(openapi_spec_file.name)

        server_url = self._context.config().get_cluster_external_endpoint()
        if Utils.is_not_empty(self.options.api_path_prefixes):
            path_prefix = self.options.api_path_prefixes[0]
            server_url = f'{server_url}{path_prefix}/api/v1'
        spec_template_data = {
            'module_id': self._context.module_id(),
            'module_name': self._context.module_name(),
            'module_version': self._context.module_version(),
            'server_url': server_url
        }

        spec_content = spec_template.render(**spec_template_data)
        # refer: https://stackoverflow.com/questions/332129/yaml-media-type
        # switch to text/vnd.yaml once yaml mime type is accepted by IANA
        return sanic.response.text(spec_content, 200, content_type='text/x-yaml')

    @staticmethod
    def get_query_param_as_string(name: str, http_request) -> Optional[str]:
        param_value = None
        param_list = Utils.get_value_as_list(name, http_request.args)
        if Utils.is_not_empty(param_list):
            param_value = param_list[0]
        return param_value

    @staticmethod
    def get_authorization_header(http_request) -> Optional[Dict]:
        if 'Authorization' not in http_request.headers:
            return None
        authorization = Utils.get_value_as_string('Authorization', http_request.headers)
        if Utils.is_empty(authorization):
            return None
        kv = authorization.split(' ')
        if len(kv) != 2:
            return None
        return {
            'token_type': kv[0],
            'token': kv[1]
        }

    async def file_upload_route(self, http_request, **_):
        try:
            username = self._api_invocation_handler.get_username(http_request)
            if Utils.is_empty(username):
                raise exceptions.unauthorized_access()

            cwd = self.get_query_param_as_string('cwd', http_request)
            files = Utils.get_value_as_list('files[]', http_request.files)
            helper = FileSystemHelper(self._context, username=username)
            result = await helper.upload_files(cwd, files)
            return sanic.response.json(result, dumps=Utils.to_json)
        except Exception as e:
            if isinstance(e, exceptions.SocaException):
                return sanic.response.json({
                    'error_code': e.error_code,
                    'success': False
                }, dumps=Utils.to_json)
            else:
                return sanic.response.json({
                    'error_code': errorcodes.GENERAL_ERROR,
                    'success': False
                }, dumps=Utils.to_json)

    async def file_download_route(self, http_request, **_):
        username = self._api_invocation_handler.get_username(http_request)
        if Utils.is_empty(username):
            return sanic.response.json({
                'error_code': errorcodes.UNAUTHORIZED_ACCESS,
                'success': False
            }, dumps=Utils.to_json)

        download_file = None
        download_files = Utils.get_value_as_list('file', http_request.args)
        if Utils.is_not_empty(download_files):
            download_file = download_files[0]

        if Utils.is_empty(download_file):
            return sanic.response.json({
                'error_code': errorcodes.UNAUTHORIZED_ACCESS,
                'success': False
            }, dumps=Utils.to_json)

        helper = FileSystemHelper(self._context, username=username)
        try:
            helper.check_access(download_file, check_read=True, check_write=False)
        except exceptions.SocaException as e:
            return sanic.response.json({
                'error_code': e.error_code,
                'message': e.message,
                'success': False
            }, dumps=Utils.to_json)

        return await sanic.response.file(download_file, filename=os.path.basename(download_file))

    def _remove_unix_socket(self):
        if not self.options.enable_unix_socket:
            return
        if Utils.is_socket(self.options.unix_socket_file):
            os.unlink(self.options.unix_socket_file)

    async def _server_startup(self):
        if self.options.enable_http:
            await self._http_server.startup()
            await self._http_server.before_start()
        else:
            await self._unix_server.startup()
            await self._unix_server.before_start()

    def _run_server(self):

        try:

            self._server_loop = asyncio.new_event_loop()

            ssl_context = None
            if self.options.enable_tls:
                ssl_context = create_ssl_context(self.options.tls_certificate_file, self.options.tls_key_file)

            if self.options.enable_http:
                if self.is_another_instance_running(self.options.hostname, self.options.port):
                    raise exceptions.SocaException(
                        error_code=errorcodes.PORT_IS_ALREADY_IN_USE,
                        message=f'Failed to start soca-server. Port: {self.options.port} is already in use.'
                    )

                self._http_server = create_server(
                    host=self.options.hostname,
                    port=self.options.port,
                    app=self._http_app,
                    ssl=ssl_context,
                    loop=self._server_loop,
                    run_async=True,
                    reuse_port=True,
                    protocol=WebSocketProtocol if self.options.enable_web_sockets else HttpProtocol
                )

            if self.options.enable_unix_socket:
                self._unix_server = create_server(
                    host=DUMMY_HOSTNAME,
                    port=DUMMY_PORT,
                    unix=self.options.unix_socket_file,
                    app=self._unix_app,
                    loop=self._server_loop,
                    run_async=True,
                    reuse_port=True
                )
                os.chmod(self.options.unix_socket_file, 0o700)

            self._server_loop.run_until_complete(self._server_startup())
            self._server_loop.run_until_complete(self._http_server.serve_coro)
            if self.options.enable_unix_socket:
                self._server_loop.run_until_complete(self._unix_server.serve_coro)

            startup_message = str(f'server started. listening on - '
                                  f'{self.options.protocol}://{self.options.hostname}:{self.options.port} (api)')
            if self.options.enable_unix_socket:
                startup_message += f', {Utils.url_encode(self.options.unix_socket_file)} (unix socket)'
            self._logger.info(startup_message)

            result = True, None
            self._is_started_future.set_result(result)

            self._server_loop.run_forever()

        except Exception as e:
            result = False, e
            self._is_started_future.set_result(result)

    def is_running(self) -> bool:
        return self._is_running.is_set()

    def start(self):
        if self.is_running():
            return

        self._is_running.set()

        self._server_thread = Thread(
            target=self._run_server,
            name=f'{self._context.module_id()}-run-server'
        )
        self._server_thread.start()
        result = self._is_started_future.result()
        if not result[0]:
            self._is_running.clear()
            raise result[1]

    def stop(self):
        if not self.is_running():
            return

        # clear _is_running, so that no new client connections will be queued
        self._is_running.clear()

        # shutdown executor and wait for current pending requests to complete and allow to respond back
        self._executor.shutdown(wait=True, cancel_futures=True)

        # we are in main thread now...
        mainloop = asyncio.get_event_loop()

        connections = []

        if self.options.enable_unix_socket:
            self._logger.info('stopping unix server ...')
            self._unix_server.close()
            self._unix_server.wait_closed()
            connections += self._unix_server.connections

        self._logger.info('stopping http server ...')
        self._http_server.close()
        self._http_server.wait_closed()
        connections += self._http_server.connections

        for connection in connections:
            connection.close_if_idle()

        # Gracefully shutdown timeout
        # refer to sanic.server.runners.serve() for more details.
        graceful = self.options.graceful_shutdown_timeout
        if connections and graceful > 0:
            self._logger.info(f'waiting for graceful shutdown timeout: {graceful} ...')
        start_shutdown: float = 0
        while connections and (start_shutdown < graceful):
            mainloop.run_until_complete(asyncio.sleep(0.1))
            start_shutdown = start_shutdown + 0.1

        self._http_app.shutdown_tasks(graceful - start_shutdown)
        if self.options.enable_unix_socket:
            self._unix_app.shutdown_tasks(graceful - start_shutdown)

        for connection in connections:
            if hasattr(connection, 'websocket') and connection.websocket:
                connection.websocket.fail_connection(code=1001)
            else:
                connection.abort()

        mainloop.run_until_complete(self._http_server.after_stop())

        # close the loop
        if self._server_loop.is_running():
            # _loop.stop() is not threadsafe. since we start a loop from a different thread,
            #   call stop using call_soon_threadsafe
            self._server_loop.call_soon_threadsafe(self._server_loop.stop)

        self._server_thread.join()

        if self.options.enable_unix_socket:
            self._remove_unix_socket()

        self._logger.info('server stopped.')
