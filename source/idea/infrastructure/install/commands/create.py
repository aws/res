#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Union

import aws_cdk

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.customdomain import CustomDomainKey
from idea.infrastructure.install.parameters.directoryservice import DirectoryServiceKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.parameters.shared_storage import SharedStorageKey

VALUES_FILE_PATH = "values.yml"
EXE = "res-admin"


class Create:
    """
    Using supplied parameters, this generates commands for installing an environment
    automagically
    """

    def __init__(self, params: Union[RESParameters, BIParameters]):
        self.params = params

    def get_commands(self) -> list[str]:
        return [
            f"{EXE} --version",
            f"{EXE} config show {self._get_suffix()}",
            *self._config(),
            *self._bootstrap(),
            *self._deploy(),
        ]

    def _config(self) -> list[str]:
        """
        Commands for generating config for an environment

        1. Generate values.yml using parameters
        2. Render settings files from generated values.yml
        3. Write rendered settings to dynamo
        4. Update the dynamo settings table for infrastructure host AMIs, AD, and custom domain
        5. Remove the local copy of config, and replace with what's in dynamo
        """
        return [
            *self._create_values_file(),
            *self._render_settings_from_values_and_write_to_dynamo(),
            *self._update_infrastructure_host_ami_config(),
            *self._update_directory_service_config(),
            *self._update_custom_domain_config(),
            f"rm -rf /root/.idea/clusters/{self.params.get_str(CommonKey.CLUSTER_NAME)}/{aws_cdk.Aws.REGION}/config",
            f"{EXE} config export {self._get_suffix()}",
        ]

    def _bootstrap(self) -> list[str]:
        """
        Bootstrap the environment

        This creates a bucket and the bootstrap stack
        """
        return [f"{EXE} bootstrap {self._get_suffix()}"]

    def _deploy(self) -> list[str]:
        """
        Deploy the environment

        Using the local configuration (downloaded from dynamo earlier), deploy
        the environment
        """
        return [f"{EXE} deploy all {self._get_suffix()}"]

    def _get_suffix(self) -> str:
        return f"--cluster-name {self.params.get_str(CommonKey.CLUSTER_NAME)} --aws-region {aws_cdk.Aws.REGION}"

    def _render_settings_from_values_and_write_to_dynamo(self) -> list[str]:
        return [
            f"{EXE} config generate --values-file {VALUES_FILE_PATH} --force --existing-resources --regenerate",
            f"{EXE} config update --overwrite --force {self._get_suffix()}",
        ]

    def _update_infrastructure_host_ami_config(self) -> list[str]:
        """
        Generate commands to update each of the settings for the custom infrastructure host amis
        """

        # Construct none_null to check none of the custom values are null
        vals = ""
        nvals = len(self._get_infrastructure_host_ami_settings().keys())
        for key, value in self._get_infrastructure_host_ami_settings().items():
            vals += f" {value} "
        quote = r'"'
        vals = f"{quote} {vals} {quote}"

        # Update only if none of the custom values are null
        config_update_commands: list[str] = []
        for key, value in self._get_infrastructure_host_ami_settings().items():
            cmd = f" if [ $(echo {vals}|wc -w) -eq {nvals} ] ; then "
            cmd += f" {EXE} config set Key={key},Type=str,Value={value} --force {self._get_suffix()}; fi"
            config_update_commands.append(cmd)

        return config_update_commands

    def _update_custom_domain_config(self) -> list[str]:
        """
        Generate commands to update each of the settings for custom dmain
        """

        # Construct none_null to check none of the custom values are null
        vals = ""
        nvals = len(self._get_custom_domain_settings().keys())
        for key, value in self._get_custom_domain_settings().items():
            vals += f" {value} "
        quote = r'"'
        vals = f"{quote} {vals} {quote}"

        # Update only if none of the custom values are null
        config_update_commands: list[str] = []
        for key, value in self._get_custom_domain_settings().items():
            cmd = f" if [ $(echo {vals}|wc -w) -eq {nvals} ] ; then "
            cmd += f" {EXE} config set Key={key},Type=str,Value={value} --force {self._get_suffix()}; fi"
            config_update_commands.append(cmd)

        # set these 2 values to true only if none_null is true
        for key in [
            "cluster.load_balancers.external_alb.certificates.provided",
            "vdc.dcv_connection_gateway.certificate.provided",
        ]:
            cmd = f" if [ $(echo {vals}|wc -w) -eq {nvals} ] ; then "
            cmd += f" {EXE} config set Key={key},Type=str,Value=true --force {self._get_suffix()};"
            cmd += " else "
            cmd += f" {EXE} config set Key={key},Type=str,Value=false --force {self._get_suffix()};"
            cmd += "fi "
            config_update_commands.append(cmd)

        return config_update_commands

    def _update_directory_service_config(self) -> list[str]:
        """
        Generate commands to update each of the settings for directoryservice
        """
        config_update_commands = []
        for key, value in self._get_directory_service_settings().items():
            # Only tls_certificate_secret_arn is optional. Update only if value present.
            if key == "directoryservice.tls_certificate_secret_arn":
                cmd = f'if [ -n "{value}" ]; then'
                cmd += f" {EXE} config set Key={key},Type={type(value).__name__},Value={value} --force {self._get_suffix()};"
                cmd += "fi "
                config_update_commands.append(cmd)
                continue

            config_update_commands.append(
                f"{EXE} config set Key={key},Type={type(value).__name__},Value='{value}' --force {self._get_suffix()}"
            )
        config_update_commands.append(
            f"{EXE} config set Key=directoryservice.root_credentials_provided,Type=bool,Value=True --force {self._get_suffix()}"
        )
        return config_update_commands

    def _get_infrastructure_host_ami_settings(self) -> dict[str, Any]:
        """
        Returns a mapping of RES settings key to parameters for updating the infrastructure host ami config
        """
        return {
            "vdc.dcv_broker.autoscaling.instance_ami": self.params.get_str(
                CommonKey.INFRASTRUCTURE_HOST_AMI
            ),
            "vdc.dcv_connection_gateway.autoscaling.instance_ami": self.params.get_str(
                CommonKey.INFRASTRUCTURE_HOST_AMI
            ),
            "bastion-host.instance_ami": self.params.get_str(
                CommonKey.INFRASTRUCTURE_HOST_AMI
            ),
            "vdc.controller.autoscaling.instance_ami": self.params.get_str(
                CommonKey.INFRASTRUCTURE_HOST_AMI
            ),
            "cluster-manager.ec2.autoscaling.instance_ami": self.params.get_str(
                CommonKey.INFRASTRUCTURE_HOST_AMI
            ),
        }

    def _get_directory_service_settings(self) -> dict[str, Any]:
        """
        Returns a mapping of RES settings key to parameters for updating the directoryservice config
        """
        return {
            "directoryservice.name": self.params.get_str(DirectoryServiceKey.NAME),
            "directoryservice.ldap_base": self.params.get_str(
                DirectoryServiceKey.LDAP_BASE
            ),
            "directoryservice.root_username_secret_arn": self.params.root_username_secret_arn,
            "directoryservice.root_password_secret_arn": self.params.get_str(
                DirectoryServiceKey.ROOT_PASSWORD_SECRET_ARN
            ),
            "directoryservice.ad_short_name": self.params.get_str(
                DirectoryServiceKey.AD_SHORT_NAME
            ),
            "directoryservice.ldap_connection_uri": self.params.get_str(
                DirectoryServiceKey.LDAP_CONNECTION_URI
            ),
            "directoryservice.users.ou": self.params.get_str(
                DirectoryServiceKey.USERS_OU
            ),
            "directoryservice.groups.ou": self.params.get_str(
                DirectoryServiceKey.GROUPS_OU
            ),
            "directoryservice.computers.ou": self.params.get_str(
                DirectoryServiceKey.COMPUTERS_OU
            ),
            "directoryservice.sudoers.ou": self.params.get_str(
                DirectoryServiceKey.SUDOERS_OU
            ),
            "directoryservice.sudoers.group_name": self.params.get_str(
                DirectoryServiceKey.SUDOERS_GROUP_NAME
            ),
            "directoryservice.tls_certificate_secret_arn": self.params.get_str(
                DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN
            ),
            "directoryservice.sssd.ldap_id_mapping": self.params.get_str(
                DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING
            ),
            "directoryservice.disable_ad_join": self.params.get_str(
                DirectoryServiceKey.DISABLE_AD_JOIN
            ),
            "directoryservice.root_user_dn_secret_arn": self.params.root_user_dn_secret_arn,
        }

    def _get_custom_domain_settings(self) -> dict[str, Any]:
        """
        Returns a mapping of RES settings key to parameters for updating the custom domain config
        """
        return {
            "cluster.load_balancers.external_alb.certificates.custom_dns_name": self.params.get_str(
                CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_WEB_APP
            ),
            "cluster.load_balancers.external_alb.certificates.acm_certificate_arn": self.params.get_str(
                CustomDomainKey.ACM_CERTIFICATE_ARN_FOR_WEB_APP
            ),
            "vdc.dcv_connection_gateway.certificate.custom_dns_name": self.params.get_str(
                CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_VDI
            ),
            "vdc.dcv_connection_gateway.certificate.certificate_secret_arn": self.params.get_str(
                CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI
            ),
            "vdc.dcv_connection_gateway.certificate.private_key_secret_arn": self.params.get_str(
                CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI
            ),
        }

    def _create_values_file(self) -> list[str]:
        """
        Generates the values file using specified parameters
        """
        return [
            f"""cat <<EOF > {VALUES_FILE_PATH}
_regenerate: false
aws_partition: {aws_cdk.Aws.PARTITION}
aws_region: {aws_cdk.Aws.REGION}
aws_account_id: '{aws_cdk.Aws.ACCOUNT_ID}'
aws_dns_suffix: {aws_cdk.Aws.URL_SUFFIX}
cluster_name: {self.params.get_str(CommonKey.CLUSTER_NAME)}
administrator_email: {self.params.get_str(CommonKey.ADMIN_EMAIL)}
ssh_key_pair_name: {self.params.get_str(CommonKey.SSH_KEY_PAIR)}
client_ip:
- {self.params.get_str(CommonKey.CLIENT_IP)}
prefix_list_ids:
- {self.params.get_str(CommonKey.CLIENT_PREFIX_LIST)}
permission_boundary_arn: {self.params.get_str(CommonKey.IAM_PERMISSION_BOUNDARY)}
alb_public: {self.params.get_str(CommonKey.IS_LOAD_BALANCER_INTERNET_FACING)}
use_vpc_endpoints: true
directory_service_provider: activedirectory
enable_aws_backup: false
kms_key_type: aws-managed
use_existing_vpc: true
storage_home_provider: efs
use_existing_home_fs: true
existing_home_fs_id: {self.params.get_str(SharedStorageKey.SHARED_HOME_FILESYSTEM_ID)}
vpc_id: {self.params.get_str(CommonKey.VPC_ID)}
existing_resources:
- subnets:public
- subnets:private
- subnets:external_load_balancer
- subnets:infrastructure_hosts
- subnets:dcv_session
- shared-storage:home
load_balancer_subnet_ids:
$(echo "{
        self.params.load_balancer_subnets_string
}" | tr -d '" ' | tr ',' '\n' | sed 's/^/- /')
infrastructure_host_subnet_ids:
$(echo "{
    self.params.infrastructure_host_subnets_string
}" | tr -d '" ' | tr ',' '\n' | sed 's/^/- /')
dcv_session_private_subnet_ids:
$(echo "{
    self.params.dcv_session_private_subnets_string
}" | tr -d '" ' | tr ',' '\n' | sed 's/^/- /')
enabled_modules:
- virtual-desktop-controller
$(echo {self.params.get_str(CommonKey.IS_LOAD_BALANCER_INTERNET_FACING)}- bastion-host | grep true | sed 's:true::')
metrics_provider: cloudwatch
base_os: amazonlinux2
instance_type: m5.large
volume_size: '200'
EOF"""
        ]
