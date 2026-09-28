#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Nested stack for isolated VPC pipeline infrastructure.

Deploys VPC endpoints and Squid proxy server required when
IsLoadBalancerInternetFacing=false (private subnets have no internet access).

Assumes BI stack already deployed and VPC/subnet values are available
via CDK context or SSM lookups at synth time.
"""

from typing import Any, List

from aws_cdk import CfnOutput, Fn, NestedStack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct

# Interface endpoints required for RES in an isolated VPC.
# Note: email-smtp (SES) is excluded because it's unavailable in certain AZs
# (use1-az2, use1-az3, use1-az5, usw1-az2, usw2-az4, apne2-az4, cac1-az3, cac1-az4).
# Add it manually if your AZs support it and SES is needed.
INTERFACE_ENDPOINT_SERVICES = [
    "application-autoscaling",
    "cloudformation",
    "ds",
    "ec2",
    "ec2messages",
    "ecr.api",
    "ecr.dkr",
    "ecs",
    "elasticfilesystem",
    "elasticloadbalancing",
    "events",
    "fsx",
    "kinesis-streams",
    "kms",
    "lambda",
    "logs",
    "monitoring",
    "secretsmanager",
    "sns",
    "sqs",
    "ssm",
    "ssmmessages",
    "sts",
]

PROXY_PORT = 3128


class IsolatedVpcInfraStack(NestedStack):
    """
    Nested stack deploying all isolated VPC prerequisites:
    - VPC interface endpoints for AWS services
    - DynamoDB gateway endpoint
    - Squid proxy server for services without endpoint support
      (Cognito, ACM, Route53, CloudWatch)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc_id: str,
        private_subnet_ids: List[str],
        public_subnet_id: str,
        vpc_cidr: str,
        http_proxy_ssm_path: str,
        https_proxy_ssm_path: str,
        no_proxy_ssm_path: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import existing VPC
        vpc = ec2.Vpc.from_vpc_attributes(
            self,
            "Vpc",
            vpc_id=vpc_id,
            vpc_cidr_block=vpc_cidr,
            availability_zones=Fn.get_azs(),
        )

        private_subnets = [
            ec2.Subnet.from_subnet_attributes(
                self,
                f"PrivateSubnet{i}",
                subnet_id=subnet_id,
                availability_zone=Fn.select(i, Fn.get_azs()),
            )
            for i, subnet_id in enumerate(private_subnet_ids)
        ]
        public_subnet = ec2.Subnet.from_subnet_attributes(
            self,
            "PublicSubnet",
            subnet_id=public_subnet_id,
            availability_zone=Fn.select(0, Fn.get_azs()),
        )

        # --- VPC Endpoints ---
        self._create_vpc_endpoints(vpc, vpc_cidr, private_subnets)

        # --- Squid Proxy Server ---
        self._proxy_instance = self._create_proxy_server(vpc, vpc_cidr, public_subnet)

        CfnOutput(
            self,
            "ProxyPrivateIp",
            value=self._proxy_instance.instance_private_ip,
            description="Private IP of the Squid proxy server",
        )
        CfnOutput(
            self,
            "ProxyEndpoint",
            value=Fn.join(
                "",
                ["http://", self._proxy_instance.instance_private_ip, f":{PROXY_PORT}"],
            ),
            description="Proxy endpoint URL (http_proxy/https_proxy)",
        )

        # Write proxy config to SSM so InstallStack can resolve them at deploy time.
        # The SSM param names match the InternetProxyParameters keys.
        proxy_url_value = Fn.join(
            "", ["http://", self._proxy_instance.instance_private_ip, f":{PROXY_PORT}"]
        )
        no_proxy_value = Fn.join(
            ",",
            [
                "127.0.0.1",
                "169.254.169.254",
                "169.254.170.2",
                "localhost",
                Fn.sub("${AWS::Region}.res"),
                Fn.sub("${AWS::Region}.vpce.amazonaws.com"),
                Fn.sub("${AWS::Region}.elb.amazonaws.com"),
                Fn.sub("s3.${AWS::Region}.amazonaws.com"),
                Fn.sub("s3.dualstack.${AWS::Region}.amazonaws.com"),
                Fn.sub("ec2.${AWS::Region}.amazonaws.com"),
                Fn.sub("ec2.${AWS::Region}.api.aws"),
                Fn.sub("ec2messages.${AWS::Region}.amazonaws.com"),
                Fn.sub("ssm.${AWS::Region}.amazonaws.com"),
                Fn.sub("ssmmessages.${AWS::Region}.amazonaws.com"),
                Fn.sub("kms.${AWS::Region}.amazonaws.com"),
                Fn.sub("secretsmanager.${AWS::Region}.amazonaws.com"),
                Fn.sub("sqs.${AWS::Region}.amazonaws.com"),
                Fn.sub("elasticloadbalancing.${AWS::Region}.amazonaws.com"),
                Fn.sub("sns.${AWS::Region}.amazonaws.com"),
                Fn.sub("logs.${AWS::Region}.amazonaws.com"),
                Fn.sub("logs.${AWS::Region}.api.aws"),
                Fn.sub("elasticfilesystem.${AWS::Region}.amazonaws.com"),
                Fn.sub("fsx.${AWS::Region}.amazonaws.com"),
                Fn.sub("dynamodb.${AWS::Region}.amazonaws.com"),
                Fn.sub("api.ecr.${AWS::Region}.amazonaws.com"),
                Fn.sub(".dkr.ecr.${AWS::Region}.amazonaws.com"),
                Fn.sub("kinesis.${AWS::Region}.amazonaws.com"),
                Fn.sub(".data-kinesis.${AWS::Region}.amazonaws.com"),
                Fn.sub(".control-kinesis.${AWS::Region}.amazonaws.com"),
                Fn.sub("events.${AWS::Region}.amazonaws.com"),
                Fn.sub("cloudformation.${AWS::Region}.amazonaws.com"),
                Fn.sub("sts.${AWS::Region}.amazonaws.com"),
                Fn.sub("application-autoscaling.${AWS::Region}.amazonaws.com"),
                Fn.sub("monitoring.${AWS::Region}.amazonaws.com"),
                Fn.sub("ecs.${AWS::Region}.amazonaws.com"),
            ],
        )

        ssm.StringParameter(
            self,
            "SsmHttpProxy",
            parameter_name=http_proxy_ssm_path,
            string_value=proxy_url_value,
            description="HTTP proxy URL for RES isolated VPC deployment",
        )
        ssm.StringParameter(
            self,
            "SsmHttpsProxy",
            parameter_name=https_proxy_ssm_path,
            string_value=proxy_url_value,
            description="HTTPS proxy URL for RES isolated VPC deployment",
        )
        ssm.StringParameter(
            self,
            "SsmNoProxy",
            parameter_name=no_proxy_ssm_path,
            string_value=no_proxy_value,
            description="NO_PROXY exclusion list for RES isolated VPC deployment",
        )

    @property
    def proxy_url(self) -> str:
        return f"http://{self._proxy_instance.instance_private_ip}:{PROXY_PORT}"

    @property
    def proxy_private_ip(self) -> str:
        return self._proxy_instance.instance_private_ip

    def _create_vpc_endpoints(
        self,
        vpc: ec2.IVpc,
        vpc_cidr: str,
        private_subnets: List[ec2.ISubnet],
    ) -> None:
        """Create all required VPC endpoints for RES."""

        endpoint_sg = ec2.SecurityGroup(
            self,
            "EndpointSG",
            vpc=vpc,
            description="RES VPC endpoints - allows HTTPS from VPC",
            allow_all_outbound=True,
        )
        endpoint_sg.add_ingress_rule(
            ec2.Peer.ipv4(vpc_cidr),
            ec2.Port.tcp(443),
            "HTTPS from VPC",
        )
        endpoint_sg.add_ingress_rule(
            ec2.Peer.ipv4(vpc_cidr),
            ec2.Port.tcp(80),
            "HTTP from VPC",
        )

        subnet_selection = ec2.SubnetSelection(subnets=private_subnets)

        # Interface endpoints
        for service_suffix in INTERFACE_ENDPOINT_SERVICES:
            logical_id = service_suffix.replace(".", "_").replace("-", "_")
            service_name = f"com.amazonaws.{self.region}.{service_suffix}"

            ec2.InterfaceVpcEndpoint(
                self,
                f"Ep_{logical_id}",
                vpc=vpc,
                service=ec2.InterfaceVpcEndpointService(service_name, 443),
                subnets=subnet_selection,
                security_groups=[endpoint_sg],
                private_dns_enabled=True,
            )

        # Note: DynamoDB and S3 gateway endpoints require route table IDs which
        # aren't available on imported VPCs. These should be created separately
        # (e.g., via AWS Console or the RES install stack).

    def _create_proxy_server(
        self,
        vpc: ec2.IVpc,
        vpc_cidr: str,
        public_subnet: ec2.ISubnet,
    ) -> ec2.Instance:
        """Create a Squid proxy server in the public subnet."""

        proxy_sg = ec2.SecurityGroup(
            self,
            "ProxySG",
            vpc=vpc,
            description="RES Squid proxy - allows port 3128 from VPC",
            allow_all_outbound=True,
        )
        proxy_sg.add_ingress_rule(
            ec2.Peer.ipv4(vpc_cidr),
            ec2.Port.tcp(PROXY_PORT),
            "Proxy traffic from VPC",
        )

        role = iam.Role(
            self,
            "ProxyRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
            ],
        )

        squid_config = self._build_squid_config(vpc_cidr)

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "yum update -y",
            "yum install squid -y",
            f"cat > /etc/squid/squid.conf << 'SQUID_EOF'\n{squid_config}\nSQUID_EOF",
            "systemctl enable squid",
            "systemctl restart squid",
        )

        return ec2.Instance(
            self,
            "ProxyInstance",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[public_subnet]),
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            security_group=proxy_sg,
            role=role,
            user_data=user_data,
            source_dest_check=False,
            # Note: associate_public_ip_address cannot be set on imported subnets
            # (CDK requires SubnetType.PUBLIC). The public subnet must have
            # mapPublicIpOnLaunch=true configured at the VPC/subnet level.
        )

    @staticmethod
    def _build_squid_config(vpc_cidr: str) -> str:
        """Build Squid configuration allowing all VPC traffic to required domains."""
        return f"""coredump_dir /var/spool/squid

http_port {PROXY_PORT}

# AWS services
acl aws dstdomain .amazonaws.com

# Cognito
acl cognito dstdomain .amazoncognito.com

# Identity Center
acl idc1 dstdomain .awsapps.com
acl idc2 dstdomain .signin.aws
acl idc3 dstdomain .amazonaws-us-gov.com

# Allow from VPC
acl vpc_network src {vpc_cidr}

http_access allow vpc_network aws
http_access allow vpc_network cognito
http_access allow vpc_network idc1
http_access allow vpc_network idc2
http_access allow vpc_network idc3

# Deny everything else
http_access deny all"""
