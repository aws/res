from __future__ import annotations

from ideasdk.context import SocaContext
import pwd
import grp

class SSSD:
    def __init__(self, context: SocaContext):
        self.context = context
        self.logger = context.logger(self.get_name())

    def get_name(self) -> str:
        return 'sssd'

    def ldap_id_mapping(self) -> str:
        return self.context.config().get_string('directoryservice.sssd.ldap_id_mapping', required=True)

    def get_uid_and_gid_for_user(self, username) -> tuple[int, int] | tuple[None, None]:
        try:
            user_info = pwd.getpwnam(username)

            uid = user_info.pw_uid
            gid = user_info.pw_gid

            return uid, gid
        except KeyError:
            self.logger.warning(f"User: {username} not yet available")
            return None, None

    def get_gid_for_group(self, groupname) -> int | None:
        try:
            group_info = grp.getgrnam(groupname)

            gid = group_info.gr_gid

            return gid
        except KeyError:
            self.logger.warning(f"Group: {groupname} not yet available")
            return None
