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

__all__ = (
    'ElasticIP',
    'Vpc',
    'SecurityGroup',
    'BastionHostSecurityGroup',
    'ExternalLoadBalancerSecurityGroup',
    'InternalLoadBalancerSecurityGroup',
    'SharedStorageSecurityGroup',
    'OpenLDAPServerSecurityGroup',
    'WebPortalSecurityGroup',
    'SchedulerSecurityGroup',
    'ComputeNodeSecurityGroup',
    'VpcEndpointSecurityGroup',
    'VpcGatewayEndpoint',
    'VpcInterfaceEndpoint',
    'DefaultClusterSecurityGroup',
    'VirtualDesktopPublicLoadBalancerAccessSecurityGroup',
    'VirtualDesktopBastionAccessSecurityGroup',
    'VirtualDesktopCustomCredentialBrokerSecurityGroup',
)

from typing import List, Optional, Dict

import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_iam as iam
)

from ideaadministrator.app.cdk.constructs import (
    SocaBaseConstruct,
    CreateTagsCustomResource,
    IdeaNagSuppression
)
from ideaadministrator.app_context import AdministratorContext
from ideadatamodel import constants
from ideasdk.utils import Utils


class ElasticIP(SocaBaseConstruct, ec2.CfnEIP):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct):
        self.context = context
        super().__init__(context, name, scope)


class Vpc(SocaBaseConstruct, ec2.Vpc):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct):
        self.context = context
        self.scope = scope
        super().__init__(context, name, scope,
                         cidr=context.config().get_string('cluster.network.vpc_cidr_block'),
                         nat_gateways=context.config().get_int('cluster.network.nat_gateways'),
                         enable_dns_support=True,
                         enable_dns_hostnames=True,
                         max_azs=context.config().get_int('cluster.network.max_azs'),
                         subnet_configuration=self.build_subnet_configuration(),
                         flow_logs=self.build_flow_logs())

    def build_flow_logs(self) -> Optional[Dict[str, ec2.FlowLogOptions]]:
        vpc_flow_logs = self.context.config().get_bool('cluster.network.vpc_flow_logs', False)
        if not vpc_flow_logs:
            return None

        vpc_flow_logs_removal_policy = self.context.config().get_string('cluster.network.vpc_flow_logs_removal_policy', 'DESTROY')
        log_group_name = self.context.config().get_string('cluster.network.vpc_flow_logs_group_name', f'{self.cluster_name}-vpc-flow-logs')
        log_group = logs.LogGroup(self.scope, 'vpc-flow-logs-group',
                                  log_group_name=log_group_name,
                                  removal_policy=cdk.RemovalPolicy(vpc_flow_logs_removal_policy))
        iam_role = iam.Role(self.scope, 'vpc-flow-logs-role',
                            assumed_by=self.build_service_principal('vpc-flow-logs'),
                            description=f'IAM Role for VPC Flow Logs, Cluster: {self.cluster_name}',
                            role_name=f'{self.cluster_name}-vpc-flow-logs-{self.context.aws().aws_region()}')
        return {
            'cloud-watch': ec2.FlowLogOptions(
                destination=ec2.FlowLogDestination.to_cloud_watch_logs(
                    log_group=log_group,
                    iam_role=iam_role
                ),
                traffic_type=ec2.FlowLogTrafficType.ALL
            )
        }

    @property
    def nat_gateway_ips(self) -> List[constructs.IConstruct]:
        result = []
        if self.public_subnets is None:
            return result
        for subnet in self.public_subnets:
            eip = subnet.node.try_find_child('EIP')
            if eip is None:
                continue
            result.append(eip)
        return result

    def build_subnet_configuration(self) -> List[ec2.SubnetConfiguration]:
        result = []
        # a public subnet always is required to support cognito access as Cognito does support VPC endpoints.
        public_subnet_config = self.build_public_subnet_config()
        result.append(public_subnet_config)

        # private can be optional
        private_subnet_config = self.build_private_subnet_config()
        if private_subnet_config is not None:
            result.append(private_subnet_config)

        # isolated can be optional
        isolated_subnet_config = self.build_isolated_subnet_config()
        if isolated_subnet_config is not None:
            result.append(isolated_subnet_config)

        return result

    def build_public_subnet_config(self) -> ec2.SubnetConfiguration:
        cidr_mask = self.context.config().get_int('cluster.network.subnet_config.public.cidr_mask', 26)
        return ec2.SubnetConfiguration(
            name='public',
            cidr_mask=cidr_mask,
            subnet_type=ec2.SubnetType.PUBLIC
        )

    def build_private_subnet_config(self) -> Optional[ec2.SubnetConfiguration]:
        cidr_mask = self.context.config().get_int('cluster.network.subnet_config.private.cidr_mask', 18)
        return ec2.SubnetConfiguration(
            name='private',
            cidr_mask=cidr_mask,
            subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
        )

    def build_isolated_subnet_config(self) -> Optional[ec2.SubnetConfiguration]:
        """
        build isolated subnet only if subnet config is provided.
        do not return any default value.
        :return: isolated subnet configuration
        """

        cidr_mask = self.context.config().get_int('cluster.network.subnet_config.isolated.cidr_mask', None)
        if cidr_mask is None:
            return None

        return ec2.SubnetConfiguration(
            name='isolated',
            cidr_mask=cidr_mask,
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
        )

    @property
    def public_subnet_ids(self) -> List[str]:
        result = []
        for subnet in self.public_subnets:
            result.append(subnet.subnet_id)
        return result

    @property
    def private_subnet_ids(self) -> List[str]:
        result = []
        for subnet in self.private_subnets:
            result.append(subnet.subnet_id)
        return result


class SecurityGroup(SocaBaseConstruct, ec2.SecurityGroup):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc,
                 allow_all_outbound=False,
                 description=Optional[str],
                 retain_on_delete=False):
        self.context = context
        super().__init__(context, name, scope,
                         security_group_name=self.build_resource_name(name),
                         vpc=vpc,
                         allow_all_outbound=allow_all_outbound,
                         description=description)
        self.vpc = vpc
        self.add_nag_suppression(suppressions=[])
        if retain_on_delete:
            self.add_retain_on_delete()

    def add_nag_suppression(self, suppressions: List[IdeaNagSuppression], construct: constructs.IConstruct = None, apply_to_children: bool = True):
        updated_suppressions = [
            # [Warning at /idea-test1-cluster/external-load-balancer-security-group/Resource] CdkNagValidationFailure: 'AwsSolutions-EC23' threw an error during validation. This is generally caused by a parameter referencing an intrinsic function. For more details enable verbose logging.'
            IdeaNagSuppression(rule_id='AwsSolutions-EC23', reason='suppress warning: parameter referencing intrinsic function')
        ]
        if suppressions:
            updated_suppressions += suppressions
        super().add_nag_suppression(updated_suppressions, construct, apply_to_children)

    def add_outbound_traffic_rule(self):
        self.add_egress_rule(
            ec2.Peer.ipv4('0.0.0.0/0'),
            ec2.Port.tcp_range(0, 65535),
            description='Allow all egress for TCP'
        )

    def add_api_ingress_rule(self):
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(8443),
            description='Allow HTTP traffic from all VPC nodes for API access'
        )

    def add_loadbalancer_ingress_rule(self, loadbalancer_security_group: ec2.ISecurityGroup):
        self.add_ingress_rule(
            loadbalancer_security_group,
            ec2.Port.tcp(8443),
            description='Allow HTTPs traffic from Load Balancer'
        )

    def add_bastion_host_ingress_rule(self, bastion_host_security_group: ec2.ISecurityGroup):
        self.add_ingress_rule(
            bastion_host_security_group,
            ec2.Port.tcp(22),
            description='Allow SSH from Bastion Host')

    def add_active_directory_rules(self):
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.udp_range(0, 1024),
            description='Allow UDP Traffic from VPC. Required for Directory Service'
        )
        self.add_egress_rule(
            ec2.Peer.ipv4('0.0.0.0/0'),
            ec2.Port.udp_range(0, 1024),
            description='Allow UDP Traffic. Required for Directory Service'
        )


class BastionHostSecurityGroup(SecurityGroup):
    """
    Security Group for Bastion Host
    Only instance that will be in Public Subnet. All other instances will be launched in private subnets.
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct, vpc: ec2.IVpc, cluster_prefix_list_id: str):
        super().__init__(context, name, scope, vpc, description='Bastion host security group')
        self.cluster_prefix_list_id = cluster_prefix_list_id
        self.setup_ingress()
        self.setup_egress()

        if self.is_ds_activedirectory():
            self.add_active_directory_rules()

    def setup_ingress(self):
        cluster_prefix_list = ec2.Peer.prefix_list(self.cluster_prefix_list_id)
        self.add_ingress_rule(
            cluster_prefix_list,
            ec2.Port.tcp(22),
            description='Allow SSH access from Cluster Prefix List to Bastion Host'
        )

        prefix_list_ids = [i for i in self.context.config().get_list('cluster.network.prefix_list_ids', default=[]) if i is not None]
        if Utils.is_not_empty(prefix_list_ids):
            for prefix_list_id in prefix_list_ids:
                prefix_list = ec2.Peer.prefix_list(prefix_list_id)
                self.add_ingress_rule(
                    prefix_list,
                    ec2.Port.tcp(22),
                    description='Allow SSH access from Prefix List to Bastion Host'
                )

        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(22),
            description='Allow SSH traffic from all VPC nodes'
        )

    def setup_egress(self):
        self.add_outbound_traffic_rule()


class ExternalLoadBalancerSecurityGroup(SecurityGroup):
    """
    External Load Balancer Security Group
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct, vpc: ec2.IVpc,
                 cluster_prefix_list_id: str,
                 bastion_host_security_group: ec2.ISecurityGroup):
        super().__init__(context, name, scope, vpc, description='External Application Load Balancer security group')
        self.cluster_prefix_list_id = cluster_prefix_list_id
        self.bastion_host_security_group = bastion_host_security_group
        self.setup_ingress()
        self.setup_egress()

    def add_peer_ingress_rule(self, peer: ec2.IPeer, peer_type: str):
        self.add_ingress_rule(
            peer,
            ec2.Port.tcp(443),
            description=f'Allow HTTPS access from {peer_type} to ALB'
        )

        self.add_ingress_rule(
            peer,
            ec2.Port.tcp(80),
            description=f'Allow HTTP access from {peer_type} to ALB'
        )

    def setup_ingress(self):
        cluster_prefix_list = ec2.Peer.prefix_list(self.cluster_prefix_list_id)
        self.add_peer_ingress_rule(cluster_prefix_list, 'Cluster Prefix List')

        prefix_list_ids = [i for i in self.context.config().get_list('cluster.network.prefix_list_ids', default=[]) if i is not None]
        if Utils.is_not_empty(prefix_list_ids):
            for prefix_list_id in prefix_list_ids:
                if Utils.is_not_empty(prefix_list_id):
                    prefix_list = ec2.Peer.prefix_list(prefix_list_id)
                    self.add_peer_ingress_rule(prefix_list, 'Prefix List')

        self.add_ingress_rule(
            self.bastion_host_security_group,
            ec2.Port.tcp(80),
            description='Allow HTTP from Bastion Host')

        self.add_ingress_rule(
            self.bastion_host_security_group,
            ec2.Port.tcp(443),
            description='Allow HTTPs from Bastion Host')

    def setup_egress(self):
        self.add_outbound_traffic_rule()

    def add_nat_gateway_ips_ingress_rule(self, nat_gateway_ips: List[constructs.IConstruct]):
        # allow NAT EIP to communicate with ALB. This so that virtual desktop instances or instances
        # in private subnets can open the Web Portal or Access the APIs using the ALB endpoint
        for eip in nat_gateway_ips:
            self.add_ingress_rule(
                ec2.Peer.ipv4(f'{eip.ref}/32'),
                ec2.Port.tcp(443),
                description='Allow NAT EIP to communicate to ALB.'
            )


class SharedStorageSecurityGroup(SecurityGroup):
    """
    Shared Storage Security Group
    Attached to EFS and FSx File Systems. Access is open to all nodes from VPC.

    Note for Lustre rules:
    Although Lustre is optional and may not be used for /internal or /home,
    compute nodes can mount FSx Lustre on-demand to /scratch. For this reason, Lustre rules are provisioned during cluster creation.
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct, vpc: ec2.IVpc):
        super().__init__(context, name, scope, vpc, description='Shared Storage security group for EFS/FSx file systems', retain_on_delete=True)
        self.setup_ingress()
        self.setup_egress()

    def setup_ingress(self):
        # NFS
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(2049),
            description='Allow NFS traffic from all VPC nodes to EFS')

        # FSx for Lustre
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(988),
            description='Allow FSx Lustre traffic from all VPC nodes')
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp_range(1021, 1023),
            description='Allow FSx Lustre traffic from all VPC nodes')

    def setup_egress(self):
        self.add_outbound_traffic_rule()


class OpenLDAPServerSecurityGroup(SecurityGroup):
    """
    OpenLDAP Server Security Group
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc,
                 bastion_host_security_group: ec2.ISecurityGroup):
        super().__init__(context, name, scope, vpc, description='OpenLDAP server security group')
        self.bastion_host_security_group = bastion_host_security_group
        self.setup_ingress()
        self.setup_egress()

    def setup_ingress(self):
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(389),
            description='Allow LDAP traffic from all VPC nodes'
        )
        self.add_api_ingress_rule()
        self.add_bastion_host_ingress_rule(self.bastion_host_security_group)

    def setup_egress(self):
        self.add_outbound_traffic_rule()


class WebPortalSecurityGroup(SecurityGroup):
    """
    Cluster Manager Security Group
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc,
                 bastion_host_security_group: ec2.ISecurityGroup,
                 loadbalancer_security_group: ec2.ISecurityGroup):
        super().__init__(context, name, scope, vpc, description='Web Portal security group')
        self.bastion_host_security_group = bastion_host_security_group
        self.loadbalancer_security_group = loadbalancer_security_group
        self.setup_ingress()
        self.setup_egress()
        if self.is_ds_activedirectory():
            self.add_active_directory_rules()

    def setup_ingress(self):
        self.add_api_ingress_rule()
        self.add_bastion_host_ingress_rule(self.bastion_host_security_group)
        self.add_loadbalancer_ingress_rule(self.loadbalancer_security_group)

        #Add inbound for SES VPC endpoint. Doesn't support these AZs
        #use1-az2, use1-az3, use1-az5, usw1-az2, usw2-az4, apne2-az4, cac1-az3, and cac1-az4
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(465),
            description='Allow SMTP traffic from VPC'
        )

    def setup_egress(self):
        self.add_outbound_traffic_rule()


class SchedulerSecurityGroup(SecurityGroup):
    """
    HPC Scheduler Security Group
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc,
                 bastion_host_security_group: ec2.ISecurityGroup,
                 loadbalancer_security_group: ec2.ISecurityGroup):
        super().__init__(context, name, scope, vpc, description='Scheduler security group')
        self.bastion_host_security_group = bastion_host_security_group
        self.loadbalancer_security_group = loadbalancer_security_group
        self.setup_ingress()
        self.setup_egress()
        if self.is_ds_activedirectory():
            self.add_active_directory_rules()

    def setup_ingress(self):
        self.add_api_ingress_rule()

        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp_range(0, 65535),
            description='Allow all TCP traffic from VPC to scheduler'
        )

        self.add_bastion_host_ingress_rule(self.bastion_host_security_group)

        self.add_loadbalancer_ingress_rule(self.loadbalancer_security_group)

    def setup_egress(self):
        self.add_outbound_traffic_rule()


class ComputeNodeSecurityGroup(SecurityGroup):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc):
        super().__init__(context, name, scope, vpc, description='Compute Node security group')
        self.setup_ingress()
        self.setup_egress()
        if self.is_ds_activedirectory():
            self.add_active_directory_rules()

    def setup_ingress(self):
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp_range(0, 65535),
            description='All TCP traffic from all VPC nodes to compute node'
        )

        self.add_ingress_rule(
            self,
            ec2.Port.all_traffic(),
            description='Allow all traffic between compute nodes and EFA'
        )

    def setup_egress(self):
        self.add_outbound_traffic_rule()

        self.add_egress_rule(
            self,
            ec2.Port.all_traffic(),
            description='Allow all traffic between compute nodes and EFA'
        )


class VirtualDesktopBastionAccessSecurityGroup(SecurityGroup):
    """
    Virtual Desktop Security Group with Bastion Access
    """
    component_name: str

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct, vpc: ec2.IVpc,
                 bastion_host_security_group: ec2.ISecurityGroup, description: str, directory_service_access: bool, component_name: str):
        super().__init__(context, name, scope, vpc, description=description)
        self.component_name = component_name
        self.bastion_host_security_group = bastion_host_security_group
        self.setup_ingress()
        self.setup_egress()
        if directory_service_access and self.is_ds_activedirectory():
            self.add_active_directory_rules()

    def setup_ingress(self):
        self.add_api_ingress_rule()
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.all_traffic(),
            description=f'Allow all Internal traffic TO {self.component_name}'
        )
        self.add_bastion_host_ingress_rule(self.bastion_host_security_group)

    def setup_egress(self):
        self.add_outbound_traffic_rule()


class VirtualDesktopPublicLoadBalancerAccessSecurityGroup(SecurityGroup):
    """
    Virtual Desktop Security Group with Bastion and Public Loadbalancer Access
    """
    component_name: str

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct, vpc: ec2.IVpc,
                 bastion_host_security_group: ec2.ISecurityGroup, description: str, directory_service_access: bool, component_name: str,
                 public_loadbalancer_security_group: ec2.ISecurityGroup):
        super().__init__(context, name, scope, vpc, description=description)
        self.component_name = component_name
        self.public_loadbalancer_security_group = public_loadbalancer_security_group
        self.bastion_host_security_group = bastion_host_security_group
        self.setup_ingress()
        self.setup_egress()
        if directory_service_access and self.is_ds_activedirectory():
            self.add_active_directory_rules()

    def setup_ingress(self):
        self.add_api_ingress_rule()
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.all_traffic(),
            description=f'Allow all Internal traffic TO {self.component_name}'
        )
        self.add_bastion_host_ingress_rule(self.bastion_host_security_group)
        self.add_loadbalancer_ingress_rule(self.public_loadbalancer_security_group)

    def setup_egress(self):
        self.add_outbound_traffic_rule()

class VirtualDesktopCustomCredentialBrokerSecurityGroup(SecurityGroup):
    """
    Virtual Desktop Security Group for Custom Credential Broker with internal HTTPS traffic access for Virtual Desktop Infrastructure (VDI) hosts
    """
    component_name: str

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc, component_name: str, vdi_cidr_blocks: List[str]):
        super().__init__(context, name, scope, vpc, description='Virtual Desktop Controller Credential Broker Lambda Function Security Group')
        self.component_name = component_name
        self.setup_ingress(vdi_cidr_blocks)
        self.setup_egress()

    def setup_ingress(self, vdi_cidr_blocks: List[str]):
        for cidr in vdi_cidr_blocks:
            self.add_ingress_rule(
                ec2.Peer.ipv4(cidr),
                ec2.Port.tcp(443),
                description=f'Allow internal HTTPS traffic for Virtual Desktop Infrastructure (VDI) hosts to {self.component_name}'
            )

    def setup_egress(self):
        self.add_outbound_traffic_rule()

class VpcEndpointSecurityGroup(SecurityGroup):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct, vpc: ec2.IVpc):
        super().__init__(context, name, scope, vpc, allow_all_outbound=True, description='VPC Endpoints Security Group')
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(443),
            description='Allow HTTPS traffic from VPC'
        )


class VpcGatewayEndpoint(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, scope: constructs.Construct,
                 service: str,
                 vpc: ec2.IVpc,
                 create_tags: CreateTagsCustomResource):
        super().__init__(context, f'{service}-gateway-endpoint')
        self.scope = scope

        self.endpoint = vpc.add_gateway_endpoint(
            self.construct_id,
            service=ec2.GatewayVpcEndpointAwsService(
                name=service
            )
        )

        create_tags.apply(
            name=self.name,
            resource_id=self.endpoint.vpc_endpoint_id,
            tags={
                constants.IDEA_TAG_NAME: self.name,
                constants.IDEA_TAG_ENVIRONMENT_NAME: self.cluster_name
            }
        )


class VpcInterfaceEndpoint(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, scope: constructs.Construct,
                 service: str,
                 vpc: ec2.IVpc,
                 vpc_endpoint_security_group: ec2.ISecurityGroup,
                 create_tags: CreateTagsCustomResource,
                 lookup_supported_azs=True,
                 subnets: ec2.SubnetSelection = None,
                 ):
        super().__init__(context, f'{service}-vpc-endpoint')
        self.scope = scope

        # this is a change from 2.x behaviour, where access to VPC endpoints was restricted by security group.
        # in 3.x, since security groups for individual components do not exist during cluster/network creation,
        # all VPC traffic can communicate with VPC Interface endpoints.
        self.endpoint = vpc.add_interface_endpoint(self.construct_id,
                                                   service=ec2.InterfaceVpcEndpointAwsService(
                                                       name=service
                                                   ),
                                                   open=True,
                                                   # setting private_dns_enabled = True can be problem in GovCloud where Route53 and in turn Private Hosted Zones is not supported.
                                                   private_dns_enabled=True,
                                                   lookup_supported_azs=lookup_supported_azs,
                                                   security_groups=[vpc_endpoint_security_group],
                                                   subnets=subnets
                                                   )

        create_tags.apply(
            name=self.name,
            resource_id=self.endpoint.vpc_endpoint_id,
            tags={
                constants.IDEA_TAG_NAME: self.name,
                constants.IDEA_TAG_ENVIRONMENT_NAME: self.cluster_name
            }
        )

    def get_endpoint_url(self) -> str:
        dns = cdk.Fn.select(1, cdk.Fn.split(':', cdk.Fn.select(0, self.endpoint.vpc_endpoint_dns_entries)))
        return f'https://{dns}'

    def get_endpoint(self) -> ec2.InterfaceVpcEndpoint:
        return self.endpoint

class DefaultClusterSecurityGroup(SecurityGroup):
    """
    Default Cluster Security Group with no inbound or outbound rules.
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc):
        super().__init__(context, name, scope, vpc, description='Default Cluster Security')


class InternalLoadBalancerSecurityGroup(SecurityGroup):
    """
    Internal Load Balancer Security Group
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc):
        super().__init__(context, name, scope, vpc, description='Internal load balancer security group')
        self.setup_ingress()
        self.setup_egress()

    def setup_ingress(self):
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(443),
            description='Allow HTTPS traffic from all VPC nodes'
        )

    def setup_egress(self):
        self.add_outbound_traffic_rule()
