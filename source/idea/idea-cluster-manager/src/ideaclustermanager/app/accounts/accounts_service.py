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
from ideasdk.client.evdi_client import EvdiClient
from ideasdk.context import SocaContext
from ideadatamodel import AuthResult
from ideadatamodel import (
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
    ListRoleAssignmentsRequest,
    DeleteRoleAssignmentRequest
)
from ideadatamodel import exceptions, errorcodes, constants
from ideasdk.utils import Utils, GroupNameHelper
from ideasdk.auth import TokenService

from ideaclustermanager.app.accounts.ldapclient.abstract_ldap_client import AbstractLDAPClient
from ideaclustermanager.app.accounts.cognito_user_pool import CognitoUserPool
from ideaclustermanager.app.accounts import auth_constants
from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from ideaclustermanager.app.accounts.db.group_dao import GroupDAO
from ideaclustermanager.app.accounts.db.user_dao import UserDAO
from ideaclustermanager.app.accounts.db.group_members_dao import GroupMembersDAO
from ideaclustermanager.app.accounts.db.single_sign_on_state_dao import SingleSignOnStateDAO
from ideaclustermanager.app.accounts.helpers.single_sign_on_helper import SingleSignOnHelper
from ideaclustermanager.app.tasks.task_manager import TaskManager
from ideaclustermanager.app.accounts.helpers.sssd_helper import SSSD
from ideaclustermanager.app.accounts.helpers.quic_update_helper import QuicUpdateHelper, UpdateQuicResults

from typing import Optional, List
import os
import re
import tempfile
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
                 ldap_client: Optional[AbstractLDAPClient],
                 user_pool: Optional[CognitoUserPool],
                 evdi_client: Optional[EvdiClient],
                 task_manager: Optional[TaskManager],
                 token_service: Optional[TokenService]):

        self.context = context
        self.logger = context.logger('accounts-service')
        self.user_pool = user_pool
        self.ldap_client = ldap_client
        self.evdi_client = evdi_client
        self.task_manager = task_manager
        self.token_service = token_service

        self.sssd = SSSD(context)
        self.group_name_helper = GroupNameHelper(context)
        self.user_dao = UserDAO(context, user_pool=user_pool)
        self.group_dao = GroupDAO(context)
        self.group_members_dao = GroupMembersDAO(context, self.user_dao)
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

    # user group management methods

    def get_group(self, group_name: str) -> Optional[Group]:
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        group = self.group_dao.get_group(group_name)

        if group is None:
            raise exceptions.SocaException(
                error_code=errorcodes.AUTH_GROUP_NOT_FOUND,
                message=f'Group not found: {group_name}'
            )

        return self.group_dao.convert_from_db(group)

    def create_group(self, group: Group) -> Group:
        """
        create a new group
        :param group: Group
        """
        ds_readonly = self.ldap_client.is_readonly()

        group_name = group.name
        if not group_name:
            raise exceptions.invalid_params('group.name is required')
        if not group.group_type:
            raise exceptions.invalid_params('group.group_type is required')
        if group.group_type not in constants.ALL_GROUP_TYPES:
            raise exceptions.invalid_params(
                f'invalid group type: {group.group_type}. must be one of: {constants.ALL_GROUP_TYPES}')
        if not group.type:
            group.type = constants.GROUP_TYPE_EXTERNAL
        if group.type not in [constants.GROUP_TYPE_EXTERNAL, constants.GROUP_TYPE_INTERNAL]:
            raise exceptions.invalid_params(
                f'invalid group type: {group.type}. must be one of: {[constants.GROUP_TYPE_EXTERNAL, constants.GROUP_TYPE_INTERNAL]}')

        db_existing_group = self.group_dao.get_group(group_name)
        if db_existing_group is not None:
            raise exceptions.invalid_params(f'group: {group_name} already exists')
        # Perform AD validation only for groups identified as external groups. Internal grpups are RES specific groups and are not expected to be present in the AD.
        if group.type == constants.GROUP_TYPE_EXTERNAL and ds_readonly:
            if not group.ds_name:
                raise exceptions.invalid_params(f'group.ds_name is required when using Read-Only Directory Service: {constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}')
            group_in_ad = self.ldap_client.get_group(group.ds_name)
            if group_in_ad is None:
                raise exceptions.invalid_params(f'group with name {group.ds_name} is not found in Read-Only Directory Service: {constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}')
            group_name_in_ad = group_in_ad['name']
            if group_name_in_ad is None:
                raise exceptions.invalid_params(f'Group name matching the provided name {group.ds_name} is not found in Directory Service: {constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}')
            if group_name_in_ad != group.ds_name:
                raise exceptions.invalid_params(f'group.ds_name {group.ds_name} does not match the value {group_name_in_ad} read from Directory Service: {constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}')
            group.gid = self.sssd.get_gid_for_group(group_name_in_ad)
            if group.gid is None:
                raise exceptions.soca_exception(error_code=errorcodes.GID_NOT_FOUND, message=f'Unable to retrieve GID for Group: {group_name_in_ad}')

        group.enabled = True

        db_group = self.group_dao.convert_to_db(group)

        self.logger.info(
            f"Creating Group {group.name} (AD READ-ONLY: {ds_readonly}) (IS RES-GROUP: {group.type == constants.GROUP_TYPE_INTERNAL})")

        self.group_dao.create_group(db_group)

        return self.group_dao.convert_from_db(db_group)

    def modify_group(self, group: Group) -> Group:
        """
        modify an existing group
        :param group: Group
        """

        group_name = group.name
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        db_group = self.group_dao.get_group(group_name)
        if db_group is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_NOT_FOUND,
                message=f'group not found for group name: {group_name}'
            )

        if not db_group['enabled']:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_IS_DISABLED,
                message='cannot modify a disabled group'
            )

        # do not support modification of group name or GID
        # only title updates are supported
        update_group = {
            'group_name': db_group['group_name'],
            'title': db_group['title']
        }

        # only update db, sync with DS not required.
        updated_group = self.group_dao.update_group(update_group)

        return self.group_dao.convert_from_db(updated_group)

    def delete_group(self, group_name: str, force: bool = False):
        """
        delete a group
        :param group_name:
        :param force: force delete a group even if group has existing members
        :return:
        """

        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        group = self.group_dao.get_group(group_name)

        if group is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_NOT_FOUND,
                message=f'group: {group_name} not found.'
            )

        # Delete User Group relation
        if self.group_members_dao.has_users_in_group(group_name):
            if force:
                usernames = self.group_members_dao.get_usernames_in_group(
                    group_name)
                try:
                    self.remove_users_from_group(
                        usernames, group_name, force)
                except exceptions.SocaException as e:
                    self.logger.info(f"Error: {e}")
            else:
                raise exceptions.soca_exception(
                    error_code=errorcodes.AUTH_INVALID_OPERATION,
                    message='Users associated to group. Group must be empty before it can be deleted.'
                )

        # Delete Project Group relation
        role_assignments = self.context.role_assignments.list_role_assignments(ListRoleAssignmentsRequest(actor_key=f"{group_name}:group")).items
        project_groups = [role_assignment.resource_id for role_assignment in role_assignments if role_assignment.resource_type=='project']
        if project_groups:
            if force:
                try:
                    for role_assignment in role_assignments:
                        self.context.role_assignments_dao.delete_role_assignment(actor_key=role_assignment.actor_key, resource_key=role_assignment.resource_key)
                except exceptions.SocaException as e:
                    self.logger.info(f"Error: {e}")
                    raise e
            else:
                raise exceptions.soca_exception(
                    error_code=errorcodes.AUTH_INVALID_OPERATION,
                    message='Projects associated to group. Group must not be mapped to any project before it can be deleted.'
                )

        self.group_dao.delete_group(group_name=group_name)

    def enable_group(self, group_name: str):
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        group = self.group_dao.get_group(group_name)

        if group is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_NOT_FOUND,
                message=f'group: {group_name} not found.'
            )

        self.group_dao.update_group({
            'group_name': group_name,
            'enabled': True
        })

    def disable_group(self, group_name: str):
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        group = self.group_dao.get_group(group_name)

        if group is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_NOT_FOUND,
                message=f'group: {group_name} not found.'
            )

        self.group_dao.update_group({
            'group_name': group_name,
            'enabled': False
        })

    def list_groups(self, request: ListGroupsRequest) -> ListGroupsResult:
        return self.group_dao.list_groups(request)

    def list_users_in_group(self, request: ListUsersInGroupRequest) -> ListUsersInGroupResult:
        return self.group_members_dao.list_users_in_group(request)

    def add_users_to_group(self, usernames: List[str], group_name: str, bypass_active_user_check: bool = False):
        """
        add users to group
        :param usernames: List of usernames to be added to the group
        :param group_name:
        :param bypass_active_user_check: For an inactive user, the user relation with groups and projects are not updated. The group_name is only added to the user's additional_groups attribute.
        The bypass_active_user_check flag can be used to bypass this check. This is helpful to add users to RES specific admin and user groups, were the user's relations to these groups must be updated
        even if the user is inactive
        :return:
        """
        if Utils.is_empty(usernames):
            raise exceptions.invalid_params('usernames is required')

        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        group = self.group_dao.get_group(group_name)
        if group is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_NOT_FOUND,
                message=f'group: {group_name} not found.'
            )
        if not group['enabled']:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_GROUP_IS_DISABLED,
                message='cannot add users to a disabled user group'
            )

        for username in usernames:
            user = self.user_dao.get_user(username)
            if user is None:
                raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_NOT_FOUND, message=f'user not found: {username}')
            if not user['enabled']:
                raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_IS_DISABLED, message=f'user is disabled: {username}')

            additional_groups = user.get('additional_groups', [])

            if group_name not in additional_groups:
                self.user_dao.update_user({
                    'username': username,
                    'additional_groups': list(set(user.get('additional_groups', []) + [group_name]))
                })

            if bypass_active_user_check or user['is_active'] or Utils.is_test_mode():
                self.group_members_dao.create_membership(group_name, username)

    def remove_user_from_groups(self, username: str, group_names: List[str]):
        """
        remove a user from multiple groups.
        useful for operations such as delete user.
        :param username:
        :param group_names:
        :return:
        """
        if Utils.is_empty(username):
            raise exceptions.invalid_params('usernames is required')
        if Utils.is_empty(group_names):
            raise exceptions.invalid_params('group_names is required')

        self.logger.info(f'removing user: {username} from groups: {group_names}')

        # dedupe and sanitize
        groups_to_remove = []
        for group_name in group_names:
            if group_name in groups_to_remove:
                continue
            groups_to_remove.append(group_name)

        user = self.user_dao.get_user(username)
        if user is None:
            raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_NOT_FOUND, message=f'user not found: {username}')
        if not user['enabled']:
            raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_IS_DISABLED, message=f'user is disabled: {username}')

        additional_groups = user.get('additional_groups', [])

        for group_name in groups_to_remove:
            group = self.group_dao.get_group(group_name)
            if group is None:
                if not user['is_active']:
                    if group_name in additional_groups:
                        additional_groups.remove(group_name)
                else:
                    self.logger.error(f'user: {username} cannot be removed from group: {group_name}. group not found')
                continue
            if not group["enabled"]:
                self.logger.warning(f'user: {username} cannot be removed from group: {group_name}. group is disabled')
                continue

            if group_name in additional_groups:
                additional_groups.remove(group_name)

            self.group_members_dao.delete_membership(group_name, username)

        self.user_dao.update_user({'username': username, 'additional_groups': additional_groups})


    def remove_users_from_group(self, usernames: List[str], group_name: str, force: bool = False):
        """
        remove multiple users from a group
        useful for bulk operations from front end
        :param usernames:
        :param group_name:
        :param force: force delete even if group is disabled. if user is not found, skip user.
        :return:
        """
        if Utils.is_empty(usernames):
            raise exceptions.invalid_params('usernames is required')

        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        try:
            group = self.group_dao.get_group(group_name)
            if group is None:
                raise exceptions.soca_exception(
                    error_code=errorcodes.AUTH_GROUP_NOT_FOUND,
                    message=f'group: {group_name} not found.'
                )
            if not group['enabled'] and not force:
                raise exceptions.soca_exception(
                    error_code=errorcodes.AUTH_GROUP_IS_DISABLED,
                    message='cannot remove users from a disabled user group'
                )

            for username in usernames:
                user = self.user_dao.get_user(username)
                if user is None:
                    if force:
                        continue
                    raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_NOT_FOUND, message=f'user not found: {username}')
                if not user['enabled'] and not force:
                    raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_IS_DISABLED, message=f'user is disabled: {username}')

                additional_groups = user.get('additional_groups', [])
                if group_name in additional_groups:
                    self.user_dao.update_user({
                        'username': username,
                        'additional_groups': list(set(user.get('additional_groups', [])) - {group_name})
                    })

                self.group_members_dao.delete_membership(group_name, username)

        except exceptions.SocaException as e:
            if e.error_code == errorcodes.AUTH_GROUP_NOT_FOUND:
                for username in usernames:
                    user = self.user_dao.get_user(username)
                    if not user['is_active']:
                        self.logger.info(f"Detected removal of inactive user {username} from deleted group {group_name}.")
                        self.context.accounts.user_dao.update_user({
                            'username': username,
                            'additional_groups': list(set(user.get('additional_groups', []) - {group_name}))
                        })
                        self.logger.info(f"Removed inactive user {username} from group {group_name} successfully")
                    else:
                        self.logger.error(f"Failed: Removal of active user {username} from deleted group {group_name}")
            else:
                raise e

    # sudo user management methods

    def add_admin_user(self, username: str):

        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        user = self.user_dao.get_user(username)
        if user is None:
            raise exceptions.SocaException(
                error_code=errorcodes.AUTH_USER_NOT_FOUND,
                message=f'User not found: {username}'
            )

        if user.get('role') == 'admin':
            return

        self.user_dao.update_user({
            'username': username,
            'role': 'admin',
            'sudo': True
        })

    def remove_admin_user(self, username: str):

        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        if self.is_cluster_administrator(username):
            raise AuthUtils.invalid_operation(f'Admin rights cannot be revoked from RES Environment Administrator: {username}.')

        user = self.user_dao.get_user(username)
        if user is None:
            raise exceptions.SocaException(
                error_code=errorcodes.AUTH_USER_NOT_FOUND,
                message=f'User not found: {username}'
            )

        if user.get('role') == 'user':
            return

        self.user_dao.update_user({
            'username': username,
            'role': 'user',
            'sudo': False
        })

    # user management methods

    def get_user(self, username: str) -> User:

        username = AuthUtils.sanitize_username(username)
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required.')

        user = self.user_dao.get_user(username)
        if user is None:
            raise exceptions.SocaException(
                error_code=errorcodes.AUTH_USER_NOT_FOUND,
                message=f'User not found: {username}'
            )

        return self.user_dao.convert_from_db(user)

    def get_user_by_email(self, email: str) -> User:
        email = AuthUtils.sanitize_email(email=email)
        if not email:
            raise exceptions.invalid_params('email is required')

        users = self.user_dao.get_user_by_email(email=email)
        if len(users) > 1:
            self.logger.warn(f'Multiple users found with email {email}')
            raise exceptions.SocaException(error_code=errorcodes.AUTH_MULTIPLE_USERS_FOUND,
                                           message=f'Multiple users found with email {email}')
        user = users[0] if users else None
        if not user:
            raise exceptions.SocaException(
                error_code=errorcodes.AUTH_USER_NOT_FOUND,
                message=f'User not found with email: {email}'
            )
        return self.user_dao.convert_from_db(user)

    def create_user(self, user: User, email_verified: bool = False) -> User:
        """
        create a new user
        """

        # username
        username = user.username
        username = AuthUtils.sanitize_username(username)
        if username == None or len(username.strip()) == 0:
            raise exceptions.invalid_params('user.username is required')
        if not re.match(constants.USERNAME_REGEX, username):
            raise exceptions.invalid_params(constants.USERNAME_ERROR_MESSAGE)
        AuthUtils.check_allowed_username(username)

        bootstrap_user = self.is_cluster_administrator(user.username)

        if not bootstrap_user and not self.ldap_client.is_existing_user(username):
            raise exceptions.invalid_params(f'User {username} does not exist in AD, please add user in AD and retry')

        existing_user = self.user_dao.get_user(username)
        if existing_user is not None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AUTH_USER_ALREADY_EXISTS,
                message=f'username: {username} already exists.'
            )

        # email
        email = user.email
        email = AuthUtils.sanitize_email(email)

        # login_shell
        login_shell = user.login_shell
        if login_shell == None or len(login_shell.strip()) == 0:
            login_shell = auth_constants.DEFAULT_LOGIN_SHELL

        # home_dir
        home_dir = user.home_dir
        if home_dir == None or len(home_dir.strip()) == 0:
            home_dir = os.path.join(auth_constants.USER_HOME_DIR_BASE, username)

        # note: no validations on uid / gid if existing uid/gid is provided.
        # ensuring uid/gid uniqueness is administrator's responsibility.

        # uid and gid
        uid = None
        gid = None
        uid, gid = self.sssd.get_uid_and_gid_for_user(username)
        if (uid is None or gid is None) and not bootstrap_user:
            raise exceptions.soca_exception(error_code=errorcodes.UID_AND_GID_NOT_FOUND, message=f'Unable to retrieve UID and GID for User: {username}')

        # sudo
        sudo = bool(user.sudo)

        # res admin
        admin = user.role == 'admin'

        # is_active
        is_active = bool(user.is_active)

        # password
        if bootstrap_user:
            password = user.password
            if email_verified:
                if password == None or len(password.strip()) == 0:
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
            else:
                self.logger.debug('create_user() - setting password to random value')
                password = Utils.generate_password(8, 2, 2, 2, 2)

            self.logger.info(f'creating Cognito user pool entry: {username}, Email: {email} , email_verified: {email_verified}')
            self.user_pool.admin_create_user(
                username=username,
                email=email,
                password=password,
                email_verified=email_verified
            )

        # additional groups
        additional_groups = Utils.get_as_list(user.additional_groups, [])
        self.logger.debug(f'Additional groups for {username}: {additional_groups}')

        self.logger.info(f"Creating user {username} in RES DDB table")
        created_user = self.user_dao.create_user({
                'username': username,
                'email': email,
                'uid': uid,
                'gid': gid,
                'additional_groups': additional_groups,
                'login_shell': login_shell,
                'home_dir': home_dir,
                'sudo': sudo,
                'enabled': True,
                'role': constants.ADMIN_ROLE if admin else constants.USER_ROLE,
                'is_active': is_active,
            })

        for additional_group in additional_groups:
            self.logger.info(f'Adding username {username} to additional group: {additional_group}')
            self.add_users_to_group([username], additional_group)

        # bootstrap user does not exist in AD, therefore skipping home directory create
        if not bootstrap_user:
            self.task_manager.send(
                task_name='accounts.create-home-directory',
                payload={
                    'username': username
                },
                message_group_id=username
            )

        return self.user_dao.convert_from_db(created_user)

    def modify_user(self, user: User, email_verified: bool = False) -> User:
        """
        Modify User

        ``email``, ``login_shell``, ``sudo``, ``uid``, ``gid``, ``is_active`` updates are supported at the moment.

        :param user:
        :param email_verified:
        :return:
        """

        username = user.username
        username = AuthUtils.sanitize_username(username)

        existing_user = self.user_dao.get_user(username)
        if existing_user is None:
            raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_NOT_FOUND,
                                            message=f'User not found: {username}')
        if not existing_user['enabled']:
            raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_IS_DISABLED,
                                            message='User is disabled and cannot be modified.')

        user_updates = {
            'username': username
        }

        if Utils.is_not_empty(user.email):
            new_email = AuthUtils.sanitize_email(user.email)
            existing_email = Utils.get_value_as_string('email', existing_user)
            if existing_email != new_email:
                user_updates['email'] = new_email

        if Utils.is_not_empty(user.login_shell):
            user_updates['login_shell'] = user.login_shell

        if user.sudo is not None:
            user_updates['sudo'] = Utils.get_as_bool(user.sudo, False)

        if user.uid is not None:
            user_updates['uid'] = user.uid

        if user.gid is not None:
            user_updates['gid'] = user.gid

        updated_user = self.user_dao.update_user(user_updates)
        updated_user = self.user_dao.convert_from_db(updated_user)
        if user.is_active:
            # Only handle user activation as the account servie doesn't define the deactivation workflow currently.
            self.activate_user(updated_user)
            updated_user.is_active = True

        return updated_user

    def activate_user(self, existing_user: User):
        if not existing_user.is_active:
            username = existing_user.username
            for additional_group in existing_user.additional_groups or []:
                try:
                    self.logger.info(f'Adding username {username} to additional group: {additional_group}')
                    self.context.accounts.add_users_to_group([username], additional_group, bypass_active_user_check=True)
                except Exception as e:
                    self.logger.warning(f'Could not add user {username} to group {additional_group}')
            self.user_dao.update_user({'username': username, 'is_active': True})


    def enable_user(self, username: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        existing_user = self.user_dao.get_user(username)
        if existing_user is None:
            raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_NOT_FOUND,
                                            message=f'User not found: {username}')

        is_enabled = Utils.get_value_as_bool('enabled', existing_user, False)
        if is_enabled:
            return
        self.user_dao.update_user({'username': username, 'enabled': True})


    def disable_user(self, username: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        if self.is_cluster_administrator(username):
            raise AuthUtils.invalid_operation('Cluster Administrator cannot be disabled.')

        existing_user = self.user_dao.get_user(username)
        if existing_user is None:
            raise exceptions.soca_exception(error_code=errorcodes.AUTH_USER_NOT_FOUND,
                                            message=f'User not found: {username}')

        is_enabled = Utils.get_value_as_bool('enabled', existing_user, False)
        if not is_enabled:
            return

        self.user_dao.update_user({'username': username, 'enabled': False})
        self.evdi_client.publish_user_disabled_event(username=username)

    def delete_user(self, username: str):
        log_tag = f'(DeleteUser: {username})'

        if self.is_cluster_administrator(username):
            raise AuthUtils.invalid_operation('Cluster Administrator cannot be deleted.')

        user = self.user_dao.get_user(username=username)
        if user is None:
            self.logger.info(f'{log_tag} user not found. skip.')
            return

        groups = Utils.get_value_as_list('additional_groups', user, [])

        if Utils.is_not_empty(groups):
            self.logger.info(f'{log_tag} clean-up group memberships')
            try:
                self.remove_user_from_groups(username=username, group_names=groups)
            except exceptions.SocaException as e:
                if e.error_code == errorcodes.AUTH_USER_IS_DISABLED:
                    pass
                else:
                    raise e

        # delete user from db
        self.logger.info(f'{log_tag} delete user in ddb')
        self.user_dao.delete_user(username=username)
        
        role_assignments = self.context.role_assignments.list_role_assignments(ListRoleAssignmentsRequest(actor_key=f"{username}:user")).items
        project_id_links = [role_assignment.resource_id for role_assignment in role_assignments if role_assignment.resource_type=='project']
        if project_id_links:
            try:
                for role_assignment in role_assignments:
                    self.context.role_assignments_dao.delete_role_assignment(actor_key=role_assignment.actor_key, resource_key=role_assignment.resource_key)
            except exceptions.SocaException as e:
                self.logger.error(f"Error deleting user-project role association: {e}")
                raise e

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
            user =  self.get_user(username=token_username)
        return user

    def add_role_dbusername_to_auth_result(self, authresult: InitiateAuthResult, ssoAuth: bool = False) -> Optional[InitiateAuthResult]:
        access_token = authresult.auth.access_token
        user = self.get_user_from_access_token(access_token=access_token)
        if user.enabled:
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

        if auth_flow == 'USER_PASSWORD_AUTH':
            cognito_username = request.cognito_username
            password = request.password
            if not self.is_cluster_administrator(cognito_username):
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

    def _get_gid_from_existing_ldap_group(self, groupname: str):
        existing_gid = None
        existing_group_from_ds = self.ldap_client.get_group(group_name=groupname)
        self.logger.debug(f'READ-ONLY DS lookup results for group  {groupname}: {existing_group_from_ds}')

        if existing_group_from_ds is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message=f'Unable to Resolve a required RES group from directory services: RES group {groupname}'
            )

        existing_gid = Utils.get_value_as_int('gid', existing_group_from_ds, default=None)

        if existing_gid is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.GENERAL_ERROR,
                message=f'Found group without POSIX gidNumber attribute - UNABLE to use this group. Update group with gidNumber attribute within Directory Service: {groupname}'
            )

        return existing_gid

    def create_defaults(self):
        ds_readonly = self.ldap_client.is_readonly()

        self.logger.info(f'Creating defaults. Read-Only status: {ds_readonly}')

        try:
            # cluster admin user
            admin_username = self.context.config().get_string('cluster.administrator_username', required=True)
            admin_email = self.context.config().get_string('cluster.administrator_email', required=True)
            admin_user = self.user_dao.get_user(username=admin_username)
            if admin_user is None:
                self.logger.info(f'creating cluster admin user: {admin_username}')
                self.create_user(
                    user=User(
                        username=admin_username,
                        email=admin_email,
                        sudo=False,
                        role='admin',
                        is_active=True,  # cluster admin always considered active user
                    ),
                    email_verified=False,
                )
        except Exception as e:
            self.logger.error(f"Error during clusteradmin user creation: {e}")

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
            self.context.ad_sync.sync_from_ad() # submit ad_sync task after configuring SSO


    def update_quic(self, quic: bool) -> UpdateQuicResults:
        return self.quic_update_helper.update_quic_config(quic)

