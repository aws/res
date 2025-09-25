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
from ideasdk.utils import Utils
from ideasdk.shell import ShellInvoker
from ideadatamodel import exceptions
from logging import Logger

from res.clients.ldap_client.active_directory_client import ActiveDirectoryClient
from ideaclustermanager.app.accounts.db.ad_automation_dao import ADAutomationDAO

from typing import Dict, List, Optional
from abc import ABC, abstractmethod


class ADComputerHelperBase(ABC):
    """
    Base class for AD computer account management helpers.
    Contains common functionality moved from both preset and delete helpers.
    """

    def __init__(self, context: SocaContext, logger: Logger , ad_automation_dao: ADAutomationDAO, sender_id: str, request: Dict):
        self.context = context
        self.logger = logger
        self.ldap_client = ActiveDirectoryClient(self.context.logger())
        self.service_account_username, self.service_account_password = (
            self.ldap_client.fetch_service_account_credentials()
        )
        self.ad_automation_dao = ad_automation_dao
        self.sender_id = sender_id
        self.request = request

        self.instance_id: Optional[str] = None
        self.hostname: Optional[str] = None

        self._shell = ShellInvoker(logger=self.logger)

        # verify if adcli is installed and available on the system.
        which_adcli = self._shell.invoke('command -v adcli', shell=True)
        if which_adcli.returncode != 0:
            raise exceptions.general_exception('unable to locate adcli on system')
        self.ADCLI = which_adcli.stdout

        # Currently adcli uses the GSSAPI SASL mechanism for LDAP authentication and to establish encryption.
        # This should satisfy all requirements set on the server side and LDAPS should only be used if the LDAP
        # port is not accessible due to firewalls or other reasons. Note that connection to the domain controller
        # with LDAPS requires the latest version of adcli (>=0.9.1), which is not available in the Amazon Linux Core x86_64 repo.
        # Only uncomment the lines below to force the LDAPS connection if required:
        # ldap_connection_uri = self.context.config().get_string('directoryservice.ldap_connection_uri', required=True)
        # self.use_ldaps = ldap_connection_uri.startswith('ldaps:')

        self.use_ldaps = False

        # initialize domain controller IP addresses
        self._domain_controller_ips = self.get_domain_controller_ip_addresses()

    @property
    def log_tag(self) -> str:
        return f'(Host: {self.hostname}, InstanceId: {self.instance_id})'

    @staticmethod
    def get_ldap_computer_filterstr(hostname: str) -> str:
        return f'(&(objectClass=computer)(cn={hostname}))'

    def get_ldap_computers_base(self) -> str:
        ou_computers = self.context.config().get_string('directoryservice.computers.ou', required=True)
        if '=' in ou_computers:
            return ou_computers
        return f'ou={ou_computers},ou={self.ldap_client.options.ldap_base}'


    def is_existing_computer_account(self, trace=False) -> bool:
        search_result = self.ldap_client.search_s(
            base=self.get_ldap_computers_base(),
            filterstr=self.get_ldap_computer_filterstr(self.hostname),
            attrlist=['dn'],
            trace=trace,
        )
        return len(search_result) > 0

    def get_domain_controller_ip_addresses(self) -> List[str]:
        """
        perform adcli discovery on the AD domain name and return all the domain controller hostnames.
        :return: hostnames all available domain controllers
        """
        cmd = [
            self.ADCLI,
            'info',
        ]
        if self.use_ldaps:
            cmd.append("--use-ldaps")
        cmd.append(self.ldap_client.options.domain_name.upper())

        result = self._shell.invoke(
            cmd=cmd,
        )
        if result.returncode != 0:
            raise exceptions.soca_exception(
                error_code=self.get_retry_error_code(),
                message=f'{self.log_tag} failed to perform adcli information discovery on AD domain: {self.ldap_client.options.domain_name}'
            )

        # self.logger.debug(f'ADCLI Domain info: {result.stdout}')
        # Example output for a domain with 6 domain controllers:
        # [domain]
        # domain-name = idea.local
        # domain-short = IDEA
        # domain-forest = idea.local
        # domain-controller = IP-C6130254.idea.local
        # domain-controller-site = us-east-1
        # domain-controller-flags = gc ldap ds kdc timeserv closest writable full-secret ads-web
        # domain-controller-usable = yes
        # domain-controllers = IP-C6130254.idea.local IP-C6120243.idea.local ip-c61301a7.idea.local ip-c61202c6.idea.local ip-c6120053.idea.local ip-c612008c.idea.local
        # [computer]
        # computer-site = us-east-1

        # store the output in domain_query for quick review of params
        domain_query = {}
        lines = str(result.stdout).splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith('['):
                continue
            try:
                result_key = line.split(' =')[0]
                result_value = line.split('= ')[1]
            except IndexError as e:
                self.logger.warning(f'Error parsing AD discovery output: {e}.  Line skipped: {line}')
                continue

            self.logger.debug(f'Key: [{result_key:25}]   Value: [{result_value:25}]')

            if (
                not Utils.get_as_string(result_key, default='') or
                not Utils.get_as_string(result_value, default='')
            ):
                self.logger.warning(f'Error parsing AD discovery output. Unable to parse Key/Value Pair. Check adcli version/output. Line skipped: {line}')
                continue

            # Save for later
            domain_query[result_key] = result_value

        # Sanity check our query results
        # todo - should domain-controller-flags be evaluated for writeable or other health flags?

        # domain-name must be present and match our configuration
        domain_name = Utils.get_value_as_string('domain-name', domain_query, default=None)
        if domain_name is None:
            raise exceptions.soca_exception(
                error_code=self.get_retry_error_code(),
                message=f'{self.log_tag} Unable to validate AD domain discovery for domain-name: {self.ldap_client.options.domain_name}'
            )

        if domain_name.upper() != self.ldap_client.options.domain_name.upper():
            raise exceptions.soca_exception(
                error_code=self.get_retry_error_code(),
                message=f"{self.log_tag} AD domain discovery mismatch for domain-name: Got: {domain_name.upper()} Expected: {self.ldap_client.options.domain_name.upper()}"
            )

        # domain_controllers must be a list of domain controllers
        # split() vs. split(' ') - we don't want empty entries in the list
        # else our len() check would be incorrect
        domain_controllers = domain_query.get('domain-controllers', '').strip().split()
        if len(domain_controllers) == 0:
            raise exceptions.soca_exception(
                error_code=self.get_retry_error_code(),
                message=f'{self.log_tag} no domain controllers found for AD domain: {self.ldap_client.options.domain_name}. check your firewall settings and verify if traffic is allowed on port 53.'
            )

        return domain_controllers

    def get_any_domain_controller_ip(self) -> str:
        """
        Return the next domain controller in the list as discovered from adcli
        :return: Domain Controller IP Address
        """
        if len(self._domain_controller_ips) == 0:
            raise exceptions.soca_exception(
                error_code=self.get_retry_error_code(),
                message=f'{self.log_tag} all existing AD domain controllers have been tried to create computer account, but failed. request will be retried.'
            )

        # We just take the first remaining domain controller as adcli discovery organizes the list for us
        # .pop(0) should be safe as we just checked for len()
        selected_dc = self._domain_controller_ips.pop(0)
        self.logger.info(f'Selecting AD domain controller for operation: {selected_dc}')

        return selected_dc

    def delete_computer(self, domain_controller_ip: str):
        cmd = [
            self.ADCLI,
            'delete-computer',
            f'--domain-controller={domain_controller_ip}',
            f'--login-user={self.service_account_username}',
            '--stdin-password',
            f'--domain={self.ldap_client.options.domain_name}',
            f'--domain-realm={self.ldap_client.options.domain_name.upper()}',
        ]
        if self.use_ldaps:
            cmd.append("--use-ldaps")
        cmd.append(self.hostname)

        delete_computer_result = self._shell.invoke(
            cmd_input=self.service_account_password,
            cmd=cmd,
        )
        if delete_computer_result.returncode != 0:
            raise exceptions.soca_exception(
                error_code=self.get_failed_error_code(),
                message=f'{self.log_tag} failed to delete existing computer account: {delete_computer_result}'
            )

    @abstractmethod
    def get_retry_error_code(self): ...

    @abstractmethod
    def get_failed_error_code(self): ...

    @abstractmethod
    def invoke(self): ...
