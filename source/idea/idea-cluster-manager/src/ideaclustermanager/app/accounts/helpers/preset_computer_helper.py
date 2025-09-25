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
from ideadatamodel import exceptions, errorcodes, EC2Instance

from ideaclustermanager.app.accounts.db.ad_automation_dao import ADAutomationDAO
from ideaclustermanager.app.accounts.helpers.ad_computer_helper_base import ADComputerHelperBase

from typing import Dict, Optional
import botocore.exceptions
import secrets
import string


class PresetComputeHelper(ADComputerHelperBase):
    """
    Helper to manage creating preset Computer Accounts in AD using adcli.

    Errors:
    * AD_AUTOMATION_PRESET_COMPUTER_FAILED - when the request is bad, invalid or cannot be retried.
    * AD_AUTOMATION_PRESET_COMPUTER_RETRY - when request is valid, but preset-computer operation fails due to intermittent or timing errors.
        operation will be retried based on SQS visibility timeout settings.
    """

    def __init__(self, context: SocaContext, ad_automation_dao: ADAutomationDAO, sender_id: str, request: Dict):
        """
        :param context:
        :param ad_automation_dao:
        :param sender_id: SenderId attribute from SQS Message
        :param request: the original request payload envelope
        """
        self.logger = context.logger('preset-computer')
        super().__init__(context, self.logger, ad_automation_dao, sender_id, request)
        
        self.ec2_instance: Optional[EC2Instance] = None

        # Metadata for AD joins
        self.aws_account = self.context.config().get_string('cluster.aws.account_id', required=True)
        self.cluster_name = self.context.config().get_string('cluster.cluster_name', required=True)
        self.aws_region = self.context.config().get_string('cluster.aws.region', required=True)
        
        self._initialize_preset_data()

    @property
    def log_tag(self) -> str:
        return f'(Host: {self.hostname}, InstanceId: {self.instance_id})'

    def get_retry_error_code(self):
        return errorcodes.AD_AUTOMATION_PRESET_COMPUTER_RETRY

    def get_failed_error_code(self):
        return errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED

    def _initialize_preset_data(self):

        payload = self.request.get("payload", {})

        # SenderId attribute from SQS message to protect against spoofing.
        if not self.sender_id:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message='Unable to verify cluster node identity: SenderId is required'
            )

        # when sent from an EC2 Instance with an IAM Role attached, SenderId is of below format (IAM role ID):
        # AROAZKN2GIY65I74VE5YH:i-035b89c7f49714a3e
        sender_id_tokens = self.sender_id.split(':')
        if len(sender_id_tokens) != 2:
            raise exceptions.soca_exception(
                error_code=errorcodes.AD_AUTOMATION_PRESET_COMPUTER_FAILED,
                message='Unable to verify cluster node identity: Invalid SenderId'
            )

        instance_id = sender_id_tokens[1]
        
        if isinstance(payload, dict) and 'instance_id' in payload:
            instance_id = payload['instance_id']
        
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
        hostname = payload.get("hostname", "")
        if not hostname:
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

        cmd = [
            self.ADCLI,
            'preset-computer',
            f'--domain-controller={domain_controller_ip}',
            f'--login-user={self.service_account_username}',
            '--stdin-password',
            f'--one-time-password={one_time_password}',
            f'--domain={self.ldap_client.options.domain_name}',
            f'--domain-ou={self.get_ldap_computers_base()}',
            '--verbose',
        ]
        if self.use_ldaps:
            cmd.append("--use-ldaps")
        cmd.append(self.hostname)

        preset_computer_result = self._shell.invoke(
            cmd_input=self.service_account_password,
            cmd=cmd,
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
                    'hostname': self.hostname,
                    'status': 'fail',
                    'error_code': e.error_code,
                    'message': e.message,
                    'node_type': self.ec2_instance.soca_node_type,
                    'module_id': self.ec2_instance.idea_module_id
                })

            # raise exception in all cases
            raise e
