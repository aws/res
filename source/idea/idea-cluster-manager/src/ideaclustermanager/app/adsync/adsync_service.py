#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideaclustermanager.app.tasks.task_manager import TaskManager
from ideasdk.context import SocaContext

from ideaclustermanager.app.accounts.ldapclient.ldap_utils import LdapUtils
from ideasdk.utils import Utils

from ideadatamodel import (
    ListGroupsRequest,
    ListUsersRequest,
    Group,
    User,
    SocaPaginator,
    constants,
    exceptions,
    errorcodes,
    SocaFilter,
)


class ADSyncService:
    def __init__(self, context: SocaContext, task_manager: TaskManager):
        self.context = context
        self.logger = context.logger("ad-sync")
        self.task_manager = task_manager

    def sync_from_ad(self):
        self.task_manager.send(task_name="adsync.sync-from-ad", payload={})

    def fetch_all_ldap_groups(self) -> list[dict]:
        self.logger.info("Fetching LDAP groups")
        ldap_groups, _ = self.context.accounts.ldap_client.search_groups()
        return ldap_groups

    def fetch_all_res_identified_groups(self) -> list[Group]:
        self.logger.info("Fetching RES groups")
        result = self.context.accounts.group_dao.list_groups(ListGroupsRequest(paginator=SocaPaginator()))
        res_identified_groups = result.listing

        while result.paginator.cursor:
            result = self.context.accounts.group_dao.list_groups(
                ListGroupsRequest(paginator=SocaPaginator(cursor=result.cursor))
            )
            res_identified_groups.extend(result.listing)

        return res_identified_groups

    def sync_all_groups(self, ldap_groups):
        ldap_groups_by_unique_identifier = {group["name"]: group for group in ldap_groups}
        ldap_group_unique_identifiers = set([group['name'] for group in ldap_groups])

        res_identified_groups = self.fetch_all_res_identified_groups()
        res_identified_groups_by_unique_identifier = {g.name: g for g in res_identified_groups}
        res_identified_group_unique_identifiers = set([g.name for g in res_identified_groups])

        group_addition_failures = set()
        for group_unique_identifier in ldap_group_unique_identifiers - res_identified_group_unique_identifiers:
            self.logger.info(f"Detected group: {group_unique_identifier} addition in AD")
            self.handle_group_addition(group=ldap_groups_by_unique_identifier[group_unique_identifier], group_addition_failures=group_addition_failures)

        for group_unique_identifier in res_identified_group_unique_identifiers - ldap_group_unique_identifiers:
            if (
                res_identified_groups_by_unique_identifier[group_unique_identifier].type
                != constants.GROUP_TYPE_INTERNAL
            ):
                self.logger.info(f"Detected group: {group_unique_identifier} deletion in AD")
                self.handle_group_deletion(group=res_identified_groups_by_unique_identifier[group_unique_identifier])
        return group_addition_failures

    def handle_group_addition(self, group, group_addition_failures):
        """
        group addition in RES
        params: group: dict(), todo: convert group dict to Group class object for uniformity.
        """
        is_admin = self.context.accounts.ldap_client.ldap_sudoers_group_name == group["name"]
        try:
            self.context.accounts.create_group(
                group=Group(
                    title=group["name"],
                    name=group["name"],
                    ds_name=group["name"],
                    gid=group["gid"],
                    group_type=constants.GROUP_TYPE_PROJECT,
                    type=constants.GROUP_TYPE_EXTERNAL,
                    role=constants.ADMIN_ROLE if is_admin else constants.USER_ROLE,
                )
            )
            self.logger.info(f"Added {group['name']} to RES successfully")
        # todo: handle specific exception(s)
        except Exception as e:
            group_addition_failures.add(group["name"])
            self.logger.error(f"Error while adding group {group['name']} to RES. Error: {e}")

    def handle_group_deletion(self, group):
        """
        group deletion in RES
        params: group: Group
        """
        try:
            self.context.accounts.delete_group(group_name=group.name, force=True)
            self.logger.info(f"Deleted {group.name} from RES successfully")
        # todo: handle specific exception(s)
        except Exception as e:
            self.logger.error(f"Error while deleting group {group.name} from RES. Error: {e}")

    def fetch_all_ldap_users_in_group(self, ldap_group_name) -> list[dict]:
        ldap_base = self.context.accounts.ldap_client.ldap_base
        filter_str = (
            f"(&(objectClass=user)(memberOf=cn={ldap_group_name},{self.context.accounts.ldap_client.ldap_user_base}))"
        )
        ldap_users, _ = self.context.accounts.ldap_client.search_users(
            username_filter=SocaFilter(), ldap_base=ldap_base, filter_str=filter_str
        )
        return ldap_users

    def fetch_ldap_users_in_ou(self) -> list[dict]:
        ldap_users, _ = self.context.accounts.ldap_client.search_users(username_filter=SocaFilter())
        return ldap_users

    def consolidate_ldap_users_by_unique_identifier(
        self, ldap_users: list, ldap_users_by_unique_identifier: dict, ldap_group_name: str = None
    ):
        for ldap_user in filter(lambda u: 'sam_account_name' in u, ldap_users):
            sam_account_name = str(ldap_user['sam_account_name']).lower()
            if sam_account_name not in ldap_users_by_unique_identifier:
                ldap_users_by_unique_identifier[sam_account_name] = ldap_user

            user = ldap_users_by_unique_identifier[sam_account_name]
            if ldap_group_name:
                user['additional_groups'] = list(set(user.get('additional_groups', []) + [ldap_group_name]))

    def get_ldap_users_by_unique_identifier(self, ldap_groups):
        self.logger.info("Fetching LDAP users")

        ldap_users_by_unique_identifier = dict()
        ldap_users_in_ou = self.fetch_ldap_users_in_ou()
        self.consolidate_ldap_users_by_unique_identifier(
            ldap_users=ldap_users_in_ou,
            ldap_users_by_unique_identifier=ldap_users_by_unique_identifier,
            ldap_group_name=None,
        )

        for ldap_group in ldap_groups:
            ldap_users_in_group = self.fetch_all_ldap_users_in_group(ldap_group_name=ldap_group['name'])
            self.consolidate_ldap_users_by_unique_identifier(
                ldap_users=ldap_users_in_group,
                ldap_users_by_unique_identifier=ldap_users_by_unique_identifier,
                ldap_group_name=ldap_group['name'],
            )

        return ldap_users_by_unique_identifier

    def fetch_all_res_identified_users(self) -> list[User]:
        self.logger.info("Fetching RES users")
        result = self.context.accounts.user_dao.list_users(ListUsersRequest(paginator=SocaPaginator()))
        res_identified_users = result.listing

        while result.paginator.cursor:
            result = self.context.accounts.user_dao.list_users(
                ListUsersRequest(paginator=SocaPaginator(cursor=result.cursor))
            )

            res_identified_users.extend(result.listing)

        return res_identified_users

    def sync_all_users(self, ldap_groups, group_addition_failures):
        admin_group = self.context.accounts.ldap_client.ldap_sudoers_group_name
        ldap_users_by_unique_identifier = self.get_ldap_users_by_unique_identifier(ldap_groups)
        ldap_user_unique_identifiers = set(ldap_users_by_unique_identifier.keys())

        res_identified_users = self.fetch_all_res_identified_users()
        res_identified_users_by_unique_identifier = {u.username: u for u in res_identified_users}
        res_identified_user_unique_identifiers = set([u.username for u in res_identified_users])

        for user_unique_identifier in ldap_user_unique_identifiers - res_identified_user_unique_identifiers:
            self.logger.info(f"Detected user: {user_unique_identifier} addition in AD")
            user = ldap_users_by_unique_identifier[user_unique_identifier]
            self.handle_user_addition(user=user, admin_group=admin_group)

        for user_unique_identifier in res_identified_user_unique_identifiers - ldap_user_unique_identifiers:
            self.logger.info(f"Detected user: {user_unique_identifier} deletion in AD")
            self.handle_user_deletion(user=res_identified_users_by_unique_identifier[user_unique_identifier])

        for user_unique_identifier in filter(
            lambda u: not self.context.accounts.is_cluster_administrator(u),
            ldap_user_unique_identifiers & res_identified_user_unique_identifiers,
        ):
            ldap_user_object = ldap_users_by_unique_identifier[user_unique_identifier]
            ldap_user_additional_groups = set(ldap_user_object.get("additional_groups", [])) - group_addition_failures

            res_user_object = res_identified_users_by_unique_identifier[user_unique_identifier]
            res_user_additional_groups = set(res_user_object.additional_groups or [])

            username = ldap_user_object['sam_account_name']

            for group_name in ldap_user_additional_groups - res_user_additional_groups:
                self.handle_user_addition_to_group(username=username, group_name=group_name)

            for group_name in res_user_additional_groups - ldap_user_additional_groups:
                self.handle_user_removal_from_group(username=username, group_name=group_name)

    def handle_user_addition(self, user, admin_group):
        additional_groups = set(user.get('additional_groups', []))
        is_admin = admin_group in additional_groups
        if is_admin:
            self.logger.info(f"Designating user {user['sam_account_name']} as admin")

        try:
            password = Utils.generate_password(8, 2, 2, 2, 2)
            self.context.accounts.create_user(
                user=User(
                    username=user['sam_account_name'],
                    password=password,
                    email=user['email'],
                    uid=user['uid'],
                    gid=user['gid'],
                    login_shell=user['login_shell'],
                    home_dir=user['home_dir'],
                    additional_groups=additional_groups,
                    sudo=is_admin,
                    is_active=False,
                    role=constants.ADMIN_ROLE if is_admin else constants.USER_ROLE,
                ),
                email_verified=True,
            )
            self.logger.info(f"Added {user['sam_account_name']} to RES successfully")
        # todo: handle specific exception(s)
        except Exception as e:
            self.logger.error(f"Error while adding user {user['sam_account_name']} to RES. Error: {e}")

    def handle_user_deletion(self, user):
        try:
            self.context.accounts.delete_user(username=user.username)
            self.logger.info(f"Deleted user {user.username} from RES successfully")
        # todo: handle specific exception(s)
        except Exception as e:
            self.logger.error(f"Error while deleting user {user.username} from RES. Error: {e}")

    def handle_user_addition_to_group(self, username: str, group_name: str):
        admin_group = self.context.accounts.ldap_client.ldap_sudoers_group_name

        try:
            self.logger.info(f"Detected user {username} addition to group {group_name} in AD")
            self.context.accounts.add_users_to_group([username], group_name)

            if group_name == admin_group:
                self.logger.info(f"Designating user {username} as admin")
                self.context.accounts.add_admin_user(username=username)

            self.context.accounts.user_dao.update_user(
                {'username': username, 'synced_on': Utils.current_time_ms()}
            )
            self.logger.info(f"Added user {username} to group {group_name} successfully")
        except Exception as e:
            self.logger.error(f"Error while adding user {username} to group {group_name} in RES. Error: {e}")

    def handle_user_removal_from_group(self, username: str, group_name: str):
        admin_group = self.context.accounts.ldap_client.ldap_sudoers_group_name

        try:
            group = self.context.accounts.get_group(group_name=group_name)

            if group.type == constants.GROUP_TYPE_INTERNAL:
                return

            self.logger.info(f"Detected user {username} removal from group {group_name} in AD")
            self.context.accounts.remove_users_from_group([username], group_name)

            if group_name == admin_group:
                self.logger.info(f"Removing user {username} as admin")
                self.context.accounts.remove_admin_user(username=username)

            self.context.accounts.user_dao.update_user(
                {'username': username, 'synced_on': Utils.current_time_ms()}
            )
            self.logger.info(f"Removed user {username} from group {group_name} successfully")

        except exceptions.SocaException as e:
            user = self.context.accounts.get_user(username=username)
            if e.error_code == errorcodes.AUTH_GROUP_NOT_FOUND and not user.is_active:
                self.logger.info(f"Detected removal of inactive user {username} from deleted group {group_name}.")
                self.context.accounts.user_dao.update_user({
                    'username': username,
                    'additional_groups': list(set(user.additional_groups) - {group_name})
                })
                self.logger.info(f"Removed inactive user {username} from group {group_name} successfully")
        except Exception as e:
            self.logger.error(
                f"Error while removing user {username} from group {group_name} in RES. Error: {e}"
            )
