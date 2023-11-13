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

import ideaclustermanager
import ideaclustermanager.app.app_messages as app_messages

from ideasdk.utils import Utils, EnvironmentUtils, Jinja2Utils, ModuleMetadataHelper
from ideasdk.server import SocaServer
from ideadatamodel import exceptions, constants
from ideadatamodel.auth import (
    User,
    Group,
)
import uuid

import os
from pathlib import Path
import sanic
from typing import Dict
from datetime import datetime

DEFAULT_HTTP_HEADERS = {
    "X-Frame-Options": "SAMEORIGIN",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy" : "default-src 'self';\
        frame-ancestors 'self';\
        font-src 'self' data:;\
        img-src 'self' data:;\
        style-src 'self' 'unsafe-inline';",
    "Strict-Transport-Security" : "max-age=10886400; includeSubDomains;"
}

class WebPortal:

    def __init__(self, context: ideaclustermanager.AppContext, server: SocaServer):
        self.context = context
        self.server = server
        self.logger = context.logger('web-portal')
        self.module_metadata_helper = ModuleMetadataHelper()
        self.web_app_dir = self.get_web_app_dir()
        self.web_resources_context_path = self.context.config().get_string('cluster-manager.web_resources_context_path', '/')
        self.web_template_env = Jinja2Utils.env_using_file_system_loader(search_path=self.web_app_dir, auto_escape=True)

    @staticmethod
    def is_dev_mode() -> bool:
        return Utils.get_as_bool(EnvironmentUtils.idea_dev_mode(), False)

    @property
    def dev_mode_web_portal_root_dir(self) -> str:
        script_dir = Path(os.path.abspath(__file__))
        return str(script_dir.parent.parent.parent.parent)

    def get_web_app_dir(self) -> str:
        if self.is_dev_mode():
            web_sources_dir = os.path.join(self.dev_mode_web_portal_root_dir, 'webapp')
            html_build_dir = os.path.join(web_sources_dir, 'build-dev-mode')
            os.makedirs(html_build_dir, exist_ok=True)
            stylesheet = os.path.join(html_build_dir, 'StyleSheet.css')
            with open(stylesheet, 'w') as f:
                f.write(app_messages.DEV_MODE_STYLESHEET)
            index_page = os.path.join(html_build_dir, 'index.html')
            with open(index_page, 'w') as f:
                f.write(app_messages.DEV_MODE_INDEX_PAGE)
            return html_build_dir
        else:
            return os.path.join(Utils.app_deploy_dir(), 'cluster-manager', 'webapp')

    def get_logo_url(self) -> str:
        logo = self.context.config().get_string('cluster-manager.web_portal.logo')
        if Utils.is_not_empty(logo):
            # logo is provided as an external url or another file in public folder.
            if logo.startswith('https://') or logo.startswith('/'):
                return logo

            # assume logo is Key of the logo image file in cluster's s3 bucket.
            # create a pre-signed url and return
            return self.context.aws_util().create_s3_presigned_url(
                key=logo,
                expires_in=12 * 60 * 60  # 12 hours
            )

        return self.make_route_path('/logo.png')  # default RES logo in public directory

    def get_copyright_text(self) -> str:
        copyright_text = self.context.config().get_string('cluster-manager.web_portal.copyright_text')

        if Utils.is_empty(copyright_text):
            copyright_text = constants.DEFAULT_COPYRIGHT_TEXT

        return copyright_text

    def build_app_init_data(self, http_request) -> Dict:
        sso_enabled = self.context.config().get_bool('identity-provider.cognito.sso_enabled', False)

        # build module metadata and applicable api context paths
        module_set_id = Utils.get_as_string(self.server.get_query_param_as_string('module_set', http_request), self.context.module_set())
        modules = []
        module_set = self.context.config().get_config(f'global-settings.module_sets.{module_set_id}')
        for module_name in module_set:
            module_metadata = self.module_metadata_helper.get_module_metadata(module_name)
            api_context_path = None
            module_id = module_set.get_string(f'{module_name}.module_id')
            # send from server side, instead of having path info hard-coded clients
            # scope for further enhancements to read context path from applicable module's configuration
            if module_metadata.type == constants.MODULE_TYPE_APP:
                api_context_path = f'/{module_id}/api/v1'
            modules.append({
                **Utils.to_dict(module_metadata),
                'module_id': module_id,
                'api_context_path': api_context_path
            })

        app_init_data = {
            'version': ideaclustermanager.__version__,
            'sso': sso_enabled,
            'cluster_name': self.context.cluster_name(),
            'aws_region': self.context.aws().aws_region(),
            'title': self.context.config().get_string('cluster-manager.web_portal.title', 'Engineering Studio on AWS'),
            'subtitle': self.context.config().get_string('cluster-manager.web_portal.subtitle', f'{self.context.cluster_name()} ({self.context.aws().aws_region()})'),
            'logo': self.get_logo_url(),
            'copyright_text': self.get_copyright_text(),
            'default_log_level': self.context.config().get_int('cluster-manager.web_portal.default_log_level', 3),
            'module_set': module_set_id,
            'modules': modules,
            'session_management': self.context.config().get_string('cluster-manager.web_portal.session_management', 'in-memory')
        }

        error_msg = self.server.get_query_param_as_string('error_msg', http_request)
        if Utils.is_not_empty(error_msg):
            app_init_data['error_msg'] = error_msg

        if sso_enabled:
            sso_auth_status = self.server.get_query_param_as_string('sso_auth_status', http_request)
            if Utils.is_not_empty(sso_auth_status):
                app_init_data['sso_auth_status'] = sso_auth_status

            sso_auth_code = self.server.get_query_param_as_string('sso_auth_code', http_request)
            if Utils.is_not_empty(sso_auth_code):
                app_init_data['sso_auth_code'] = sso_auth_code

        return app_init_data

    def addNonceToHeader(self, header, nonce):
        http_header = {}
        for key,val in header.items():
            if key == "Content-Security-Policy":
                http_header[key] = val + "script-src 'self' 'nonce-" + nonce + "';"
            else:
                http_header[key] = val
        return http_header

    async def index_route(self, http_request):
        template = self.web_template_env.get_template('index.html')
        app_init_data = self.build_app_init_data(http_request)
        # Generate nonce to be passed to script tag and http header to allow inline script from "index.html"
        nonce = uuid.uuid4().hex
        result = template.render(app_init_data=Utils.base64_encode(Utils.to_json(app_init_data)), nonce=nonce)
        return sanic.response.html(
            body=result,
            status=200,
            headers=self.addNonceToHeader(header=DEFAULT_HTTP_HEADERS, nonce=nonce)
        )

    async def sso_initiate_route(self, _):
        sso_enabled = self.context.config().get_bool('identity-provider.cognito.sso_enabled', False)
        if not sso_enabled:
            return sanic.response.redirect(self.web_resources_context_path, headers=DEFAULT_HTTP_HEADERS)

        try:
            domain_url = self.context.config().get_string('identity-provider.cognito.domain_url', required=True)
            sso_client_id = self.context.config().get_string('identity-provider.cognito.sso_client_id', required=True)
            sso_idp_provider_name = self.context.config().get_string('identity-provider.cognito.sso_idp_provider_name', required=True)
            external_endpoint_url = self.context.config().get_cluster_external_endpoint()
            state = Utils.uuid()
            redirect_uri = f'{external_endpoint_url}{self.make_route_path("/sso/oauth2/callback")}'
            query_params = [
                'response_type=code',
                f'redirect_uri={Utils.url_encode(redirect_uri)}',
                f'state={state}',
                f'client_id={sso_client_id}',
                f'identity_provider={sso_idp_provider_name}'
            ]
            authorization_url = f'{domain_url}/authorize?{"&".join(query_params)}'

            # todo - add throttling to prevent ddb flooding from malicious actors and code
            self.context.accounts.sso_state_dao.create_sso_state({
                'state': state,
                'redirect_uri': redirect_uri
            })

            self.logger.debug(f'redirecting: {authorization_url}')
            return sanic.response.redirect(authorization_url, headers=DEFAULT_HTTP_HEADERS)
        except Exception as e:
            self.logger.exception(f'failed to initiate sso: {e}')
            return sanic.response.redirect(f'{self.web_resources_context_path}?sso_auth_status=FAIL',
                headers=DEFAULT_HTTP_HEADERS)

    async def sso_oauth2_callback_route(self, http_request):
        sso_enabled = self.context.config().get_bool('identity-provider.cognito.sso_enabled', False)
        if not sso_enabled:
            return sanic.response.redirect(self.web_resources_context_path, headers=DEFAULT_HTTP_HEADERS)

        try:

            authorization_code = self.server.get_query_param_as_string('code', http_request)
            state = self.server.get_query_param_as_string('state', http_request)
            error = self.server.get_query_param_as_string('error', http_request)
            error_description = self.server.get_query_param_as_string('error_description', http_request)

            if Utils.is_not_empty(error):
                self.logger.warning(f'sso auth failure: error={error}, error_description={error_description}')
                return sanic.response.redirect(f'{self.web_resources_context_path}?sso_auth_status=FAIL',
                                               headers=DEFAULT_HTTP_HEADERS)

            if Utils.is_empty(authorization_code):
                raise exceptions.invalid_params('code is required')
            if Utils.is_empty(state):
                raise exceptions.invalid_params('state is required')

            self.logger.debug(f'sso callback: authorization_code={authorization_code}, state={state}')

            # todo - add throttling to prevent ddb flooding from malicious actors and code
            sso_state = self.context.accounts.sso_state_dao.get_sso_state(state=state)
            if sso_state is None:
                raise exceptions.invalid_params(f'sso state not found for state: {state}')

            auth_result = self.context.token_service.get_access_token_using_sso_auth_code(
                authorization_code=authorization_code,
                redirect_uri=sso_state['redirect_uri']
            )

            # decode the access token and check if the username matches to the user that exists in DB
            claims = self.context.token_service.decode_token(auth_result.access_token)
            self.logger.info(f'sso token claims: {Utils.to_json(claims)}')

            username = Utils.get_value_as_string('username', claims)
            self.logger.debug(f'Cognito SSO claims - Username: {username}')

            if Utils.is_empty(username):
                self.logger.exception(f'Error - Unable to read IdP username from claims: {claims}')
                return sanic.response.redirect(f'{self.web_resources_context_path}?sso_auth_status=FAIL',
                                               headers=DEFAULT_HTTP_HEADERS)

            self.logger.debug(f'SSO auth: Looking up user: {username}')
            existing_user = self.context.accounts.user_dao.get_user(username=username)

            if existing_user is None:
                self.logger.warning(f'SSO auth: {username} is not previously known. User must be synced before first SSO attempt')
                # TODO auto-enrollment would go here
                self.logger.info(f'SSO auth: Unable to process {username}')
                self.logger.info(f'disabling federated user in user pool: {username}')
                self.context.user_pool.admin_disable_user(username=username)
                self.logger.info(f'deleting federated user in user pool: {username}')
                self.context.user_pool.admin_delete_user(username=username)
                try:
                    self.logger.info(f'Deleting state {state}')
                    self.context.accounts.sso_state_dao.delete_sso_state(state)
                except:
                    self.logger.info(f'Could not delete state {state}')
                return sanic.response.redirect(f'{self.web_resources_context_path}?sso_auth_status=FAIL&error_msg=UserNotFound',
                                               headers=DEFAULT_HTTP_HEADERS)

            self.logger.debug(f'Updating SSO State for user {username}: {state}')
            self.context.accounts.sso_state_dao.update_sso_state({
                'state': state,
                'access_token': auth_result.access_token,
                'refresh_token': auth_result.refresh_token,
                'expires_in': auth_result.expires_in,
                'id_token': auth_result.id_token,
                'token_type': auth_result.token_type
            })

            if not existing_user["is_active"]:
                user = self.context.accounts.user_dao.convert_from_db(existing_user)
                self.context.accounts.activate_user(user)

            return sanic.response.redirect(f'{self.web_resources_context_path}?sso_auth_status=SUCCESS&sso_auth_code={state}',
                                           headers=DEFAULT_HTTP_HEADERS)

        except Exception as e:
            self.logger.exception(f'failed to process sso oauth2 callback: {e}')
            return sanic.response.redirect(f'{self.web_resources_context_path}?sso_auth_status=FAIL',
                                           headers=DEFAULT_HTTP_HEADERS)

    def make_route_path(self, path: str) -> str:
        if not path.startswith('/'):
            path = f'/{path}'

        if self.web_resources_context_path == '/':
            return path
        else:
            return f'{self.web_resources_context_path}{path}'

    def initialize(self):
        # index route
        self.server.http_app.add_route(self.index_route, self.web_resources_context_path)
        # sso route
        self.server.http_app.add_route(self.sso_initiate_route, self.make_route_path('/sso'))
        # sso oauth 2 callback route
        self.server.http_app.add_route(self.sso_oauth2_callback_route, self.make_route_path('/sso/oauth2/callback'))
        # add static resources at the end
        self.server.http_app.static(self.web_resources_context_path, self.web_app_dir)
