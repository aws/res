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

from ideasdk.context import SocaContext
from ideadatamodel import constants, exceptions

from ideaclustermanager.app.accounts.ldapclient import AbstractLDAPClient, LdapClientOptions, OpenLDAPClient, ActiveDirectoryClient

from typing import TypeVar
import json

AbstractLDAPClientType = TypeVar('AbstractLDAPClientType', bound=AbstractLDAPClient)


def build_ldap_client(context: SocaContext, logger=None) -> AbstractLDAPClientType:
    ds_provider = context.config().get_string('directoryservice.provider', required=True)
    if ds_provider == constants.DIRECTORYSERVICE_OPENLDAP:

        ldap_connection_uri = context.config().get_string('directoryservice.ldap_connection_uri', required=True)
        domain_name = context.config().get_string('directoryservice.name', required=True)
        ds_service_account_username, ds_service_account_password = get_credentials_value_from_secret_arn(context)

        return OpenLDAPClient(
            context=context,
            options=LdapClientOptions(
                uri=ldap_connection_uri,
                domain_name=domain_name,
                root_username=ds_service_account_username,
                root_password=ds_service_account_password
            ),
            logger=logger
        )

    elif ds_provider in {constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY, constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY}:

        domain_name = context.config().get_string('directoryservice.name', required=True)
        if ds_provider == constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY:
            directory_id = context.config().get_string('directoryservice.directory_id', required=True)
        else:
            # Self-managed AD does not have a directory_id
            directory_id = None
        ad_netbios = context.config().get_string('directoryservice.ad_short_name', required=True)
        ldap_connection_uri = context.config().get_string('directoryservice.ldap_connection_uri', required=True)
        ds_service_account_username, ds_service_account_password = get_credentials_value_from_secret_arn(context)
        password_max_age = context.config().get_int('directoryservice.password_max_age', required=True)

        return ActiveDirectoryClient(
            context=context,
            options=LdapClientOptions(
                uri=ldap_connection_uri,
                domain_name=domain_name,
                root_username=ds_service_account_username,
                root_password=ds_service_account_password,
                ad_netbios=ad_netbios,
                directory_id=directory_id,
                password_max_age=password_max_age
            ),
            logger=logger
        )

    else:

        raise exceptions.general_exception(f'directory service provider: {ds_provider} not supported')

def get_credentials_value_from_secret_arn(context: SocaContext) -> str:
    ds_service_account_credentials = context.config().get_secret('directoryservice.service_account_credentials_secret_arn', required=True)
    parsed_credentials_dic = json.loads(ds_service_account_credentials)
    username = list(parsed_credentials_dic.keys())[0]
    password = parsed_credentials_dic[username]
    return username, password
