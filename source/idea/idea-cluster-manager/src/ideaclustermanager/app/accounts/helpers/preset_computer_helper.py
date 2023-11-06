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
from ideadatamodel import exceptions, errorcodes, EC2Instance

from ideaclustermanager.app.accounts.ldapclient.active_directory_client import ActiveDirectoryClient
from ideaclustermanager.app.accounts.db.ad_automation_dao import ADAutomationDAO

from typing import Dict, List, Optional
import botocore.exceptions
import secrets
import string



class PresetComputeHelper:
    """
    Helper to manage creating preset Computer Accounts in AD using adcli.

    Errors:
    * AD_AUTOMATION_PRESET_COMPUTER_FAILED - when the request is bad, invalid or cannot be retried.
    * AD_AUTOMATION_PRESET_COMPUTER_RETRY - when request is valid, but preset-computer operation fails due to intermittent or timing errors.
        operation will be retried based on SQS visibility timeout settings.
    """

    def __init__(self, context: SocaContext, ldap_client: ActiveDirectoryClient, ad_automation_dao: ADAutomationDAO, sender_id: str, request: Dict):
        """
        :param context:
        :param ldap_client:
        :param ad_automation_dao:
        :param sender_id: SenderId attribute from SQS Message
        :param request: the original request payload envelope
        """
        self.context = context
        self.ldap_client = ldap_client
        self.ad_automation_dao = ad_automation_dao
        self.sender_id = sender_id
        self.request = request

        self.logger = context.logger('preset-computer')

        self.nonce: Optional[str] = None
        self.instance_id: Optional[str] = None
        self.ec2_instance: Optional[EC2Instance] = None
        self.hostname: Optional[str] = None

        # Metadata for AD joins
        self.aws_account = self.context.config().get_string('cluster.aws.account_id', required=True)
        self.cluster_name = self.context.config().get_string('cluster.cluster_name', required=True)
        self.aws_region = self.context.config().get_string('cluster.aws.region', required=True)
        # parse and validate sender_id and request
        payload = Utils.get_value_as_dict('payload', request, {})

        # SenderId attribute from SQS message to protect against spoofing.
        if Utils.is_empty(sender_id):
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message='Unable to verify cluster node identity: SenderId is required'
            )

        # enforce a nonce for an additional layer of protection against spoofing and help tracing
        nonce = Utils.get_value_as_string('nonce', payload)
        if Utils.is_empty(nonce):
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message='nonce is required'
            )
        self.nonce = nonce

        # when sent from an EC2 Instance with an IAM Role attached, SenderId is of below format (IAM role ID):
        # AROAZKN2GIY65I74VE5YH:i-035b89c7f49714a3e
        sender_id_tokens = sender_id.split(':')
        if len(sender_id_tokens) != 2:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message='Unable to verify cluster node identity: Invalid SenderId'
            )

        instance_id = sender_id_tokens[1]
        try:
            ec2_instances = self.context.aws_util().ec2_describe_instances(filters=[
                {
                    'Name': 'instance-id',
                    'Values': [instance_id]
                },
                {
                    'Name': 'instance-state-name',
                    'Values': ['running']
                }
            ])
        except botocore.exceptions.ClientError as e:
            error_code = str(e.response['Error']['Code'])
            if error_code.startswith('InvalidInstanceID'):
                raise exceptions.soca_exception(
                    error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                    message=f'Unable to verify cluster node identity: Invalid InstanceId - {instance_id}'
                )
            else:
                # for all other errors, retry
                raise e

        if len(ec2_instances) == 0:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message=f'Unable to verify cluster node identity: InstanceId = {instance_id} not found'
            )

        self.instance_id = instance_id

        self.ec2_instance = ec2_instances[0]

        # for Windows instances, there is no way to fetch the hostname from describe instances API.
        # request payload from windows instances will contain hostname. eg. EC2AMAZ-6S29U5P
        hostname = Utils.get_value_as_string('hostname', payload)
        if Utils.is_empty(hostname):
            # Generate and make use of an IDEA hostname
            hostname_data = f"{self.aws_region}|{self.aws_account}|{self.cluster_name}|{self.instance_id}"
            hostname_prefix = self.context.config().get_string('directoryservice.ad_automation.hostname_prefix', default='IDEA-')

            # todo - move to constants
            # todo - change this to produce the shake output and take this many chars vs. bytes (hex)
            # check the configured hostname_prefix length and how much it leaves us for generating the random portion.
            avail_chars = (15 - len(hostname_prefix))
            if avail_chars < 4:
                raise exceptions.soca_exception(
                    error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                    message=f'{self.log_tag}configured hostname_prefix is too large. Required at least 4 char of random data. Decrease the size of directoryservice.ad_automation.hostname_prefix: {len(hostname_prefix)}'
                )

            self.logger.info(f'Using hostname information {hostname_data} (configured hostname prefix: [{hostname_prefix}] / len {len(hostname_prefix)} / {avail_chars} chars available for random portion)')
            # Take the last n-chars from the resulting shake256 bucket of 256
            shake_value = Utils.shake_256(hostname_data, 256)[(avail_chars * -1):]
            hostname = f'{hostname_prefix}{shake_value}'.upper()
            self.logger.info(f'Generated IDEA hostname / AD hostname of: {hostname} / len {len(hostname)}')

        self.hostname = hostname
        self.logger.info(f'Using hostname for AD join: {self.hostname}')

        self._shell = ShellInvoker(logger=self.logger)

        # verify if adcli is installed and available on the system.
        which_adcli = self._shell.invoke('command -v adcli', shell=True)
        if which_adcli.returncode != 0:
            raise exceptions.general_exception('unable to locate adcli on system to initialize PresetComputerHelper')
        self.ADCLI = which_adcli.stdout

        # initialize domain controller IP addresses
        self._domain_controller_ips = self.get_domain_controller_ip_addresses()

    @property
    def log_tag(self) -> str:
        return f'(Host: {self.hostname}, InstanceId: {self.instance_id}, Nonce: {self.nonce})'

    def get_ldap_computers_base(self) -> str:
        ou_computers = self.context.config().get_string('directoryservice.computers.ou', required=True)
        if '=' in ou_computers:
            return ou_computers
        return f'ou={ou_computers},ou={self.ldap_client.ad_netbios},{self.ldap_client.ldap_base}'

    @staticmethod
    def get_ldap_computer_filterstr(hostname: str) -> str:
        return f'(&(objectClass=computer)(cn={hostname}))'

    def is_existing_computer_account(self, trace=False) -> bool:
        search_result = self.ldap_client.search_s(
            base=self.get_ldap_computers_base(),
            filterstr=self.get_ldap_computer_filterstr(self.hostname),
            attrlist=['dn'],
            trace=trace
        )
        return len(search_result) > 0

    def get_domain_controller_ip_addresses(self) -> List[str]:
        """
        perform adcli discovery on the AD domain name and return all the domain controller hostnames.
        :return: hostnames all available domain controllers
        """
        result = self._shell.invoke(
            cmd=[
                self.ADCLI,
                'info',
                self.ldap_client.domain_name.upper()
            ]
        )
        if result.returncode != 0:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY,
                message=f'{self.log_tag} failed to perform adcli information discovery on AD domain: {self.ldap_client.domain_name}'
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
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY,
                message=f'{self.log_tag} Unable to validate AD domain discovery for domain-name: {self.ldap_client.domain_name}'
            )

        if domain_name.upper() != self.ldap_client.domain_name.upper():
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY,
                message=f"{self.log_tag} AD domain discovery mismatch for domain-name: Got: {domain_name.upper()} Expected: {self.ldap_client.domain_name.upper()}"
            )

        # domain-short must be present and match our configuration
        domain_shortname = Utils.get_value_as_string('domain-short', domain_query, default=None)
        if domain_shortname is None:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY,
                message=f'{self.log_tag} Unable to validate AD domain discovery for domain shortname: {self.ldap_client.domain_name}'
            )
        if domain_shortname.upper() != self.ldap_client.ad_netbios.upper():
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY,
                message=f'{self.log_tag} AD domain discovery mismatch for shortname: Got: {domain_shortname.upper()} Expected: {self.ldap_client.ad_netbios.upper()}'
            )

        # domain_controllers must be a list of domain controllers
        # split() vs. split(' ') - we don't want empty entries in the list
        # else our len() check would be incorrect
        domain_controllers = domain_query.get('domain-controllers', '').strip().split()
        if len(domain_controllers) == 0:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY,
                message=f'{self.log_tag} no domain controllers found for AD domain: {self.ldap_client.domain_name}. check your firewall settings and verify if traffic is allowed on port 53.'
            )

        return domain_controllers

    def get_any_domain_controller_ip(self) -> str:
        """
        Return the next domain controller in the list as discovered from adcli
        :return: Domain Controller IP Address
        """
        if len(self._domain_controller_ips) == 0:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY,
                message=f'{self.log_tag} all existing AD domain controllers have been tried to create computer account, but failed. request will be retried.'
            )

        # We just take the first remaining domain controller as adcli discovery organizes the list for us
        # .pop(0) should be safe as we just checked for len()
        selected_dc = self._domain_controller_ips.pop(0)
        self.logger.info(f'Selecting AD domain controller for operation: {selected_dc}')

        return selected_dc

    def delete_computer(self, domain_controller_ip: str):
        delete_computer_result = self._shell.invoke(
            cmd_input=self.ldap_client.ldap_root_password,
            cmd=[
                self.ADCLI,
                'delete-computer',
                f'--domain-controller={domain_controller_ip}',
                f'--login-user={self.ldap_client.ldap_root_username}',
                '--stdin-password',
                f'--domain={self.ldap_client.domain_name}',
                f'--domain-realm={self.ldap_client.domain_name.upper()}',
                self.hostname
            ]
        )
        if delete_computer_result.returncode != 0:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message=f'{self.log_tag} failed to delete existing computer account: {delete_computer_result}'
            )

    def preset_computer(self, domain_controller_ip: str) -> str:

        # generate one-time-password. password cannot be more than 120 characters and cannot start with numbers.
        # OTP = <prefix_letter> + 119-characters from letters(mixed case) and digits == 120 chars
        # prefix_letter is always a letter (mixed case) to avoid a digit landing as the first character.
        # Expanding the pool to include printable/punctuation can be considered but would introduce
        # escaping and quoting considerations as it is passed to the shell/adcli.
        one_time_password = secrets.choice(string.ascii_letters)
        one_time_password += ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(119))

        # sanity check to make sure we never create a computer with a weak domain password
        if len(one_time_password) != 120:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message=f'{self.log_tag} Internal error - Failed to generate a strong domain password'
            )

        preset_computer_result = self._shell.invoke(
            cmd_input=self.ldap_client.ldap_root_password,
            cmd=[
                self.ADCLI,
                'preset-computer',
                f'--domain-controller={domain_controller_ip}',
                f'--login-user={self.ldap_client.ldap_root_username}',
                '--stdin-password',
                f'--one-time-password={one_time_password}',
                f'--domain={self.ldap_client.domain_name}',
                f'--domain-ou={self.get_ldap_computers_base()}',
                '--verbose',
                self.hostname
            ],
            skip_error_logging=True
        )

        if preset_computer_result.returncode != 0:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message=f'{self.log_tag} failed to preset-computer. details: {preset_computer_result}'
            )

        # We cannot issue an immediate update as the modify_s aims at the domain
        # and replicaton may have not taken place yet. So this should be queued for an update
        # when the object appears within the AD connection?
        # todo - jobIDs / other info that is useful to the AD admin?
        # should the incoming node provide a description field to cluster-manager?
        # infra nodes wouldn't have a jobID
        #self.ldap_client.update_computer_description(
        #    computer=self.hostname,
        #    description=f'IDEA|{self.cluster_name}|{self.instance_id}'
        #)
        # We cannot include this in the preset-computer or other adcli commands as this
        # is not inlucded in all adcli implementations for our baseOSs. So we manually update LDAP.
        # eg.
        #                # f"--description='IDEA {self.aws_region} / {self.cluster_name} / {self.instance_id}'",

        return one_time_password

    def invoke(self):
        """
        call adcli preset-computer and update the ad-automation dynamodb table with applicable status
        """

        try:

            # fetch a domain controller IP to "pin" all adcli operations to ensure we don't run into synchronization problems
            domain_controller_ip = self.get_any_domain_controller_ip()

            if self.is_existing_computer_account():
                # if computer already exists in AD
                # it is likely the case where the private IP is being reused in the VPC where an old cluster node was deleted without removing entry from AD.
                # delete and create preset-computer
                self.logger.warning(f'{self.log_tag} found existing computer account. deleting using DC: {domain_controller_ip} ...')
                self.delete_computer(domain_controller_ip=domain_controller_ip)

            self.logger.info(f'{self.log_tag} creating new computer account using DC: {domain_controller_ip} ...')

            try:
                one_time_password = self.preset_computer(domain_controller_ip=domain_controller_ip)
            except exceptions.SocaException as e:
                if e.error_code == errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED:
                    # ad is finicky. returns below error even for valid request:
                    #  ! Cannot set computer password: Authentication error
                    if 'Cannot set computer password: Authentication error' in e.message:
                        self.delete_computer(domain_controller_ip=domain_controller_ip)
                        return self.invoke()
                    else:
                        # if failed due to some other reason, re-raise as a retry exception
                        raise exceptions.soca_exception(
                            error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY,
                            message=e.message
                        )
                else:
                    raise e

            self.ad_automation_dao.create_ad_automation_entry(entry={
                'instance_id': self.instance_id,
                'nonce': self.nonce,
                'hostname': self.hostname,
                'otp': one_time_password,
                'domain_controller': domain_controller_ip,
                'node_type': self.ec2_instance.soca_node_type,
                'module_id': self.ec2_instance.idea_module_id,
                'status': 'success'
            })

            self.logger.info(f'{self.log_tag} computer account created successfully.')
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED:
                # add feedback entry for the host indicating failure status, and stop polling ddb
                self.ad_automation_dao.create_ad_automation_entry(entry={
                    'instance_id': self.instance_id,
                    'nonce': self.nonce,
                    'hostname': self.hostname,
                    'status': 'fail',
                    'error_code': e.error_code,
                    'message': e.message,
                    'node_type': self.ec2_instance.soca_node_type,
                    'module_id': self.ec2_instance.idea_module_id
                })

            # raise exception in all cases
            raise e
