#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass
from typing import Any

from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class CommonKey(Key):
    CLUSTER_NAME = "EnvironmentName"
    ADMIN_EMAIL = "AdministratorEmail"
    SSH_KEY_PAIR = "SSHKeyPair"
    CLIENT_IP = "ClientIp"
    CLIENT_PREFIX_LIST = "ClientPrefixList"
    VPC_ID = "VpcId"
    PUBLIC_SUBNETS = "PublicSubnets"
    PRIVATE_SUBNETS = "PrivateSubnets"


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
                "A prefix list that covers IPs allowed to directly access the Web UI and SSH "
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

    vpc_id: str = Base.parameter(
        Attributes(
            id=CommonKey.VPC_ID,
            type="AWS::EC2::VPC::Id",
            allowed_pattern="vpc-[0-9a-f]{17}",
            constraint_description="VpcId must begin with 'vpc-', only contain letters (a-f) or numbers(0-9) "
            "and must be 17 characters in length",
        )
    )

    public_subnets: list[str] = Base.parameter(
        Attributes(
            id=CommonKey.PUBLIC_SUBNETS,
            type="List<AWS::EC2::Subnet::Id>",
            description="Pick at least 2 public subnets from 2 different Availability Zones",
            allowed_pattern=".+",
        )
    )

    private_subnets: list[str] = Base.parameter(
        Attributes(
            id=CommonKey.PRIVATE_SUBNETS,
            type="List<AWS::EC2::Subnet::Id>",
            description="Pick at least 2 private subnets from 2 different Availability Zones",
            allowed_pattern=".+",
        )
    )


class CommonParameterGroups:
    parameter_group_for_environment_and_installer_details: dict[str, Any] = {
        "Label": {"default": "Environment and installer details"},
        "Parameters": [
            CommonKey.CLUSTER_NAME,
            CommonKey.ADMIN_EMAIL,
            CommonKey.SSH_KEY_PAIR,
            CommonKey.CLIENT_IP,
            CommonKey.CLIENT_PREFIX_LIST,
        ],
    }

    parameter_group_for_network_configuration: dict[str, Any] = {
        "Label": {"default": "Network configuration for the RES environment"},
        "Parameters": [
            CommonKey.VPC_ID,
            CommonKey.PRIVATE_SUBNETS,
            CommonKey.PUBLIC_SUBNETS,
        ],
    }
