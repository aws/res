#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import logging
from typing import Any, Dict, Optional, Tuple, Union

import ldap  # type: ignore
from ldap.controls import SimplePagedResultsControl  # type: ignore
from ldap.controls.sss import SSSRequestControl, SSSResponseControl  # type: ignore
from ldap.controls.vlv import VLVRequestControl, VLVResponseControl  # type: ignore
from ldap.ldapobject import LDAPObject  # type: ignore
from ldappool import ConnectionManager  # type: ignore
from pydantic import BaseModel
from res.resources import cluster_settings  # type: ignore
from res.utils import aws_utils, sssd_utils  # type: ignore

DEFAULT_LDAP_CONNECTION_POOL_SIZE = 10
DEFAULT_LDAP_CONNECTION_RETRY_MAX = 60
DEFAULT_LDAP_CONNECTION_RETRY_DELAY = 10
DEFAULT_LDAP_CONNECTION_TIMEOUT = 10
DEFAULT_LDAP_ENABLE_CONNECTION_POOL = True
DEFAULT_LDAP_PAGE_SIZE = 100


def from_bytes(value: Union[bytes, bytearray]) -> str:
    if isinstance(value, bytes):
        return str(value, "utf-8")
    else:
        return value.decode("utf-8")


class ActiveDirectoryClientOptions(BaseModel):
    uri: Optional[str]
    domain_name: Optional[str]
    service_account_credentials_secret_arn: Optional[str]
    groups_filter: Optional[str]
    groups_ou: Optional[str]
    users_filter: Optional[str]
    users_ou: Optional[str]
    sudoers_group_name: Optional[str]
    ldap_base: Optional[str]
    tls_certificate_secret_arn: Optional[str]
    service_account_dn_secret_arn: Optional[str]
    sssd_ldap_id_mapping: Optional[str]


def get_active_directory_client_options() -> ActiveDirectoryClientOptions:
    settings: Dict[str, Any] = cluster_settings.get_settings()

    return ActiveDirectoryClientOptions(
        uri=settings.get("directoryservice.ldap_connection_uri"),
        domain_name=settings.get("directoryservice.name"),
        service_account_credentials_secret_arn=settings.get(
            "directoryservice.service_account_credentials_secret_arn"
        ),
        users_filter=settings.get(
            "directoryservice.users_filter", "(sAMAccountName=*)"
        ),
        groups_ou=settings.get("directoryservice.groups.ou"),
        groups_filter=settings.get(
            "directoryservice.groups_filter", "(sAMAccountName=*)"
        ),
        users_ou=settings.get("directoryservice.users.ou"),
        sudoers_group_name=settings.get("directoryservice.sudoers.group_name"),
        ldap_base=settings.get("directoryservice.ldap_base"),
        tls_certificate_secret_arn=settings.get(
            "directoryservice.tls_certificate_secret_arn"
        ),
        service_account_dn_secret_arn=settings.get(
            "directoryservice.root_user_dn_secret_arn"
        ),
        sssd_ldap_id_mapping=(
            settings.get("directoryservice.sssd.ldap_id_mapping", "false").lower()
        ),
    )


class ActiveDirectoryClient:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.options = get_active_directory_client_options()

        self._service_account_username, self._service_account_password = (
            self.fetch_service_account_credentials()
        )

        # initialize pooled connection manager for LDAP to conserve resources
        # Set any LDAP options that may be needed
        self.logger.debug(f"Setting LDAP options..")
        default_ldap_options = [
            {"name": "Referrals", "code": ldap.OPT_REFERRALS, "value": ldap.OPT_OFF},
            {
                "name": "Protocol Version",
                "code": ldap.OPT_PROTOCOL_VERSION,
                "value": ldap.VERSION3,
            },
        ]
        if self.options.tls_certificate_secret_arn:
            default_ldap_options.append(
                {
                    "name": "TLS CA Cert Dir",
                    "code": ldap.OPT_X_TLS_CACERTDIR,
                    "value": sssd_utils.TLS_CA_CERT_DIR,
                }
            )
            default_ldap_options.append(
                {
                    "name": "TLS CA Cert File",
                    "code": ldap.OPT_X_TLS_CACERTFILE,
                    "value": sssd_utils.TLS_CA_CERT_FILE_PATH,
                }
            )
        for option in default_ldap_options:
            self.logger.debug(
                f"Setting default option: {option.get('name')}({option.get('code')}) -> {option.get('value')}"
            )
            ldap.set_option(option.get("code"), option.get("value"))
            self.logger.debug(
                f"Confirming default option: {option.get('name')}({option.get('code')}) -> {ldap.get_option(option.get('code'))}"
            )

        self.logger.debug(f"Starting LDAP connection pool to {self.ldap_uri}")
        self.connection_manager = ConnectionManager(
            uri=self.ldap_uri,
            size=DEFAULT_LDAP_CONNECTION_POOL_SIZE,
            retry_max=DEFAULT_LDAP_CONNECTION_RETRY_MAX,
            retry_delay=DEFAULT_LDAP_CONNECTION_RETRY_DELAY,
            timeout=DEFAULT_LDAP_CONNECTION_TIMEOUT,
            use_pool=DEFAULT_LDAP_ENABLE_CONNECTION_POOL,
        )

    def filter_out_referrals_from_response(self, results: list[Any]) -> list[Any]:
        # Response might contain search_ref results based on AD configuration.
        # This result item does not correspond to a user in the AD instead corresponds to alternate location in which the client may search for additional matching entries.
        # Below logic filters out references from the results
        # https://ldapwiki.com/wiki/Wiki.jsp?page=Search%20Responses
        search_results = []
        referrals = []

        for result in results:
            if result[0]:
                search_results.append(result)
            else:
                referrals.append(result)

        if referrals:
            self.logger.debug(f"Referrals skipped in result response: {referrals}")

        return search_results

    # ldap wrapper methods
    def add_s(self, dn, modlist):
        trace_message = f'ldapadd -x -D "{self.ldap_service_account_bind}" -H {self.ldap_uri} "{dn}"'
        attributes = []
        for mod in modlist:
            key = mod[0]
            values = []
            for value in mod[1]:
                values.append(from_bytes(value))
            attributes.append(f'{key}={",".join(values)}')
        self.logger.info(f'> {trace_message}, attributes: ({" ".join(attributes)})')
        with self.get_ldap_service_account_connection() as conn:
            conn.add_s(dn, modlist)

    def modify_s(self, dn, modlist):
        trace_message = f'ldapmodify -x -D "{self.ldap_service_account_bind}" -H {self.ldap_uri} "{dn}"'
        attributes = []
        for mod in modlist:
            key = mod[1]
            values = []
            for value in mod[2]:
                values.append(from_bytes(value))
            attributes.append(f'{key}={",".join(values)}')
        self.logger.info(f'> {trace_message}, attributes: ({" ".join(attributes)})')
        with self.get_ldap_service_account_connection() as conn:
            conn.modify_s(dn, modlist)

    def delete_s(self, dn: str) -> None:
        """
        Performs an LDAP delete operation on dn
        :param dn:
        """
        trace_message = f'ldapdelete -x -D "{self.ldap_service_account_bind}" -H {self.ldap_uri} "{dn}"'
        self.logger.info(f"> {trace_message}")

        with self.get_ldap_service_account_connection() as conn:
            conn.delete_s(dn)

    def search_s(
        self,
        base: str,
        scope: int = ldap.SCOPE_SUBTREE,
        filterstr: Optional[str] = None,
        attrlist: Optional[list[str]] = None,
        attrsonly: int = 0,
        trace: bool = True,
    ) -> list[Any]:
        """
        Perform an LDAP search operation. Each result tuple is of the form (dn, attrs),
        where dn is a string containing the DN (distinguished name) of the entry,
        and attrs is a dictionary containing the attributes associated with the entry.
        :param base: The base DN (distinguished name) of the entry
        :param scope: The LDAP scope of the entry
        :param filterstr: The filter to apply to the entry
        :param attrlist: The attributes to search for the entry
        :param attrsonly: Whether to only search for the attributes
        :param trace: Whether to trace LDAP operations
        :return: A dictionary containing the results of the LDAP search operation
        """
        if trace:
            trace_message = f'ldapsearch -x -b "{base}" -D "{self.ldap_service_account_bind}" -H {self.ldap_uri} "{filterstr}"'
            if attrlist is not None:
                trace_message = f'{trace_message} {" ".join(attrlist)}'
            self.logger.info(f"> {trace_message}")

        with self.get_ldap_service_account_connection() as conn:
            results = conn.search_s(base, scope, filterstr, attrlist, attrsonly)
            return self.filter_out_referrals_from_response(results)

    def simple_paginated_search(
        self,
        base: str,
        scope: int = ldap.SCOPE_SUBTREE,
        filterstr: Optional[str] = None,
        attrlist: Optional[list[str]] = None,
        attrsonly: int = 0,
        timeout: int = -1,
    ) -> Dict[str, Any]:
        """
        Perform a paginated LDAP search operation.
        :param base: The base DN (distinguished name) of the entry
        :param scope: The LDAP scope of the entry
        :param filterstr: The filter to apply to the entry
        :param attrlist: The attributes to search for the entry
        :param attrsonly: Whether to only search for the attributes
        :param timeout: Timeout in seconds to wait for the result
        :return: A dictionary containing the results of the LDAP search operation
        """
        trace_message = f'ldapsearch -x -b "{base}" -D "{self.ldap_service_account_bind}" -H {self.ldap_uri} "{filterstr}"'
        if attrlist is not None:
            trace_message = f'{trace_message} {" ".join(attrlist)}'
        self.logger.info(f"> {trace_message}")
        result = []
        page_size = DEFAULT_LDAP_PAGE_SIZE

        with self.get_ldap_service_account_connection() as conn:
            serverctrls = SimplePagedResultsControl(True, size=page_size, cookie="")
            message_id = conn.search_ext(
                base,
                scope,
                filterstr,
                attrlist,
                attrsonly,
                [serverctrls],
                None,
                timeout,
            )

            while True:
                rtype, rdata, rmsgid, res_serverctrls = conn.result3(message_id)
                result.extend(rdata)

                def _control_filter(control):
                    return control.controlType == SimplePagedResultsControl.controlType

                controls = [c for c in res_serverctrls if _control_filter(c)]

                if not controls or len(controls) == 0 or not controls[0].cookie:
                    break

                serverctrls.cookie = controls[0].cookie
                message_id = conn.search_ext(
                    base,
                    scope,
                    filterstr,
                    attrlist,
                    attrsonly,
                    [serverctrls],
                    None,
                    timeout,
                )

            filtered_result = self.filter_out_referrals_from_response(result)
            return {"result": filtered_result, "total": None, "cookie": None}

    def fetch_service_account_credentials(self) -> Tuple[str, str]:
        """
        Fetch service account credentials.
        :return: A tuple containing the service account credentials (username, password)
        """
        secret_arn = self.options.service_account_credentials_secret_arn
        if secret_arn:
            secret = json.loads(aws_utils.get_secret_string(secret_arn))
            if secret:
                return (
                    list(secret.keys())[0],
                    list(secret.values())[0],
                )

        raise Exception(
            "Service account username/password not configured",
        )

    def get_ldap_service_account_connection(self) -> LDAPObject:
        """
        Get the LDAP service account connection.
        :return: an LDAP connection object bound to ROOT user from the connection pool
        """
        conn = self.connection_manager.connection(
            bind=self.ldap_service_account_bind, passwd=self._service_account_password
        )
        if self.logger.isEnabledFor(logging.DEBUG):
            cm_info = str(self.connection_manager)
            self.logger.debug(f"LDAP CM returning conn ({conn}), CM now:\n{cm_info}")

        return conn

    @property
    def ldap_uri(self) -> str:
        """
        LDAP connection URI.
        :return: the LDAP connection URI
        """
        if self.options.uri:
            return self.options.uri
        return "ldap://localhost"

    @property
    def ldap_service_account_bind(self) -> str:
        """
        LDAP service account bind.
        :return: the LDAP service account bind
        """
        return f"{self._service_account_username}@{self.options.domain_name}"
