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

import ldap  # noqa
from ideaclustermanager import AppContext
from ideaclustermanager.app.accounts.ldapclient import LdapClientOptions, OpenLDAPClient
from ideasdk.utils import Utils
from ideatestutils import IdeaTestProps

test_props = IdeaTestProps()


class MockLdapClient(OpenLDAPClient):
    def __init__(self, context: AppContext):
        super().__init__(
            context=context,
            options=LdapClientOptions(
                domain_name="idea.local",
                uri="ldap://localhost",
                root_username="mock",
                root_password="mock",
            ),
        )

    def add_s(self, dn, modlist):
        trace_message = (
            f'ldapadd -x -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{dn}"'
        )
        attributes = []
        for mod in modlist:
            key = mod[0]
            values = []
            for value in mod[1]:
                values.append(Utils.from_bytes(value))
            attributes.append(f'{key}={",".join(values)}')
        self.logger.info(f'> {trace_message}, attributes: ({" ".join(attributes)})')

    def modify_s(self, dn, modlist):
        trace_message = (
            f'ldapmodify -x -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{dn}"'
        )
        attributes = []
        for mod in modlist:
            key = mod[1]
            values = []
            for value in mod[2]:
                values.append(Utils.from_bytes(value))
            attributes.append(f'{key}={",".join(values)}')
        self.logger.info(f'> {trace_message}, attributes: ({" ".join(attributes)})')

    def delete_s(self, dn):
        trace_message = (
            f'ldapdelete -x -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{dn}"'
        )
        self.logger.info(f"> {trace_message}")

    def search_s(
        self,
        base,
        scope=ldap.SCOPE_SUBTREE,
        filterstr=None,
        attrlist=None,
        attrsonly=0,
        trace=True,
    ):
        trace_message = f'ldapsearch -x -b "{base}" -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{filterstr}"'
        if attrlist is not None:
            trace_message = f'{trace_message} {" ".join(attrlist)}'
        self.logger.info(f"> {trace_message}")
        return ()

    def is_existing_user(self, username):
        trace_message = f'ldapisexistinguser -x -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{username}"'
        self.logger.info(f"> {trace_message}")
        if test_props.get_non_existent_username() in username:
            return False
        return True
