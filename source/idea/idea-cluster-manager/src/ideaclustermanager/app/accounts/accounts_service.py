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
import re
from ideasdk.client.evdi_client import EvdiClient
from ideasdk.context import SocaContext

from ideadatamodel import (
    AuthResult,
    SignUpUserRequest,
    ConfirmSignUpRequest,
    ResendConfirmationCodeRequest,
    User,
    Group,
    InitiateAuthRequest,
    InitiateAuthResult,
    RespondToAuthChallengeRequest,
    RespondToAuthChallengeResult,
    ListUsersRequest,
    ListUsersResult,
    ListGroupsRequest,
    ListGroupsResult,
    ListUsersInGroupRequest,
    ListUsersInGroupResult,
    ConfigureSSORequest,
)
from ideadatamodel import exceptions, errorcodes, constants
from ideasdk.utils import Utils, GroupNameHelper
from ideasdk.auth import TokenService

from ideaclustermanager.app.accounts.cognito_user_pool import CognitoUserPool
from ideaclustermanager.app.accounts import auth_constants
from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from ideaclustermanager.app.accounts.db.group_dao import GroupDAO
from ideaclustermanager.app.accounts.db.user_dao import UserDAO
from ideaclustermanager.app.accounts.db.group_members_dao import GroupMembersDAO
from ideaclustermanager.app.accounts.db.single_sign_on_state_dao import SingleSignOnStateDAO
from ideaclustermanager.app.accounts.helpers.single_sign_on_helper import SingleSignOnHelper
from ideaclustermanager.app.accounts.helpers.sssd_helper import SSSD
from ideaclustermanager.app.accounts.helpers.quic_update_helper import QuicUpdateHelper, UpdateQuicResults

from res.resources import accounts
from res.clients.ad_sync import ad_sync_client
from res import exceptions as res_exceptions

from typing import Optional
import os
import time
import json


def nonce() -> str:
    return Utils.short_uuid()


class AccountsService:
    """
    Account Management Service

    Integrates with OpenLDAP/AD, Cognito User Pools and exposes functionality around:
    1. User Management
    2. Groups
    3. User Onboarding
    4. Single Sign-On

    The service is primarily invoked via AuthAPI and AccountsAPI
    """

    def __init__(self, context: SocaContext,
                 user_pool: Optional[CognitoUserPool],
                 evdi_client: Optional[EvdiClient],
                 token_service: Optional[TokenService]):

        self.context = context
        self.logger = context.logger('accounts-service')
        self.user_pool = user_pool
        self.evdi_client = evdi_client
        self.token_service = token_service

        self.sssd = SSSD(context)
        self.group_name_helper = GroupNameHelper(context)
        self.user_dao = UserDAO(context, user_pool=user_pool)
        self.group_dao = GroupDAO(context)
        self.group_members_dao = GroupMembersDAO(context)
        self.sso_state_dao = SingleSignOnStateDAO(context)
        self.single_sign_on_helper = SingleSignOnHelper(context)
        self.quic_update_helper = QuicUpdateHelper(context)

        self.user_dao.initialize()
        self.group_dao.initialize()
        self.group_members_dao.initialize()
        self.sso_state_dao.initialize()

        self.ds_automation_dir = self.context.config().get_string('directoryservice.automation_dir', required=True)
        self.cluster_name = self.context.config().get_string('cluster.cluster_name', required=True)

    def is_cluster_administrator(self, username: str) -> bool:
        cluster_administrator = self.context.config().get_string('cluster.administrator_username', required=True)
        return username == cluster_administrator

    def is_sso_enabled(self) -> bool:
        return self.context.config().get_bool('identity-provider.cognito.sso_enabled', False)
    
    def is_cognito_self_sign_up_enabled(self) -> bool:
        return self.context.config().get_bool('identity-provider.cognito.enable_self_sign_up', False)

    # user group management methods

    def get_group(self, group_name: str) -> Optional[Group]:
        group = accounts.get_group(group_name)
        return GroupDAO.convert_from_db(group)

    def modify_group(self, group: Group) -> Group:
        """
        modify an existing group
        :param group: Group
        """
        # do not support modification of group name or GID
        # only title updates are supported
        update_group = {
            'group_name': group.name,
            'title': group.title,
            'enabled': group.enabled,
        }

        # only update db, sync with DS not required.
        updated_group = accounts.update_group(update_group)
        return GroupDAO.convert_from_db(updated_group)

    def list_groups(self, request: ListGroupsRequest) -> ListGroupsResult:
        return self.group_dao.list_groups(request)

    def list_users_in_group(self, request: ListUsersInGroupRequest) -> ListUsersInGroupResult:
        return self.group_members_dao.list_users_in_group(request)

    def remove_admin_user(self, username: str) -> User:
        if self.is_cluster_administrator(username):
            raise AuthUtils.invalid_operation(f'Admin rights cannot be revoked from RES Environment Administrator: {username}.')

        updated_user = accounts.update_user({
            'username': username,
            'role': 'user',
            'sudo': False
        })
        return self.user_dao.convert_from_db(updated_user)

    # user management methods

    def get_user(self, username: str) -> User:
        user = accounts.get_user(username)
        return UserDAO.convert_from_db(user)

    def get_user_by_email(self, email: str) -> User:
        email = AuthUtils.sanitize_email(email=email)
        if not email:
            raise exceptions.invalid_params('email is required')

        users = self.user_dao.get_user_by_email(email=email)
        if len(users) > 1:
            self.logger.warning(f'Multiple users found with email {email}')
            raise exceptions.SocaException(error_code=errorcodes.AUTH_MULTIPLE_USERS_FOUND,
                                           message=f'Multiple users found with email {email}')
        user = users[0] if users else None
        if not user:
            raise exceptions.SocaException(
                error_code=errorcodes.AUTH_USER_NOT_FOUND,
                message=f'User not found with email: {email}'
            )
        return UserDAO.convert_from_db(user)

    def sign_up_user(self, request: SignUpUserRequest):
        if not self.is_cognito_self_sign_up_enabled():
            raise exceptions.SocaException(
                error_code=errorcodes.COGNITO_SELF_SIGN_UP_DISABLED,
                message='Cognito self sign up is disabled.'
            )

        email = request.email
        password = request.password
        if Utils.is_empty(email):
            raise exceptions.invalid_params('email is required')
        if Utils.is_empty(password):
            raise exceptions.invalid_params('password is required')

        username, domain = request.email.split('@')
        if not re.match(constants.COGNITO_USERNAME_REGEX, username):
            raise exceptions.invalid_params(constants.COGNITO_USERNAME_ERROR_MESSAGE)

        try:
            existing_user = accounts.get_user(username)

            if existing_user is not None:
                raise exceptions.invalid_params(f'User already exists: {username}')
        except res_exceptions.UserNotFound as e:
            pass

        self.check_user_password_against_cognito_user_pool_policy(password)

        self.user_pool.sign_up_user(
            username=username,
            email=email,
            password=password,
        )

    def confirm_sign_up(self, request: ConfirmSignUpRequest):
        if not self.is_cognito_self_sign_up_enabled():
            raise exceptions.SocaException(
                error_code=errorcodes.COGNITO_SELF_SIGN_UP_DISABLED,
                message='Cognito self sign up is disabled.'
            )

        email = request.email
        confirmation_code = request.confirmation_code
        if Utils.is_empty(email):
            raise exceptions.invalid_params('email is required')
        if Utils.is_empty(confirmation_code):
            raise exceptions.invalid_params('confirmation code is required')

        username, domain = request.email.split('@')
        if not re.match(constants.COGNITO_USERNAME_REGEX, username):
            raise exceptions.invalid_params(constants.COGNITO_USERNAME_ERROR_MESSAGE)

        self.user_pool.confirm_sign_up(
            username=username,
            confirmation_code=confirmation_code,
        )

        accounts.create_user({
            'username': username,
            'email': email,
            'additional_groups': [],
            'login_shell':  auth_constants.DEFAULT_LOGIN_SHELL,
            'home_dir': os.path.join(auth_constants.USER_HOME_DIR_BASE, username),
            'sudo': False,
            'enabled': True,
            'role': constants.USER_ROLE,
            'is_active': True,
            'identity_source': constants.COGNITO_USER_IDP_TYPE
        })

    def resend_confirmation_code(self, request: ResendConfirmationCodeRequest):
        if not self.is_cognito_self_sign_up_enabled():
            raise exceptions.SocaException(
                error_code=errorcodes.COGNITO_SELF_SIGN_UP_DISABLED,
                message='Cognito self sign up is disabled.'
            )

        username = request.username
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        if not re.match(constants.COGNITO_USERNAME_REGEX, username):
            raise exceptions.invalid_params(constants.COGNITO_USERNAME_ERROR_MESSAGE)

        self.user_pool.resend_confirmation_code(username)

    def modify_user(self, user: User) -> User:
        db_user = UserDAO.convert_to_db(user)
        db_user.pop('is_active', None)
        updated_user = accounts.update_user(db_user)

        if user.is_active:
            # Only handle user activation as the account servie doesn't define the deactivation workflow currently.
            updated_user = accounts.activate_user({"username": user.username})

        return UserDAO.convert_from_db(updated_user)

    def check_user_password_against_cognito_user_pool_policy(self, password: str):
        if password is None or not password.strip():
            raise exceptions.invalid_params('Password is required')

        user_pool_password_policy = self.user_pool.describe_password_policy()
        # Validate password compliance versus Cognito user pool password policy
        # Cognito: https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-policies.html
        if len(password) < user_pool_password_policy.minimum_length:
            raise exceptions.invalid_params(f'Password should be at least {user_pool_password_policy.minimum_length} characters long')
        elif len(password) > 256:
            raise exceptions.invalid_params(f'Password can be up to 256 characters')
        elif user_pool_password_policy.require_numbers and re.search('[0-9]', password) is None:
            raise exceptions.invalid_params('Password should include at least 1 number')
        elif user_pool_password_policy.require_uppercase and re.search('[A-Z]', password) is None:
            raise exceptions.invalid_params('Password should include at least 1 uppercase letter')
        elif user_pool_password_policy.require_lowercase and re.search('[a-z]', password) is None:
            raise exceptions.invalid_params('Password should include at least 1 lowercase letter')
        elif user_pool_password_policy.require_symbols and re.search('[\^\$\*\.\[\]{}\(\)\?"!@#%&\/\\,><\':;\|_~`=\+\-]', password) is None:
            raise exceptions.invalid_params('Password should include at least 1 of these special characters: ^ $ * . [ ] { } ( ) ? " ! @ # % & / \ , > < \' : ; | _ ~ ` = + -')

    def activate_user(self, existing_user: User):
        accounts.activate_user(UserDAO.convert_to_db(existing_user))

    def disable_user(self, username: str):
        if self.is_cluster_administrator(username):
            raise AuthUtils.invalid_operation('Cluster Administrator cannot be disabled.')

        accounts.update_user({'username': username, 'enabled': False}, force=True)
        self.evdi_client.publish_user_disabled_event(username=username)

    def reset_password(self, username: str):
        username = AuthUtils.sanitize_username(username)
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        if not self.is_cluster_administrator(username):
            raise AuthUtils.invalid_operation('Only Cluster Administrator password can be reset.')

        # trigger reset password email
        self.user_pool.admin_reset_password(username)

    def list_users(self, request: ListUsersRequest) -> ListUsersResult:
        return self.user_dao.list_users(request)

    def change_password(self, access_token: str, username: str, old_password: str, new_password: str):
        """
        change password for given username in user pool
        this method expects an access token from an already logged-in user, who is trying to change their password.
        :return:
        """

        if not self.is_cluster_administrator(username):
            raise AuthUtils.invalid_operation('Only Cluster Administrator password can be changed.')

        # change password in user pool before changing in ldap
        self.user_pool.change_password(
            username=username,
            access_token=access_token,
            old_password=old_password,
            new_password=new_password
        )

    def get_user_from_access_token(self, access_token: str) -> Optional[User]:
        decoded_token = self.token_service.decode_token(token=access_token)
        token_username = decoded_token.get('username')
        return self.get_user_from_token_username(token_username=token_username)

    def get_user_from_token_username(self, token_username: str) -> Optional[User]:
        if not token_username:
            raise exceptions.unauthorized_access()
        email = self.token_service.get_email_from_token_username(token_username=token_username)
        user = None
        if email:
            user = self.get_user_by_email(email=email)
        else:
            # This is for clusteradmin
            user = self.get_user(username=token_username)
        return user

    def add_role_dbusername_to_auth_result(self, authresult: InitiateAuthResult, ssoAuth: bool = False) -> Optional[InitiateAuthResult]:
        access_token = authresult.auth.access_token
        user = self.get_user_from_access_token(access_token=access_token)
        if user.enabled:
            if not ssoAuth and user.identity_source == constants.SSO_USER_IDP_TYPE:
                self.sign_out(authresult.auth.refresh_token, sso_auth=ssoAuth)
                self.logger.error(msg=f'User {user.username} already exists as SSO user. Denied login.')
                raise exceptions.unauthorized_access()
            else:
                authresult.role = user.role
                authresult.db_username = user.username
                return authresult
        else:
            self.sign_out(authresult.auth.refresh_token, sso_auth=ssoAuth)
            self.logger.error(msg=f'User {user.username} is disabled. Denied login.')
            raise exceptions.unauthorized_access()

    # public API methods for user onboarding, login, forgot password flows.
    def initiate_auth(self, request: InitiateAuthRequest) -> InitiateAuthResult:
        auth_flow = request.auth_flow
        if Utils.is_empty(auth_flow):
            raise exceptions.invalid_params('auth_flow is required.')

        enable_native_user_login = self.context.config().get_bool('identity-provider.cognito.enable_native_user_login', required=True)

        if auth_flow == 'USER_PASSWORD_AUTH':
            cognito_username = request.cognito_username
            password = request.password
            if not self.is_cluster_administrator(cognito_username) and not enable_native_user_login:
                raise exceptions.unauthorized_access()
            authresult = self.user_pool.initiate_username_password_auth(request)
            if not authresult.challenge_name:
                authresult = self.add_role_dbusername_to_auth_result(authresult=authresult)
            return authresult
        elif auth_flow == 'REFRESH_TOKEN_AUTH':
            cognito_username = request.cognito_username
            refresh_token = request.refresh_token
            if not self.is_cluster_administrator(cognito_username):
                raise exceptions.unauthorized_access()
            authresult = self.user_pool.initiate_refresh_token_auth(
                username=cognito_username, refresh_token=refresh_token)
            authresult = self.add_role_dbusername_to_auth_result(authresult=authresult)
            return authresult
        elif auth_flow == 'SSO_AUTH':
            if not self.is_sso_enabled():
                raise exceptions.unauthorized_access()

            authorization_code = request.authorization_code
            if Utils.is_empty(authorization_code):
                raise exceptions.invalid_params('authorization_code is required.')

            db_sso_state = self.sso_state_dao.get_sso_state(authorization_code)
            if not db_sso_state:
                raise exceptions.unauthorized_access()

            self.sso_state_dao.delete_sso_state(authorization_code)
            authresult = InitiateAuthResult(
                auth=AuthResult(
                    access_token= db_sso_state.get('access_token'),
                    refresh_token= db_sso_state.get('refresh_token'),
                    id_token= db_sso_state.get('id_token'),
                    expires_in= db_sso_state.get('expires_in'),
                    token_type= db_sso_state.get('token_type'),
                )
            )
            authresult = self.add_role_dbusername_to_auth_result(authresult=authresult, ssoAuth=True)
            return authresult
        elif auth_flow == 'SSO_REFRESH_TOKEN_AUTH':
            if not self.is_sso_enabled():
                raise exceptions.unauthorized_access()
            cognito_username = request.cognito_username
            refresh_token = request.refresh_token
            authresult = self.user_pool.initiate_refresh_token_auth(
                username=cognito_username, refresh_token=refresh_token, sso=True)
            authresult = self.add_role_dbusername_to_auth_result(authresult=authresult, ssoAuth=True)
            return authresult

    def respond_to_auth_challenge(self, request: RespondToAuthChallengeRequest) -> RespondToAuthChallengeResult:

        if Utils.is_empty(request.username):
            raise exceptions.invalid_params('username is required.')

        challenge_name = request.challenge_name
        if Utils.is_empty(challenge_name):
            raise exceptions.invalid_params('challenge_name is required.')
        if challenge_name != 'NEW_PASSWORD_REQUIRED':
            raise exceptions.invalid_params(f'challenge_name: {challenge_name} is not supported.')

        if Utils.is_empty(request.session):
            raise exceptions.invalid_params('session is required.')

        if Utils.is_empty(request.new_password):
            raise exceptions.invalid_params('new_password is required.')

        self.logger.debug(f'respond_to_auth_challenge() - Request: {request}')

        result = self.user_pool.respond_to_auth_challenge(request)

        return result

    def forgot_password(self, username: str):
        """
        invoke user pool's forgot password API
        introduce mandatory timing delays to ensure valid / invalid user invocations are processed in approximately the same time
        """
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        wait_time_seconds = 5
        start = Utils.current_time_ms()
        self.user_pool.forgot_password(username)
        end = Utils.current_time_ms()
        total_secs = (end - start) / 1000

        if total_secs <= wait_time_seconds:
            time.sleep(wait_time_seconds - total_secs)

    def confirm_forgot_password(self, username: str, password: str, confirmation_code: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        if Utils.is_empty(password):
            raise exceptions.invalid_params('password is required')
        if Utils.is_empty(confirmation_code):
            raise exceptions.invalid_params('confirmation_code is required')

        # update user-pool first to verify confirmation code.
        self.user_pool.confirm_forgot_password(username, password, confirmation_code)

    def sign_out(self, refresh_token: str, sso_auth: bool):
        """
        revokes the refresh token issued by InitiateAuth API.
        """
        self.token_service.revoke_authorization(
            refresh_token=refresh_token,
            sso_auth=sso_auth
        )

    def global_sign_out(self, username: str):
        """
        Signs out a user from all devices.
        It also invalidates all refresh tokens that Amazon Cognito has issued to a user.
        The user's current access and ID tokens remain valid until they expire.
        """

        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        self.user_pool.admin_global_sign_out(username=username)

    def configure_sso(self, request: ConfigureSSORequest):
        self.logger.info(f"Configure sso request: {request}")
        payload = json.dumps({ "configure_sso_request": request.dict(exclude_none=True, by_alias=True) })

        response = self.context.aws().aws_lambda().invoke(
            FunctionName=f"{self.cluster_name}-configure_sso",
            Payload=payload,
        )
        self.logger.info(f"Configure sso response: {response}")
        if 'FunctionError' in response:
            response_payload = json.loads(response['Payload'].read())
            if 'errorMessage' in response_payload:
                raise exceptions.soca_exception(
                    error_code=errorcodes.GENERAL_ERROR,
                    message=response_payload['errorMessage']
                )
            raise exceptions.soca_exception(
                    error_code=errorcodes.GENERAL_ERROR,
                    message=response['FunctionError']
            )
        elif response['StatusCode'] == 200:
            try:
                ad_sync_client.start_ad_sync() # submit ad_sync task after configuring SSO
            except res_exceptions.ADSyncInProcess:
                # AD Sync may have been triggered by the scheduler Lambda and is still in progress
                pass


    def update_quic(self, quic: bool) -> UpdateQuicResults:
        return self.quic_update_helper.update_quic_config(quic)
