#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass
from typing import Any

from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class CommonKey(Key):
    CLUSTER_NAME = "EnvironmentName"
    ADMIN_EMAIL = "AdministratorEmail"
    INFRASTRUCTURE_HOST_AMI = "InfrastructureHostAMI"
    SSH_KEY_PAIR = "SSHKeyPair"
    CLIENT_IP = "ClientIp"
    CLIENT_PREFIX_LIST = "ClientPrefixList"
    VPC_ID = "VpcId"
    LOAD_BALANCER_SUBNETS = "LoadBalancerSubnets"
    INFRASTRUCTURE_HOST_SUBNETS = "InfrastructureHostSubnets"
    VDI_SUBNETS = "VdiSubnets"
    IS_LOAD_BALANCER_INTERNET_FACING = "IsLoadBalancerInternetFacing"


@dataclass
class CommonParameters(Base):
    ssh_key_pair_name: str = Base.parameter(
        Attributes(
            id=CommonKey.SSH_KEY_PAIR,
            type="AWS::EC2::KeyPair::KeyName",
            description=(
                "Default SSH keys, registered in EC2 that can be used to "
                "SSH into environment instances."
            ),
            allowed_pattern=".+",
        )
    )

    client_ip: str = Base.parameter(
        Attributes(
            id=CommonKey.CLIENT_IP,
            type="String",
            description=(
                "Default IP(s) allowed to directly access the Web UI and SSH "
                "into the bastion host. We recommend that you restrict it with "
                "your own IP/subnet (x.x.x.x/32 for your own ip or x.x.x.x/24 "
                "for range. Replace x.x.x.x with your own PUBLIC IP. You can get "
                "your public IP using tools such as https://ifconfig.co/)."
            ),
            allowed_pattern="(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})",
            constraint_description=(
                "ClientIP must be a valid IP or network range of the form x.x.x.x/x. "
                "specify your IP/NETMASK (e.g x.x.x/32 or x.x.x.x/24 for subnet range)"
            ),
        )
    )

    client_prefix_list: str = Base.parameter(
        Attributes(
            id=CommonKey.CLIENT_PREFIX_LIST,
            type="String",
            description=(
                "(Optional) A prefix list that covers IPs allowed to directly access the Web UI and SSH "
                "into the bastion host."
            ),
            allowed_pattern="^(pl-[a-z0-9]{8,20})?$",
            constraint_description=(
                "Must be a valid prefix list ID, which starts with 'pl-'.  These can be "
                "found either by navigating to the VPC console, or by calling ec2:DescribePrefixLists"
            ),
        )
    )

    cluster_name: str = Base.parameter(
        Attributes(
            id=CommonKey.CLUSTER_NAME,
            type="String",
            description='Provide name of the Environment, the name of the environment must start with "res-" and should be less than or equal to 11 characters.',
            allowed_pattern="res-[A-Za-z\-\_0-9]{0,7}",
            constraint_description='The name of the environment must start with "res-" and should be less than or equal to 11 characters.',
        )
    )

    administrator_email: str = Base.parameter(
        Attributes(
            id=CommonKey.ADMIN_EMAIL,
            allowed_pattern=r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$|^$)",
            constraint_description="AdministratorEmail must be a valid email id",
        )
    )

    infrastructure_host_ami: str = Base.parameter(
        Attributes(
            id=CommonKey.INFRASTRUCTURE_HOST_AMI,
            type="String",
            allowed_pattern="^(ami-[0-9a-f]{8,17})?$",
            description="(Optional) You may provide a custom AMI id to use for all the infrastructure hosts. The current supported base OS is Amazon Linux 2.",
            constraint_description="The AMI id must begin with 'ami-' followed by only letters (a-f) or numbers(0-9).",
        )
    )

    vpc_id: str = Base.parameter(
        Attributes(
            id=CommonKey.VPC_ID,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain VpcId.",
        )
    )

    load_balancer_subnets: list[str] = Base.parameter(
        Attributes(
            id=CommonKey.LOAD_BALANCER_SUBNETS,
            type="AWS::SSM::Parameter::Value<List<String>>",
            description="Provide parameter store path to contain at least 2 subnet IDs. Select at least 2 subnets from different Availability Zones. For deployments that need restricted internet access, select private subnets. For deployments that need internet access, select public subnets.",
            allowed_pattern=".+",
        )
    )

    infrastructure_host_subnets: list[str] = Base.parameter(
        Attributes(
            id=CommonKey.INFRASTRUCTURE_HOST_SUBNETS,
            type="AWS::SSM::Parameter::Value<List<String>>",
            description="Provide parameter store path to contain at least 2 subnet IDs. Select at least 2 private subnets from different Availability Zones.",
            allowed_pattern=".+",
        )
    )

    vdi_subnets: list[str] = Base.parameter(
        Attributes(
            id=CommonKey.VDI_SUBNETS,
            type="AWS::SSM::Parameter::Value<List<String>>",
            description="Provide parameter store path to contain at least 2 subnet IDs. Select at least 2 subnets from different Availability Zones. For deployments that need restricted internet access, select private subnets. For deployments that need internet access, select public subnets",
            allowed_pattern=".+",
        )
    )

    is_load_balancer_internet_facing: str = Base.parameter(
        Attributes(
            id=CommonKey.IS_LOAD_BALANCER_INTERNET_FACING,
            type="String",
            description="Select true to deploy internet facing load balancer (Requires public subnets for load balancer). For deployments that need restricted internet access, select false.",
            allowed_values=["true", "false"],
        )
    )


class CommonParameterGroups:
    parameter_group_for_environment_and_installer_details: dict[str, Any] = {
        "Label": {"default": "Environment and installer details"},
        "Parameters": [
            CommonKey.CLUSTER_NAME,
            CommonKey.ADMIN_EMAIL,
            CommonKey.INFRASTRUCTURE_HOST_AMI,
            CommonKey.SSH_KEY_PAIR,
            CommonKey.CLIENT_IP,
            CommonKey.CLIENT_PREFIX_LIST,
        ],
    }

    parameter_group_for_network_configuration: dict[str, Any] = {
        "Label": {"default": "Network configuration for the RES environment"},
        "Parameters": [
            CommonKey.VPC_ID,
            CommonKey.IS_LOAD_BALANCER_INTERNET_FACING,
            CommonKey.LOAD_BALANCER_SUBNETS,
            CommonKey.INFRASTRUCTURE_HOST_SUBNETS,
            CommonKey.VDI_SUBNETS,
        ],
    }
