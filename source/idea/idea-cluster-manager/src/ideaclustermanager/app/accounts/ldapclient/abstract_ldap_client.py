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

from ideadatamodel import (
    exceptions, errorcodes, constants,
    SocaBaseModel,
    SocaFilter,
    SocaPaginator
)
from ideasdk.context import SocaContext
from ideasdk.utils import Utils
from ideaclustermanager.app.accounts.ldapclient.ldap_utils import LdapUtils

from typing import Optional, Dict, List, Tuple
import ldap  # noqa
from ldap.ldapobject import LDAPObject  # noqa
from ldap.controls import SimplePagedResultsControl  # noqa
from ldap.controls.vlv import VLVRequestControl, VLVResponseControl  # noqa
from ldap.controls.sss import SSSRequestControl, SSSResponseControl  # noqa
from ldappool import ConnectionManager  # noqa
from abc import abstractmethod
import base64
import logging


class LdapClientOptions(SocaBaseModel):
    uri: Optional[str]
    domain_name: Optional[str]
    root_username: Optional[str]
    root_password: Optional[str]
    root_username_secret_arn: Optional[str]
    root_password_secret_arn: Optional[str]
    root_username_file: Optional[str]
    root_password_file: Optional[str]
    connection_pool_enabled: Optional[bool]
    connection_pool_size: Optional[int]
    connection_retry_max: Optional[int]
    connection_retry_delay: Optional[float]
    connection_timeout: Optional[float]
    ad_netbios: Optional[str]
    directory_id: Optional[str]
    password_max_age: Optional[float]


DEFAULT_LDAP_CONNECTION_POOL_SIZE = 10
DEFAULT_LDAP_CONNECTION_RETRY_MAX = 60
DEFAULT_LDAP_CONNECTION_RETRY_DELAY = 10
DEFAULT_LDAP_CONNECTION_TIMEOUT = 10
DEFAULT_LDAP_ENABLE_CONNECTION_POOL = True
DEFAULT_LDAP_PAGE_SIZE = 100
DEFAULT_LDAP_PAGE_START = 0
DEFAULT_LDAP_COOKIE = ''

UID_MIN = 5000
UID_MAX = 65533  # 65534 is for "nobody" and 65535 is reserved
GID_MIN = 5000
GID_MAX = 65533


class AbstractLDAPClient:

    def __init__(self, context: SocaContext, options: LdapClientOptions, logger=None):
        self.context = context

        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('ldap-client')

        self.options = options

        if Utils.is_empty(self.domain_name):
            raise exceptions.general_exception('options.domain_name is required')

        self._root_username: Optional[str] = None
        self._root_password: Optional[str] = None

        self.refresh_root_username_password()

        # initialize pooled connection manager for LDAP to conserve resources
        # Set any LDAP options that may be needed
        self.logger.debug(f"Setting LDAP options..")
        default_ldap_options = [
            { 'name': 'Referrals' , 'code': ldap.OPT_REFERRALS, 'value': ldap.OPT_OFF },
            { 'name': 'Protocol Version', 'code': ldap.OPT_PROTOCOL_VERSION, 'value': ldap.VERSION3 }
        ]
        for option in default_ldap_options:
            self.logger.debug(f"Setting default option: {option.get('name')}({option.get('code')}) -> {option.get('value')}")
            ldap.set_option(option.get('code'), option.get('value'))
            self.logger.debug(f"Confirming default option: {option.get('name')}({option.get('code')}) -> {ldap.get_option(option.get('code'))}")

        configured_ldap_options = self.context.config().get_list('directoryservice.ldap_options', default=[])
        if configured_ldap_options:
            self.logger.debug(f"Obtained LDAP options from directoryservice.ldap_options: {configured_ldap_options}")
            for option in configured_ldap_options:
                opt_d = dict(eval(option))
                if isinstance(opt_d, dict):
                    self.logger.debug(f"Setting configured option: {opt_d.get('name')}({opt_d.get('code')}) -> {opt_d.get('value')}")
                    ldap.set_option(opt_d.get('code'), opt_d.get('value'))
                    self.logger.debug(f"Confirming configured option: {opt_d.get('name')}({opt_d.get('code')}) -> {ldap.get_option(opt_d.get('code'))}")

        self.logger.debug(f"Starting LDAP connection pool to {self.ldap_uri}")
        self.connection_manager = ConnectionManager(
            uri=self.ldap_uri,
            size=Utils.get_as_int(options.connection_pool_size, DEFAULT_LDAP_CONNECTION_POOL_SIZE),
            retry_max=Utils.get_as_int(options.connection_retry_max, DEFAULT_LDAP_CONNECTION_RETRY_MAX),
            retry_delay=Utils.get_as_float(options.connection_retry_delay, DEFAULT_LDAP_CONNECTION_RETRY_DELAY),
            timeout=Utils.get_as_float(options.connection_timeout, DEFAULT_LDAP_CONNECTION_TIMEOUT),
            use_pool=Utils.get_as_bool(options.connection_pool_enabled, DEFAULT_LDAP_ENABLE_CONNECTION_POOL)
        )

    def filter_out_referrals_from_response(self, results):
        # Response might contain search_ref results based on AD configuration. 
        # This result item does not correspond to a user in the AD instead corresponds to alternate location in which the client may search for additional matching entries.
        # Below logic filters out references from the results
        # https://ldapwiki.com/wiki/Wiki.jsp?page=Search%20Responses
        
        filter_criteria = lambda x: x[0] != None
        search_results = []
        referrals = []
        
        for result in results: 
            if filter_criteria(result):
                search_results.append(result)
            else:
                referrals.append(result)
        
        if(referrals): self.logger.debug(f"Referrals skipped in result response: {referrals}")
        
        return search_results

    # ldap wrapper methods
    def add_s(self, dn, modlist):
        trace_message = f'ldapadd -x -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{dn}"'
        attributes = []
        for mod in modlist:
            key = mod[0]
            values = []
            for value in mod[1]:
                values.append(Utils.from_bytes(value))
            attributes.append(f'{key}={",".join(values)}')
        self.logger.info(f'> {trace_message}, attributes: ({" ".join(attributes)})')
        with self.get_ldap_root_connection() as conn:
            conn.add_s(dn, modlist)

    def modify_s(self, dn, modlist):
        trace_message = f'ldapmodify -x -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{dn}"'
        attributes = []
        for mod in modlist:
            key = mod[1]
            values = []
            for value in mod[2]:
                values.append(Utils.from_bytes(value))
            attributes.append(f'{key}={",".join(values)}')
        self.logger.info(f'> {trace_message}, attributes: ({" ".join(attributes)})')
        with self.get_ldap_root_connection() as conn:
            conn.modify_s(dn, modlist)

    def delete_s(self, dn):
        trace_message = f'ldapdelete -x -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{dn}"'
        self.logger.info(f'> {trace_message}')
        with self.get_ldap_root_connection() as conn:
            conn.delete_s(dn)

    def search_s(self, base, scope=ldap.SCOPE_SUBTREE, filterstr=None, attrlist=None, attrsonly=0, trace=True):
        if trace:
            trace_message = f'ldapsearch -x -b "{base}" -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{filterstr}"'
            if attrlist is not None:
                trace_message = f'{trace_message} {" ".join(attrlist)}'
            self.logger.info(f'> {trace_message}')

        with self.get_ldap_root_connection() as conn:
            results = conn.search_s(base, scope, filterstr, attrlist, attrsonly)
            return self.filter_out_referrals_from_response(results)

    def simple_paginated_search(
        self,
        base,
        scope=ldap.SCOPE_SUBTREE,
        filterstr=None,
        attrlist=None,
        attrsonly=0,
        timeout=-1,
        page_size: int = None,
    ) -> Dict:
        trace_message = f'ldapsearch -x -b "{base}" -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{filterstr}"'
        if attrlist is not None:
            trace_message = f'{trace_message} {" ".join(attrlist)}'
        self.logger.info(f'> {trace_message}')
        result = []
        page_size = Utils.get_as_int(page_size, DEFAULT_LDAP_PAGE_SIZE)

        with self.get_ldap_root_connection() as conn:
            serverctrls = SimplePagedResultsControl(True, size=page_size, cookie='')
            message_id = conn.search_ext(base, scope, filterstr, attrlist, attrsonly, [serverctrls], None, timeout)

            while True:
                rtype, rdata, rmsgid, res_serverctrls = conn.result3(message_id)
                result.extend(rdata)

                controls = [
                    control
                    for control in res_serverctrls
                    if control.controlType == SimplePagedResultsControl.controlType
                ]

                if not controls or len(controls) == 0 or not controls[0].cookie:
                    break

                # cookie = Utils.from_bytes(base64.b64encode(controls[0].cookie))
                serverctrls.cookie = controls[0].cookie
                message_id = conn.search_ext(base, scope, filterstr, attrlist, attrsonly, [serverctrls], None, timeout)


            filtered_result = self.filter_out_referrals_from_response(result)
            return {'result': filtered_result, 'total': None, 'cookie': None}

    def sssvlv_paginated_search(self,
                                base,
                                sort_by: str,
                                scope=ldap.SCOPE_SUBTREE,
                                filterstr=None,
                                attrlist=None,
                                attrsonly=0,
                                timeout=-1,
                                start=0,
                                page_size: int = None) -> Dict:
        """
        Server Side Sorting and Virtual List View (SSSVLV) based search and paging for LDAP
        Refer to https://ldapwiki.com/wiki/Virtual%20List%20View%20Control for more details

        start: 0 based offset
        ldap offsets are 1 based, but to normalize pagination across all soca services,
        all paging offsets must start with 0 for SOCA services

        sort_by: <attributeName>:<matchingRule>
        eg.
            1. gidNumber:integerOrderingMatch
            2. uidNumber:integerOrderingMatch
            3. cn:caseIgnoreOrderingMatch
        Refer to https://ldapwiki.com/wiki/MatchingRule for more details.

        :param base:
        :param sort_by:
        :param scope:
        :param filterstr:
        :param attrlist:
        :param attrsonly:
        :param timeout: float
        :param start: int, default 0
        :param page_size: int, default: 20
        :return:
        """
        trace_message = f'ldapsearch -x -b "{base}" -D "{self.ldap_root_bind}" -H {self.ldap_uri} "{filterstr}"'
        if attrlist is not None:
            trace_message = f'{trace_message} {" ".join(attrlist)}'
        self.logger.info(f'> {trace_message}')
        result = []

        # sssvlv has a limit on no. of concurrent paginated result sets per connection to manage memory.
        # and does not offer a clean way to manage or clean up paginated results.
        # to overcome this, create a new connection each time instead of using a pooled connection
        # this comes at a significant performance hit and needs to be assessed based on no. of users and size of directory
        conn = None
        try:
            conn = ldap.initialize(self.ldap_uri)
            conn.bind_s(who=self.ldap_root_bind, cred=self.ldap_root_password, method=ldap.AUTH_SIMPLE)

            page_size = Utils.get_as_int(page_size, DEFAULT_LDAP_PAGE_SIZE)
            page_start = Utils.get_as_int(start, DEFAULT_LDAP_PAGE_START)

            serverctrls = [
                VLVRequestControl(
                    criticality=True,
                    before_count=0,
                    after_count=page_size - 1,
                    offset=page_start + 1,
                    content_count=0
                ),
                SSSRequestControl(
                    criticality=True,
                    ordering_rules=[sort_by]
                )
            ]

            message_id = conn.search_ext(base, scope, filterstr, attrlist, attrsonly, serverctrls, None, timeout)
            rtype, rdata, rmsgid, res_serverctrls = conn.result3(message_id)

            total = 0
            for res_control in res_serverctrls:
                if res_control.controlType == VLVResponseControl.controlType:
                    total = res_control.content_count

            result.extend(rdata)
            return {
                'result': result,
                'total': total
            }

        except ldap.VLV_ERROR:
            return {
                'result': result,
                'total': 0
            }
        finally:
            try:
                if conn:
                    conn.unbind_s()
            except AttributeError:
                pass

    @property
    def ds_provider(self) -> str:
        return self.context.config().get_string('directoryservice.provider', required=True)

    def is_openldap(self) -> bool:
        return self.ds_provider == constants.DIRECTORYSERVICE_OPENLDAP

    def is_activedirectory(self) -> bool:
        return self.ds_provider in (
            constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY,
            constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY
        )
    def is_readonly(self) -> bool:
        return self.ds_provider in (
            constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY
        )

    @property
    def domain_name(self) -> str:
        return self.options.domain_name

    @property
    def ldap_base(self) -> str:
        tokens = self.domain_name.split('.')
        return f'dc={",dc=".join(tokens)}'

    @property
    def ldap_uri(self) -> str:
        if Utils.is_not_empty(self.options.uri):
            return self.options.uri
        return 'ldap://localhost'

    @property
    def password_max_age(self) -> Optional[float]:
        return self.options.password_max_age

    def fetch_root_username(self) -> str:
        if Utils.is_not_empty(self.options.root_username):
            return self.options.root_username

        file = self.options.root_username_file
        if Utils.is_not_empty(file) and Utils.is_file(file):
            with open(file, 'r') as f:
                return f.read().strip()

        secret_arn = self.options.root_username_secret_arn
        if Utils.is_not_empty(secret_arn):
            result = self.context.aws().secretsmanager().get_secret_value(
                SecretId=secret_arn
            )
            return Utils.get_value_as_string('SecretString', result)

        raise exceptions.soca_exception(
            error_code=errorcodes.GENERAL_ERROR,
            message='DS root username/password not configured'
        )

    def fetch_root_password(self) -> str:
        if Utils.is_not_empty(self.options.root_password):
            return self.options.root_password

        file = self.options.root_password_file
        if Utils.is_not_empty(file) and Utils.is_file(file):
            with open(file, 'r') as f:
                return f.read().strip()

        secret_arn = self.options.root_password_secret_arn
        if Utils.is_not_empty(secret_arn):
            result = self.context.aws().secretsmanager().get_secret_value(
                SecretId=secret_arn
            )
            return Utils.get_value_as_string('SecretString', result)

        raise exceptions.soca_exception(
            error_code=errorcodes.GENERAL_ERROR,
            message='DS root username/password not configured'
        )

    def update_root_password(self, password: str):
        if Utils.is_not_empty(self.options.root_password):
            self.options.root_password = password

        file = self.options.root_password_file
        if Utils.is_not_empty(file) and Utils.is_file(file):
            with open(file, 'w') as f:
                f.write(password)

        secret_arn = self.options.root_password_secret_arn
        if Utils.is_not_empty(secret_arn):
            self.context.aws().secretsmanager().put_secret_value(
                SecretId=secret_arn,
                SecretString=password
            )

        self._root_password = password

    def refresh_root_username_password(self):
        self._root_username = self.fetch_root_username()
        self._root_password = self.fetch_root_password()

    @property
    def ldap_root_username(self) -> str:
        return self._root_username

    @property
    def ldap_root_password(self) -> str:
        return self._root_password

    def get_ldap_root_connection(self) -> LDAPObject:
        """
        returns an LDAP connection object bound to ROOT user from the connection pool
        """
        res = self.connection_manager.connection(
            bind=self.ldap_root_bind,
            passwd=self.ldap_root_password
        )
        if self.logger.isEnabledFor(logging.DEBUG):
            cm_info = str(self.connection_manager)
            self.logger.debug(f"LDAP CM returning conn ({res}), CM now:\n{cm_info}")

        return res

    @staticmethod
    def convert_ldap_group(ldap_group: Dict) -> Optional[Dict]:
        if Utils.is_empty(ldap_group):
            return None
        name = LdapUtils.get_string_value('cn', ldap_group)
        gid = LdapUtils.get_int_value('gidNumber', ldap_group)
        users = LdapUtils.get_string_list('memberUid', ldap_group)

        return {
            'name': name,
            'gid': gid,
            'users': users
        }

    def is_existing_group(self, group_name: str) -> bool:
        if Utils.is_empty(group_name):
            raise exceptions.invalid_params('group_name is required')

        result = self.search_s(
            base=self.ldap_group_base,
            filterstr=self.build_group_filterstr(group_name),
            attrlist=['cn']
        )

        return len(result) > 0

    def is_existing_user(self, username: str) -> bool:

        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')

        results = self.search_s(
            base=self.ldap_base,
            filterstr=self.build_user_filterstr(username),
            attrlist=['sAMAccountName']
        )

        return len(results) > 0

    def is_sudo_user(self, username: str) -> bool:
        results = self.search_s(
            base=self.ldap_sudoers_base,
            filterstr=self.build_sudoer_filterstr(username),
            attrlist=['sAMAccountName']
        )

        return len(results) > 0


    @property
    @abstractmethod
    def ldap_computers_base(self) -> str:
        ...

    @property
    @abstractmethod
    def ldap_user_base(self) -> str:
        ...

    @property
    @abstractmethod
    def ldap_user_filterstr(self) -> str:
        ...

    def build_computer_dn(self, computer: str) -> str:
        return f'cn={computer},{self.ldap_computers_base}'

    def build_user_dn(self, username: str) -> str:
        return f'cn={username},{self.ldap_user_base}'

    def build_user_filterstr(self, username: str) -> str:
        return f'(&{self.ldap_user_filterstr}(sAMAccountName={username}))'

    @property
    @abstractmethod
    def ldap_group_base(self) -> str:
        ...

    @property
    @abstractmethod
    def ldap_group_filterstr(self) -> str:
        ...

    def build_group_dn(self, group_name: str) -> str:
        return f'cn={group_name},{self.ldap_group_base}'

    def build_group_filterstr(self, group_name: str = None, username: str = None) -> str:
        filterstr = self.ldap_group_filterstr
        if group_name is not None:
            # Check if we have a fully qualified
            if group_name.upper().startswith('CN='):
                filterstr = f'{filterstr}(distinguishedName={group_name})'
            else:
                filterstr = f'{filterstr}(cn={group_name})'
        if username is not None:
            filterstr = f'{filterstr}(memberUid={username})'
        return f'(&{filterstr})'

    @property
    @abstractmethod
    def ldap_sudoers_base(self) -> str:
        ...

    @property
    @abstractmethod
    def ldap_sudoer_filterstr(self) -> str:
        ...

    def build_sudoer_filterstr(self, username: str) -> str:
        return f'(&{self.ldap_sudoer_filterstr}(sAMAccountName={username}))'

    @property
    @abstractmethod
    def ldap_root_bind(self) -> str:
        ...

    @abstractmethod
    def change_password(self, username: str, password: str):
        ...

    def convert_ldap_user(self, ldap_user: Dict) -> Optional[Dict]:
        if Utils.is_empty(ldap_user):
            return None

        self.logger.debug(f'convert_ldap_user() - Converting from full lookup results: {ldap_user}')

        cn = LdapUtils.get_string_value('cn', ldap_user)
        username = LdapUtils.get_string_value('uid', ldap_user)
        if Utils.is_empty(username):
            username = LdapUtils.get_string_value('sAMAccountName', ldap_user)
        sam_account_name = LdapUtils.get_string_value('sAMAccountName', ldap_user)
        email = LdapUtils.get_string_value('mail', ldap_user)
        uid = LdapUtils.get_int_value('uidNumber', ldap_user)
        gid = LdapUtils.get_int_value('gidNumber', ldap_user)
        login_shell = LdapUtils.get_string_value('loginShell', ldap_user)
        home_dir = LdapUtils.get_string_value('homeDirectory', ldap_user)

        # UserAccountControl from ActiveDirectory
        if self.is_activedirectory():
            user_account_control = LdapUtils.get_int_value('userAccountControl', ldap_user)
        else:
            user_account_control = None

        password_last_set = None
        password_last_set_win = LdapUtils.get_int_value('pwdLastSet', ldap_user)
        if password_last_set_win is not None and password_last_set_win != 0:
            password_last_set = Utils.from_win_timestamp(password_last_set_win)

        result = {
            'cn': cn,
            'username': username,
            'sam_account_name': sam_account_name,
            'email': email,
            'uid': uid,
            'gid': gid,
            'login_shell': login_shell,
            'home_dir': home_dir,
            'user_account_control': user_account_control
        }

        if password_last_set:
            result['password_last_set'] = password_last_set
            result['password_max_age'] = self.password_max_age

        return result

    def get_group(self, group_name: str) -> Optional[Dict]:
        self.logger.debug(f"abstract_ldap-get_group(): Attempting to lookup {group_name} . Base: {self.ldap_group_base}")
        result = self.search_s(
            base=self.ldap_group_base,
            filterstr=self.build_group_filterstr(group_name)
        )

        if len(result) == 0:
            return None

        return self.convert_ldap_group(result[0][1])

    @abstractmethod
    def sync_group(self, group_name: str, gid: int) -> Dict:
        ...

    def get_all_groups_with_user(self, username: str) -> List[str]:
        ldap_result = self.search_s(
            base=self.ldap_group_base,
            filterstr=self.build_group_filterstr(username=username),
            attrlist=['cn']
        )

        result = []
        for ldap_group in ldap_result:
            name = LdapUtils.get_string_value('cn', ldap_group[1])
            result.append(name)

        return result

    def search_groups(self, group_name_filter: SocaFilter = None,
                      username_filter: SocaFilter = None,
                      page_size: int = None,
                      start: int = 0) -> Tuple[List[Dict], SocaPaginator]:
        result = []

        group_name_token = None
        if group_name_filter is not None:
            if Utils.is_not_empty(group_name_filter.eq):
                group_name_token = group_name_filter.eq
            elif Utils.is_not_empty(group_name_filter.starts_with):
                group_name_token = f'{group_name_filter.starts_with}*'
            elif Utils.is_not_empty(group_name_filter.ends_with):
                group_name_token = f'*{group_name_filter.ends_with}'
            elif Utils.is_not_empty(group_name_filter.like):
                group_name_token = f'*{group_name_filter.like}*'

        username_token = None
        if username_filter is not None:
            if Utils.is_not_empty(username_filter.eq):
                username_token = username_filter.eq
            elif Utils.is_not_empty(username_filter.starts_with):
                username_token = f'{username_filter.starts_with}*'
            elif Utils.is_not_empty(username_filter.ends_with):
                username_token = f'*{username_filter.ends_with}'
            elif Utils.is_not_empty(username_filter.like):
                username_token = f'*{username_filter.like}*'

        if Utils.are_empty(group_name_token, username_token):
            filterstr = self.ldap_group_filterstr
        else:
            filterstr = self.build_group_filterstr(group_name=group_name_token, username=username_token)

        if self.is_activedirectory():

            search_result = self.simple_paginated_search(
                base=self.ldap_group_base,
                filterstr=filterstr
            )

            ldap_result = search_result.get('result', [])
            total = len(ldap_result)

        else:

            search_result = self.sssvlv_paginated_search(
                base=self.ldap_group_base,
                sort_by='gidNumber:integerOrderingMatch',
                filterstr=filterstr,
                page_size=page_size,
                start=start
            )

            ldap_result = search_result.get('result', [])
            total = Utils.get_value_as_int('total', search_result)

        for ldap_group in ldap_result:
            user_group = self.convert_ldap_group(ldap_group[1])
            if Utils.is_empty(user_group):
                continue
            result.append(user_group)

        return result, SocaPaginator(page_size=page_size, start=start, total=total)

    def add_user_to_group(self, usernames: List[str], group_name: str):
        try:
            group_dn = self.build_group_dn(group_name)
            group_attrs = []
            for username in usernames:
                group_attrs.append((ldap.MOD_ADD, 'memberUid', [Utils.to_bytes(username)]))
            self.modify_s(group_dn, group_attrs)
        except ldap.TYPE_OR_VALUE_EXISTS:
            pass

    def remove_user_from_group(self, usernames: List[str], group_name: str):
        group_dn = self.build_group_dn(group_name)
        mod_attrs = []
        for username in usernames:
            mod_attrs.append((ldap.MOD_DELETE, 'memberUid', [Utils.to_bytes(username)]))
        self.modify_s(group_dn, mod_attrs)

    def delete_group(self, group_name: str):
        if not self.is_existing_group(group_name):
            return

        group_dn = self.build_group_dn(group_name)
        self.delete_s(group_dn)

    @abstractmethod
    def add_sudo_user(self, username: str):
        ...

    @abstractmethod
    def remove_sudo_user(self, username: str):
        ...

    def list_sudo_users(self) -> List[str]:
        result = []

        ldap_result = self.search_s(
            base=self.ldap_sudoers_base,
            filterstr=self.ldap_sudoer_filterstr,
            attrlist=['sAMAccountName']
        )

        for entry in ldap_result:
            sudo_user = entry[1]
            username = LdapUtils.get_string_value('sAMAccountName', sudo_user)
            result.append(username)

        return result

    def get_user(self, username: str, trace=True) -> Optional[Dict]:

        results = self.search_s(
            base=self.ldap_user_base,
            filterstr=self.build_user_filterstr(username),
            trace=trace
        )

        if len(results) == 0:
            return None

        return self.convert_ldap_user(results[0][1])

    @abstractmethod
    def create_service_account(self, username: str, password: str):
        ...

    @abstractmethod
    def sync_user(self, *,
                  uid: int,
                  gid: int,
                  username: str,
                  email: str,
                  login_shell: str,
                  home_dir: str) -> Dict:
        ...

    def update_computer_description(self, computer: str, description: str):
        computer_dn = self.build_computer_dn(computer)
        computer_attrs = [
            (ldap.MOD_REPLACE, 'description', [Utils.to_bytes(description)])
        ]
        self.modify_s(computer_dn, computer_attrs)

    def update_email(self, username: str, email: str):
        user_dn = self.build_user_dn(username)
        user_attrs = [
            (ldap.MOD_REPLACE, 'mail', [Utils.to_bytes(email)])
        ]
        self.modify_s(user_dn, user_attrs)

    def delete_user(self, username: str):
        user_dn = self.build_user_dn(username)
        self.delete_s(user_dn)

    def search_users(
        self,
        username_filter: SocaFilter,
        ldap_base: str = None,
        filter_str: str = None,
        page_size: int = None,
        start: int = 0,
    ) -> Tuple[List[Dict], SocaPaginator]:
        result = []

        if not filter_str:
            filter_str = self.ldap_user_filterstr

        if username_filter is not None:
            if Utils.is_not_empty(username_filter.eq):
                filter_str = self.build_user_filterstr(username=username_filter.eq)
            elif Utils.is_not_empty(username_filter.starts_with):
                filter_str = self.build_user_filterstr(username=f'{username_filter.starts_with}*')
            elif Utils.is_not_empty(username_filter.ends_with):
                filter_str = self.build_user_filterstr(username=f'*{username_filter.ends_with}')
            elif Utils.is_not_empty(username_filter.like):
                filter_str = self.build_user_filterstr(username=f'*{username_filter.like}*')

        if not ldap_base:
            ldap_base = self.ldap_user_base

        if self.is_activedirectory():
            search_result = self.simple_paginated_search(base=ldap_base, filterstr=filter_str)

            ldap_result = search_result.get('result', [])
            total = len(ldap_result)

        else:

            search_result = self.sssvlv_paginated_search(
                base=ldap_base,
                sort_by='uidNumber:integerOrderingMatch',
                filterstr=filter_str,
                page_size=page_size,
                start=start
            )

            ldap_result = search_result.get('result', [])
            total = Utils.get_value_as_int('total', search_result)

        for ldap_user in ldap_result:
            user = self.convert_ldap_user(ldap_user[1])
            if Utils.is_empty(user):
                continue
            result.append(user)

        return result, SocaPaginator(page_size=page_size, start=start, total=total)

    def authenticate_user(self, username: str, password: str) -> bool:
        try:
            user_dn = self.build_user_dn(username)
            conn = ldap.initialize(self.ldap_uri)
            # try bind
            conn.bind_s(who=user_dn, cred=password, method=ldap.AUTH_SIMPLE)
            # free resources
            conn.unbind_ext_s()
            return True
        except ldap.INVALID_CREDENTIALS:
            return False
