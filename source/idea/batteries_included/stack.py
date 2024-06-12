#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from aws_cdk import CfnStack, Stack, aws_ssm
from constructs import Construct

from idea.batteries_included.parameters.parameters import BIParameters


class BiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        template_url: str,
        parameters: BIParameters = BIParameters(),
    ) -> None:
        super().__init__(scope, stack_id)

        self.bi_stack = CfnStack(
            self,
            "RESExternal",
            parameters={
                "PortalDomainName": str(parameters.portal_domain_name),
                "Keypair": str(parameters.ssh_key_pair_name),
                "EnvironmentName": str(parameters.cluster_name),
                "AdminPassword": str(parameters.root_password),
                "ServiceAccountPassword": str(parameters.root_password),
                "ClientIpCidr": str(parameters.client_ip),
                "ClientPrefixList": str(parameters.client_prefix_list),
                "RetainStorageResources": str(parameters.retain_storage_resources),
            },
            template_url=template_url,
        )

        self.vpc_id = aws_ssm.StringParameter(
            self,
            id=str(parameters.vpc_id),
            parameter_name=str(parameters.vpc_id),
            string_value=self.bi_stack.get_att("Outputs.VpcId").to_string(),
        )

        self.vpc_id.node.add_dependency(self.bi_stack)

        self.load_balancer_subnets = aws_ssm.StringListParameter(
            self,
            id=str(parameters.load_balancer_subnets),
            parameter_name=str(parameters.load_balancer_subnets),
            string_list_value=self.bi_stack.get_att("Outputs.PublicSubnets")
            .to_string()
            .split(","),
        )

        self.load_balancer_subnets.node.add_dependency(self.bi_stack)

        self.infrastructure_host_subnets = aws_ssm.StringListParameter(
            self,
            id=str(parameters.infrastructure_host_subnets),
            parameter_name=str(parameters.infrastructure_host_subnets),
            string_list_value=self.bi_stack.get_att("Outputs.PrivateSubnets")
            .to_string()
            .split(","),
        )

        self.infrastructure_host_subnets.node.add_dependency(self.bi_stack)

        self.vdi_subnets = aws_ssm.StringListParameter(
            self,
            id=str(parameters.vdi_subnets),
            parameter_name=str(parameters.vdi_subnets),
            string_list_value=self.bi_stack.get_att("Outputs.PrivateSubnets")
            .to_string()
            .split(","),
        )

        self.vdi_subnets.node.add_dependency(self.bi_stack)

        self.active_directory_name = aws_ssm.StringParameter(
            self,
            id=str(parameters.name),
            parameter_name=str(parameters.name),
            string_value=self.bi_stack.get_att(
                "Outputs.ActiveDirectoryName"
            ).to_string(),
        )

        self.active_directory_name.node.add_dependency(self.bi_stack)

        self.ad_short_name = aws_ssm.StringParameter(
            self,
            id=str(parameters.ad_short_name),
            parameter_name=str(parameters.ad_short_name),
            string_value=self.bi_stack.get_att("Outputs.ADShortName").to_string(),
        )

        self.ad_short_name.node.add_dependency(self.bi_stack)

        self.ldap_base = aws_ssm.StringParameter(
            self,
            id=str(parameters.ldap_base),
            parameter_name=str(parameters.ldap_base),
            string_value=self.bi_stack.get_att("Outputs.LDAPBase").to_string(),
        )

        self.ldap_base.node.add_dependency(self.bi_stack)

        self.ldap_connection_uri = aws_ssm.StringParameter(
            self,
            id=str(parameters.ldap_connection_uri),
            parameter_name=str(parameters.ldap_connection_uri),
            string_value=self.bi_stack.get_att("Outputs.LDAPConnectionURI").to_string(),
        )

        self.ldap_connection_uri.node.add_dependency(self.bi_stack)

        self.acm_certificate_arn_for_web_ui = aws_ssm.StringParameter(
            self,
            id=str(parameters.acm_certificate_arn_for_web_ui),
            parameter_name=str(parameters.acm_certificate_arn_for_web_ui),
            string_value=(
                self.bi_stack.get_att("Outputs.ACMCertificateARNforWebApp").to_string()
                if parameters.portal_domain_name
                else '""'
            ),
        )

        self.acm_certificate_arn_for_web_ui.node.add_dependency(self.bi_stack)

        self.private_key_secret_arn_for_vdi_domain_name = aws_ssm.StringParameter(
            self,
            id=str(parameters.private_key_secret_arn_for_vdi_domain_name),
            parameter_name=str(parameters.private_key_secret_arn_for_vdi_domain_name),
            string_value=(
                self.bi_stack.get_att("Outputs.PrivateKeySecretArn").to_string()
                if parameters.portal_domain_name
                else '""'
            ),
        )

        self.private_key_secret_arn_for_vdi_domain_name.node.add_dependency(
            self.bi_stack
        )

        self.certificate_secret_arn_for_vdi_domain_name = aws_ssm.StringParameter(
            self,
            id=str(parameters.certificate_secret_arn_for_vdi_domain_name),
            parameter_name=str(parameters.certificate_secret_arn_for_vdi_domain_name),
            string_value=(
                self.bi_stack.get_att("Outputs.CertificateSecretArn").to_string()
                if parameters.portal_domain_name
                else '""'
            ),
        )

        self.certificate_secret_arn_for_vdi_domain_name.node.add_dependency(
            self.bi_stack
        )

        self.root_username = aws_ssm.StringParameter(
            self,
            id=str(parameters.root_username),
            parameter_name=str(parameters.root_username),
            string_value=self.bi_stack.get_att(
                "Outputs.ServiceAccountUsername"
            ).to_string(),
        )

        self.root_username.node.add_dependency(self.bi_stack)

        self.root_password_secret_arn = aws_ssm.StringParameter(
            self,
            id=str(parameters.root_password_secret_arn),
            parameter_name=str(parameters.root_password_secret_arn),
            string_value=self.bi_stack.get_att(
                "Outputs.ServiceAccountPasswordSecretArn"
            ).to_string(),
        )

        self.root_password_secret_arn.node.add_dependency(self.bi_stack)

        self.root_user_dn = aws_ssm.StringParameter(
            self,
            id=str(parameters.root_user_dn),
            parameter_name=str(parameters.root_user_dn),
            string_value=self.bi_stack.get_att(
                "Outputs.ServiceAccountUserDN"
            ).to_string(),
        )

        self.root_user_dn.node.add_dependency(self.bi_stack)

        self.users_ou = aws_ssm.StringParameter(
            self,
            id=str(parameters.users_ou),
            parameter_name=str(parameters.users_ou),
            string_value=self.bi_stack.get_att("Outputs.UsersOU").to_string(),
        )

        self.users_ou.node.add_dependency(self.bi_stack)

        self.groups_ou = aws_ssm.StringParameter(
            self,
            id=str(parameters.groups_ou),
            parameter_name=str(parameters.groups_ou),
            string_value=self.bi_stack.get_att("Outputs.GroupsOU").to_string(),
        )

        self.groups_ou.node.add_dependency(self.bi_stack)

        self.sudoers_ou = aws_ssm.StringParameter(
            self,
            id=str(parameters.sudoers_ou),
            parameter_name=str(parameters.sudoers_ou),
            string_value=self.bi_stack.get_att("Outputs.SudoersOU").to_string(),
        )

        self.sudoers_ou.node.add_dependency(self.bi_stack)

        self.sudoers_group_name = aws_ssm.StringParameter(
            self,
            id=str(parameters.sudoers_group_name),
            parameter_name=str(parameters.sudoers_group_name),
            string_value="RESAdministrators",
        )

        self.sudoers_group_name.node.add_dependency(self.bi_stack)

        self.computers_ou = aws_ssm.StringParameter(
            self,
            id=str(parameters.computers_ou),
            parameter_name=str(parameters.computers_ou),
            string_value=self.bi_stack.get_att("Outputs.ComputersOU").to_string(),
        )

        self.computers_ou.node.add_dependency(self.bi_stack)

        self.existing_home_fs_id = aws_ssm.StringParameter(
            self,
            id=str(parameters.existing_home_fs_id),
            parameter_name=str(parameters.existing_home_fs_id),
            string_value=self.bi_stack.get_att(
                "Outputs.SharedHomeFilesystemId"
            ).to_string(),
        )

        self.existing_home_fs_id.node.add_dependency(self.bi_stack)
