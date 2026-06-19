#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Optional, Union

import aws_cdk as cdk
import constructs
from aws_cdk import CfnCondition, Fn
from aws_cdk import aws_ec2 as ec2

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs import lambda_
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.policies import (
    AddPeerIngressRulePolicy,
    UpdateClusterPrefixListPolicy,
    VpcLookupPolicy,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.add_ingress_rule_lambda import (
    add_ingress_rule_handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.update_prefix_list_lambda import (
    update_prefix_list_handler,
)
from idea.infrastructure.resources.lambda_functions.custom_resource.vpc_lookup_lambda import (
    vpc_lookup_handler,
)


class ExistingVpc(ResBaseConstruct):
    """
    Class encapsulating Existing VPC
    Acts as an intermediate entity to retrieve subnets that are configured in cluster config, instead of returning all subnets in Vpc.
    Downstream stacks should use ExistingVpc instead of ec2.Vpc to retrieve subnet information.
    """

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        arn_builder: ArnBuilder,
        lambda_layer: cdk.aws_lambda.LayerVersion,
        parameters: Union[RESParameters, BIParameters],
    ):
        self.scope = scope
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.arn_builder = arn_builder

        super().__init__(scope, name, cluster_name=self.cluster_name)

        lambda_name = f"{name}-vpc-lookup"
        vpc_lookup_lambda = lambda_.Function(
            scope,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Update cluster settings during cluster module deployment",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=vpc_lookup_handler.handler,
            layers=[lambda_layer],  # type: ignore
            initial_policy=VpcLookupPolicy.create_policy_statements(arn_builder),  # type: ignore
            parameters=parameters,
        )

        vpc_lookup_custom_resource = cdk.CustomResource(
            scope,
            f"{name}-vpc-lookup-custom-resource",
            service_token=vpc_lookup_lambda.function_arn,
            properties={
                "vpc_id": parameters.get_str(CommonKey.VPC_ID),
                "subnets": arn_builder.cluster_settings.vdi_subnets,
            },
            resource_type="Custom::VpcLookup",
        )
        vpc_lookup_custom_resource.node.add_dependency(vpc_lookup_lambda)

        cidr_block = vpc_lookup_custom_resource.get_att_string("cidr_block")
        availability_zones = vpc_lookup_custom_resource.get_att(
            "availability_zones"
        ).to_string_list()

        vpc_id = parameters.get_str(CommonKey.VPC_ID)
        self.vpc = ec2.Vpc.from_vpc_attributes(
            scope,
            f"{name}-vpc",
            vpc_cidr_block=cidr_block,
            availability_zones=availability_zones,
            private_subnet_ids=self.arn_builder.cluster_settings.infrastructure_host_subnets,  # type: ignore
            vpc_id=vpc_id,
        )
        self.vdi_subnet_cidr_blocks = vpc_lookup_custom_resource.get_att(
            "subnet_cidr_blocks"
        ).to_string_list()


class PrefixList(ResBaseConstruct, ec2.CfnPrefixList):
    """
    Prefix list of RES cluster
    """

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        address_family: str,
        max_entries: int,
        parameters: Union[RESParameters, BIParameters],
    ):
        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        super().__init__(
            scope,
            name,
            cluster_name=cluster_name,
            address_family=address_family,  # type: ignore
            max_entries=max_entries,  # type: ignore
            prefix_list_name=ResBaseConstruct.build_resource_name(name, cluster_name),  # type: ignore
        )


class UpdateClusterPrefixList(ResBaseConstruct):
    """
    Custom resource for updating the cluster prefix list based on the customer provided client IP
    """

    def __init__(
        self,
        scope: constructs.Construct,
        id_: str,
        cluster_prefix_list: ec2.PrefixList,
        arn_builder: ArnBuilder,
        lambda_layer: cdk.aws_lambda.LayerVersion,
        parameters: Union[RESParameters, BIParameters],
    ):
        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        super().__init__(scope, id_, cluster_name, parameters)

        lambda_name = "update-cluster-prefix-list-lambda"
        lambda_function = lambda_.Function(
            self,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Manage Cluster Prefix List",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=update_prefix_list_handler.handler,
            layers=[lambda_layer],  # type: ignore
            initial_policy=UpdateClusterPrefixListPolicy.create_policy_statements(arn_builder),  # type: ignore
            parameters=parameters,
        )

        lambda_function.node.add_dependency(cluster_prefix_list)

        client_ip = parameters.get_str(CommonKey.CLIENT_IP)
        client_ip_parts = Fn.split("/", client_ip)
        client_ip_has_netmask = CfnCondition(
            scope,
            "client-ip-has-netmask",
            expression=Fn.condition_equals(Fn.len(client_ip_parts), 2),
        )
        client_ip = Fn.condition_if(
            client_ip_has_netmask.logical_id,
            client_ip,
            f"{client_ip}/32",
        ).to_string()

        update_cluster_prefix_list_custom_resource = cdk.CustomResource(
            self,
            "update-cluster-prefix-list-custom-resource",
            service_token=lambda_function.function_arn,
            properties={
                "prefix_list_id": cluster_prefix_list.attr_prefix_list_id,  # type: ignore
                "add_entries": [
                    {
                        "Cidr": client_ip,
                        "Description": "Allow access to cluster from Client IP",
                    }
                ],
            },
            resource_type="Custom::ClusterPrefixList",
        )
        update_cluster_prefix_list_custom_resource.node.add_dependency(lambda_function)


class SecurityGroup(ResBaseConstruct, ec2.SecurityGroup):
    """
    Base security group
    """

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        vpc: ec2.IVpc,
        parameters: Union[RESParameters, BIParameters],
        cluster_prefix_list_id: Optional[str] = None,
        allow_all_outbound: bool = False,
        description: Optional[str] = None,
        retain_on_delete: bool = False,
    ):
        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        super().__init__(
            scope,
            name,
            cluster_name=cluster_name,
            security_group_name=ResBaseConstruct.build_resource_name(  # type: ignore
                name, cluster_name
            ),
            vpc=vpc,  # type: ignore
            allow_all_outbound=allow_all_outbound,  # type: ignore
            description=description,  # type: ignore
        )
        self.vpc = vpc
        self.cluster_prefix_list_id = cluster_prefix_list_id

        if retain_on_delete:
            self.add_retain_on_delete()

    def add_outbound_traffic_rule(self) -> None:
        self.add_egress_rule(
            ec2.Peer.ipv4("0.0.0.0/0"),
            ec2.Port.tcp_range(0, 65535),
            description="Allow all egress for TCP",
        )

    def add_dns_resolution_egress_rule(self) -> None:
        self.add_egress_rule(
            ec2.Peer.ipv4("0.0.0.0/0"),
            ec2.Port.udp(53),
            description="Allow DNS resolution via UDP",
        )

    def add_api_ingress_rule(self) -> None:
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(8443),
            description="Allow HTTP traffic from all VPC nodes for API access",
        )

    def add_loadbalancer_ingress_rule(
        self, loadbalancer_security_group: ec2.ISecurityGroup
    ) -> None:
        self.add_ingress_rule(
            loadbalancer_security_group,
            ec2.Port.tcp(8443),
            description="Allow HTTPs traffic from Load Balancer",
        )

    def add_bastion_host_ingress_rule(
        self, bastion_host_security_group: ec2.ISecurityGroup
    ) -> None:
        self.add_ingress_rule(
            bastion_host_security_group,
            ec2.Port.tcp(22),
            description="Allow SSH from Bastion Host",
        )

    def add_active_directory_rules(self) -> None:
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.udp_range(0, 1024),
            description="Allow UDP Traffic from VPC. Required for Directory Service",
        )
        self.add_egress_rule(
            ec2.Peer.ipv4("0.0.0.0/0"),
            ec2.Port.udp_range(0, 1024),
            description="Allow UDP Traffic. Required for Directory Service",
        )


class SharedStorageSecurityGroup(SecurityGroup):
    """
    Shared storage security group with retention policy
    """

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        vpc: ec2.IVpc,
        parameters: Union[RESParameters, BIParameters],
    ):
        super().__init__(
            scope,
            name,
            vpc=vpc,
            description="Shared Storage Security Group",
            parameters=parameters,
            retain_on_delete=True,  # Security group should be retained on deletion
        )

        self.setup_ingress()

    def setup_ingress(self) -> None:
        # Add EFS ingress rule
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(2049),
            description="Allow NFS traffic from all VPC nodes to EFS",
        )

        # Add FSx Lustre ingress rules
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(988),
            description="Allow FSx Lustre traffic from all VPC nodes",
        )

        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp_range(1021, 1023),
            description="Allow FSx Lustre traffic from all VPC nodes",
        )


class BastionHostSecurityGroup(SecurityGroup):
    """
    Bastion host security group
    """

    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        cluster_prefix_list_id: str,
        parameters: Union[RESParameters, BIParameters],
    ):
        self.parameters = parameters

        super().__init__(
            scope,
            name,
            vpc=vpc,
            cluster_prefix_list_id=cluster_prefix_list_id,
            description="Bastion host security group",
            parameters=parameters,
        )
        self.setup_ingress()
        self.setup_egress()

        self.add_active_directory_rules()

    def setup_ingress(self) -> None:
        cluster_prefix_list = ec2.Peer.prefix_list(self.cluster_prefix_list_id)  # type: ignore
        self.add_ingress_rule(
            cluster_prefix_list,
            ec2.Port.tcp(22),
            description="Allow SSH access from Cluster Prefix List to Bastion Host",
        )

        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(22),
            description="Allow SSH traffic from all VPC nodes",
        )

    def setup_egress(self) -> None:
        self.add_outbound_traffic_rule()


class ExternalLoadBalancerSecurityGroup(SecurityGroup):
    """
    External load balancer security group
    """

    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        cluster_prefix_list_id: str,
        bastion_host_security_group: ec2.ISecurityGroup,
        parameters: Union[RESParameters, BIParameters],
    ):
        self.scope = scope
        self.parameters = parameters

        super().__init__(
            scope,
            name,
            vpc=vpc,
            cluster_prefix_list_id=cluster_prefix_list_id,
            description="External Application Load Balancer security group",
            parameters=parameters,
        )
        self.bastion_host_security_group = bastion_host_security_group
        self.setup_ingress()
        self.setup_egress()

    def add_peer_ingress_rule(self, peer: ec2.IPeer, peer_type: str) -> None:
        self.add_ingress_rule(
            peer,
            ec2.Port.tcp(443),
            description=f"Allow HTTPS access from {peer_type} to ALB",
        )

        self.add_ingress_rule(
            peer,
            ec2.Port.tcp(80),
            description=f"Allow HTTP access from {peer_type} to ALB",
        )

    def setup_ingress(self) -> None:
        cluster_prefix_list = ec2.Peer.prefix_list(self.cluster_prefix_list_id)  # type: ignore
        self.add_peer_ingress_rule(cluster_prefix_list, "Cluster Prefix List")

        ec2.CfnSecurityGroupIngress(
            self.scope,
            "bastion-host-http-ingress",
            group_id=self.security_group_id,
            source_security_group_id=self.bastion_host_security_group.security_group_id,
            ip_protocol="tcp",
            from_port=80,
            to_port=80,
            description="Allow HTTP from Bastion Host",
        )

        ec2.CfnSecurityGroupIngress(
            self.scope,
            "bastion-host-https-ingress",
            group_id=self.security_group_id,
            source_security_group_id=self.bastion_host_security_group.security_group_id,
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            description="Allow HTTPS from Bastion Host",
        )

    def setup_egress(self) -> None:
        self.add_outbound_traffic_rule()


class AddPrefixListPeerIngressRule(ResBaseConstruct):
    """
    Custom resource for creating security group ingress rules based on the customer provided prefix list
    """

    def __init__(
        self,
        scope: constructs.Construct,
        id_: str,
        external_alb_security_group_id: str,
        bastion_host_security_group_id: str,
        arn_builder: ArnBuilder,
        lambda_layer: cdk.aws_lambda.LayerVersion,
        parameters: Union[RESParameters, BIParameters],
    ):
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.parameters = parameters
        super().__init__(scope, id_, self.cluster_name, self.parameters)

        prefix_list_id = self.parameters.get_str(CommonKey.CLIENT_PREFIX_LIST)
        lambda_name = "add-prefix-list-peer-ingress-rule-lambda"
        lambda_function = lambda_.Function(
            self,
            lambda_name,
            runtime=constants.RES_COMMON_LAMBDA_RUNTIME,
            description="Add prefix list peer ingress rule",  # type: ignore
            timeout=cdk.Duration.seconds(180),  # type: ignore
            handler=add_ingress_rule_handler.handler,
            layers=[lambda_layer],  # type: ignore
            initial_policy=AddPeerIngressRulePolicy.create_policy_statements(arn_builder),  # type: ignore
            parameters=self.parameters,
        )
        add_prefix_list_peer_ingress_rule_custom_resource = cdk.CustomResource(
            self,
            "add-prefix-list-peer-ingress-rule-custom-resource",
            service_token=lambda_function.function_arn,
            properties={
                "ingress_rule_mappings": [
                    {
                        "security_group_id": external_alb_security_group_id,
                        "ingress_rules": [
                            {
                                "IpProtocol": "tcp",
                                "FromPort": 443,
                                "ToPort": 443,
                                "PrefixListIds": [
                                    {
                                        "PrefixListId": prefix_list_id,
                                        "Description": f"Allow HTTPS access from prefix list to ALB",
                                    }
                                ],
                            },
                            {
                                "IpProtocol": "tcp",
                                "FromPort": 80,
                                "ToPort": 80,
                                "PrefixListIds": [
                                    {
                                        "PrefixListId": prefix_list_id,
                                        "Description": f"Allow HTTP access from prefix list to ALB",
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "security_group_id": bastion_host_security_group_id,
                        "ingress_rules": [
                            {
                                "IpProtocol": "tcp",
                                "FromPort": 22,
                                "ToPort": 22,
                                "PrefixListIds": [
                                    {
                                        "PrefixListId": prefix_list_id,
                                        "Description": f"Allow SSH access from Prefix List to Bastion Host",
                                    }
                                ],
                            },
                        ],
                    },
                ],
            },
            resource_type="Custom::AddPrefixListPeerIngressRule",
        )
        add_prefix_list_peer_ingress_rule_custom_resource.node.add_dependency(
            lambda_function
        )


class InternalLoadBalancerSecurityGroup(SecurityGroup):
    """
    Internal load balancer security group
    """

    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        parameters: Union[RESParameters, BIParameters],
    ):
        super().__init__(
            scope,
            name,
            vpc,
            description="Internal load balancer security group",
            parameters=parameters,
        )
        self.setup_ingress()
        self.setup_egress()

    def setup_ingress(self) -> None:
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(443),
            description="Allow HTTPS traffic from all VPC nodes",
        )

    def setup_egress(self) -> None:
        self.add_outbound_traffic_rule()


class VirtualDesktopBastionAccessSecurityGroup(SecurityGroup):
    """
    Virtual Desktop Security Group with Bastion Access
    """

    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        parameters: Union[RESParameters, BIParameters],
        bastion_host_security_group: ec2.ISecurityGroup,
        description: str,
        directory_service_access: bool,
        component_name: str,
    ):
        super().__init__(
            scope,
            name,
            vpc,
            description=description,
            parameters=parameters,
        )
        self.component_name = component_name
        self.bastion_host_security_group = bastion_host_security_group
        self.setup_ingress()
        self.setup_egress()
        if directory_service_access:
            self.add_active_directory_rules()

    def setup_ingress(self) -> None:
        self.add_api_ingress_rule()
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.all_traffic(),
            description=f"Allow all Internal traffic TO {self.component_name}",
        )
        self.add_bastion_host_ingress_rule(self.bastion_host_security_group)

    def setup_egress(self) -> None:
        self.add_outbound_traffic_rule()


class VirtualDesktopPublicLoadBalancerAccessSecurityGroup(SecurityGroup):
    """
    Virtual Desktop Security Group with Bastion and Public Loadbalancer Access
    """

    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        parameters: Union[RESParameters, BIParameters],
        bastion_host_security_group: ec2.ISecurityGroup,
        description: str,
        directory_service_access: bool,
        component_name: str,
        public_loadbalancer_security_group: ec2.ISecurityGroup,
    ):
        super().__init__(
            scope,
            name,
            vpc,
            parameters=parameters,
            description=description,
        )
        self.component_name = component_name
        self.public_loadbalancer_security_group = public_loadbalancer_security_group
        self.bastion_host_security_group = bastion_host_security_group
        self.setup_ingress()
        self.setup_egress()
        if directory_service_access:
            self.add_active_directory_rules()

    def setup_ingress(self) -> None:
        self.add_api_ingress_rule()
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.all_traffic(),
            description=f"Allow all Internal traffic TO {self.component_name}",
        )
        self.add_bastion_host_ingress_rule(self.bastion_host_security_group)
        self.add_loadbalancer_ingress_rule(self.public_loadbalancer_security_group)

    def setup_egress(self) -> None:
        self.add_outbound_traffic_rule()


class VpcEndpointSecurityGroup(SecurityGroup):
    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        parameters: Union[RESParameters, BIParameters],
    ):
        super().__init__(
            scope,
            name,
            vpc,
            description="VPC Endpoints Security Group",
            parameters=parameters,
            allow_all_outbound=True,
        )
        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(443),
            description="Allow HTTPS traffic from VPC",
        )


class VirtualDesktopCustomCredentialBrokerSecurityGroup(SecurityGroup):
    """
    Virtual Desktop Security Group for Custom Credential Broker with internal HTTPS traffic access for Virtual Desktop Infrastructure (VDI) hosts
    """

    component_name: str

    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        component_name: str,
        parameters: Union[RESParameters, BIParameters],
    ):
        super().__init__(
            scope,
            name,
            vpc,
            description="Virtual Desktop Controller Credential Broker Lambda Function Security Group",
            parameters=parameters,
        )
        self.component_name = component_name
        self.setup_egress()

    def setup_egress(self) -> None:
        self.add_outbound_traffic_rule()
        self.add_dns_resolution_egress_rule()


class VpcInterfaceEndpoint(ResBaseConstruct):

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        vpc: ec2.IVpc,
        arn_builder: ArnBuilder,
        parameters: Union[RESParameters, BIParameters],
        vpc_endpoint_security_group: ec2.ISecurityGroup,
        lookup_supported_azs: bool = True,
        private_dns_enabled: bool = True,
    ):

        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        super().__init__(scope, f"{name}-vpc-endpoint", self.cluster_name, parameters)
        self.scope = scope

        subnets = ec2.SubnetSelection(
            subnets=[  # type: ignore
                ec2.Subnet.from_subnet_id(
                    self.scope,
                    f"interface-endpoint-subnet-{index}",
                    subnet_id,
                )
                for index, subnet_id in enumerate(
                    arn_builder.cluster_settings.infrastructure_host_subnets  # type: ignore
                )
            ]
        )

        self.endpoint = vpc.add_interface_endpoint(
            self.construct_id,
            service=ec2.InterfaceVpcEndpointAwsService(name=name),
            open=True,
            # setting private_dns_enabled = True can be problem in GovCloud where Route53 and in turn Private Hosted Zones is not supported.
            private_dns_enabled=private_dns_enabled,
            lookup_supported_azs=lookup_supported_azs,
            security_groups=[vpc_endpoint_security_group],
            subnets=subnets,
        )
        self.add_common_tags(self.endpoint)

    def get_endpoint_url(self) -> str:
        dns = cdk.Fn.select(
            1,
            cdk.Fn.split(":", cdk.Fn.select(0, self.endpoint.vpc_endpoint_dns_entries)),
        )
        return f"https://{dns}"

    def get_endpoint(self) -> ec2.InterfaceVpcEndpoint:
        return self.endpoint


class ClusterManagerSecurityGroup(SecurityGroup):
    """
    Cluster Manager Security Group
    """

    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        bastion_host_security_group: ec2.ISecurityGroup,
        loadbalancer_security_group: ec2.ISecurityGroup,
        parameters: Union[RESParameters, BIParameters],
    ):
        super().__init__(
            scope,
            name,
            vpc,
            description="Cluster Manager security group",
            parameters=parameters,
        )
        self.bastion_host_security_group = bastion_host_security_group
        self.loadbalancer_security_group = loadbalancer_security_group
        self.setup_ingress()
        self.setup_egress()
        self.add_active_directory_rules()

    def setup_ingress(self) -> None:
        self.add_api_ingress_rule()
        self.add_bastion_host_ingress_rule(self.bastion_host_security_group)
        self.add_loadbalancer_ingress_rule(self.loadbalancer_security_group)

        self.add_ingress_rule(
            ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            ec2.Port.tcp(465),
            description="Allow SMTPS traffic from VPC",
        )

    def setup_egress(self) -> None:
        self.add_outbound_traffic_rule()


class DcvSessionManagementLambdaSecurityGroup(SecurityGroup):
    """
    Security group for the DCV Session Management Lambda.
    Only egress rules are needed — ALB invokes Lambda via the
    Lambda API, not through VPC networking.
    """

    def __init__(
        self,
        name: str,
        scope: constructs.Construct,
        vpc: ec2.IVpc,
        parameters: Union[RESParameters, BIParameters],
    ):
        super().__init__(
            scope,
            name,
            vpc,
            description="DCV Session Management Lambda security group",
            parameters=parameters,
        )
        self.setup_egress()

    def setup_egress(self) -> None:
        self.add_outbound_traffic_rule()
        self.add_dns_resolution_egress_rule()
