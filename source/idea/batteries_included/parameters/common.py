#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass
from typing import Any, Optional

from idea.infrastructure.install.constants import OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX
from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class CommonKey(Key):
    CLUSTER_NAME = "EnvironmentName"
    ADMIN_EMAIL = "AdministratorEmail"
    INFRASTRUCTURE_HOST_AMI = "InfrastructureHostAMI"
    SSH_KEY_PAIR = "SSHKeyPair"
    CLIENT_IP = "ClientIp"
    CLIENT_PREFIX_LIST = "ClientPrefixList"
    IAM_PERMISSION_BOUNDARY = "IAMPermissionBoundary"
    IAM_RESOURCE_PREFIX = "IAMResourcePrefix"
    IAM_RESOURCE_PATH = "IAMResourcePath"
    VPC_ID = "VpcId"
    LOAD_BALANCER_SUBNETS = "LoadBalancerSubnets"
    INFRASTRUCTURE_HOST_SUBNETS = "InfrastructureHostSubnets"
    VDI_SUBNETS = "VdiSubnets"
    IS_LOAD_BALANCER_INTERNET_FACING = "IsLoadBalancerInternetFacing"
    RETAIN_STORAGE_RESOURCES = "RetainStorageResources"


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
            allowed_pattern=r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})",
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
            description='Provide name of the Environment, the name of the environment must start with "res-" without capital letters and should be less than or equal to 11 characters.',
            allowed_pattern=r"res-[a-z_0-9-]{0,7}",
            constraint_description='The name of the environment must start with "res-" without capital letters and should be less than or equal to 11 characters.',
        )
    )

    administrator_email: str = Base.parameter(
        Attributes(
            id=CommonKey.ADMIN_EMAIL,
            allowed_pattern=r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$|^$)",
            constraint_description="AdministratorEmail must be a valid email id",
        )
    )

    iam_permission_boundary: str = Base.parameter(
        Attributes(
            id=CommonKey.IAM_PERMISSION_BOUNDARY,
            type="String",
            description="You may provide an IAM permission boundary ARN that will be attached to all roles created in RES.",
            allowed_pattern=r"^(?:arn:(?:aws|aws-us-gov|aws-cn):iam::[0-9]{12}:policy/[A-Za-z0-9_+=,.@-]{1,128})?$",
            constraint_description="The IAM permission boundary must be a valid ARN.",
        )
    )

    iam_resource_prefix: str = Base.parameter(
        Attributes(
            id=CommonKey.IAM_RESOURCE_PREFIX,
            type="String",
            description=(
                "You may provide an IAM resource prefix that will be attached to all IAM resources created in RES. "
                "The prefix should end with hyphen ('-') and contain no slash ('/') character."
            ),
            allowed_pattern=r"^([a-zA-Z0-9][a-zA-Z0-9_-]{0,10}-)?$",
            constraint_description="IAM resource prefix must contain only letters, numbers, hyphens, or underscores and end with a hyphen (-), and be less than or equal to 12 characters.",
        )
    )

    iam_resource_path: str = Base.parameter(
        Attributes(
            id=CommonKey.IAM_RESOURCE_PATH,
            type="String",
            description=(
                "You may provide an IAM resource path that will be attached to all IAM resources created in RES. "
                "The path should start and end with slashes ('/') and be less than or equal to 512 characters. "
                "It can contain multiple slashes ('/') between the start and end slashes ('/')."
            ),
            allowed_pattern=r"^(/[a-zA-Z0-9_./-]{0,510}/)?$",
            constraint_description="IAM resource path must start and end with '/', and be less than or equal to 512 characters.",
        )
    )

    infrastructure_host_ami: str = Base.parameter(
        Attributes(
            id=CommonKey.INFRASTRUCTURE_HOST_AMI,
            type="String",
            allowed_pattern="^(ami-[0-9a-f]{8,17})?$",
            description="You may provide a custom AMI id to use for all the infrastructure hosts. The current supported base operating systems are Amazon Linux 2, RHEL8 and RHEL9.",
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

    retain_storage_resources: str = Base.parameter(
        Attributes(
            id=CommonKey.RETAIN_STORAGE_RESOURCES,
            type="String",
            description="Retain the home file system and the RES VPC on RES deletion. Provide `True` to eliminate risk of accidentally deleting data.",
            allowed_values=["True", "False"],
        )
    )

    iam_resource_prefix_string: str = ""
    iam_resource_path_string: str = "/"
    load_balancer_subnets_string: Optional[str] = None
    infrastructure_host_subnets_string: Optional[str] = None
    dcv_session_private_subnets_string: Optional[str] = None


class CommonParameterGroups:
    parameter_group_for_environment_and_installer_details: dict[str, Any] = {
        "Label": {"default": "Environment and installer details"},
        "Parameters": [
            CommonKey.CLUSTER_NAME.value,
            CommonKey.ADMIN_EMAIL.value,
            CommonKey.SSH_KEY_PAIR.value,
            CommonKey.CLIENT_IP.value,
            CommonKey.INFRASTRUCTURE_HOST_AMI.value,
            CommonKey.CLIENT_PREFIX_LIST.value,
            CommonKey.IAM_PERMISSION_BOUNDARY.value,
            CommonKey.IAM_RESOURCE_PREFIX.value,
            CommonKey.IAM_RESOURCE_PATH.value,
        ],
    }

    parameter_group_for_network_configuration: dict[str, Any] = {
        "Label": {"default": "Network configuration for the RES environment"},
        "Parameters": [
            CommonKey.VPC_ID.value,
            CommonKey.IS_LOAD_BALANCER_INTERNET_FACING.value,
            CommonKey.LOAD_BALANCER_SUBNETS.value,
            CommonKey.INFRASTRUCTURE_HOST_SUBNETS.value,
            CommonKey.VDI_SUBNETS.value,
            CommonKey.RETAIN_STORAGE_RESOURCES.value,
        ],
    }


class CommonParameterLabels:
    parameter_labels_for_environment_and_installer_details: dict[str, Any] = {
        CommonKey.CLIENT_PREFIX_LIST.value: {
            "default": f"{CommonKey.CLIENT_PREFIX_LIST.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        CommonKey.INFRASTRUCTURE_HOST_AMI.value: {
            "default": f"{CommonKey.INFRASTRUCTURE_HOST_AMI.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        CommonKey.IAM_PERMISSION_BOUNDARY.value: {
            "default": f"{CommonKey.IAM_PERMISSION_BOUNDARY.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        CommonKey.IAM_RESOURCE_PREFIX.value: {
            "default": f"{CommonKey.IAM_RESOURCE_PREFIX.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        CommonKey.IAM_RESOURCE_PATH.value: {
            "default": f"{CommonKey.IAM_RESOURCE_PATH.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
    }
