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

import ideaadministrator
from ideaadministrator.app.cdk.idea_code_asset import IdeaCodeAsset, SupportedLambdaPlatforms
from ideaadministrator.app.cdk.stacks import IdeaBaseStack
from ideadatamodel import (
    constants
)
from ideasdk.utils import Utils

from ideaadministrator.app.cdk.constructs import (
    Vpc,
    ExistingVpc,
    SubnetFilterKeys,
    VpcGatewayEndpoint,
    VpcInterfaceEndpoint,
    PrivateHostedZone,
    SecurityGroup,
    DefaultClusterSecurityGroup,
    BastionHostSecurityGroup,
    ExternalLoadBalancerSecurityGroup,
    InternalLoadBalancerSecurityGroup,
    VpcEndpointSecurityGroup,
    CreateTagsCustomResource,
    Policy,
    ManagedPolicy,
    Role,
    LambdaFunction,
    SNSTopic,
    BackupPlan
)
from ideaadministrator import app_constants

from typing import List, Dict, Optional

import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_events as events,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_events_targets as events_targets,
    aws_s3 as s3,
    aws_backup as backup,
    aws_kms as kms
)


class ClusterStack(IdeaBaseStack):
    """
    Cluster Stack

    Provisions base infrastructure components for RES Environment:
    * VPC, VPC Endpoints (if applicable)
    * Internal and External Load Balancers
    * Common IAM Roles and Security Groups
    * Self-signed Certificates (if applicable)
    * Route53 Private Hosted Zone
    * Common custom resource Lambda Functions
    * Cluster Prefix List
    * AWS Backup Vault and Backup Plan
    * Cluster Settings
    """

    def __init__(self, scope: constructs.Construct,
                 cluster_name: str,
                 aws_region: str,
                 aws_profile: str,
                 module_id: str,
                 deployment_id: str,
                 termination_protection: bool = True,
                 env: cdk.Environment = None):

        super().__init__(scope=scope,
                         cluster_name=cluster_name,
                         aws_region=aws_region,
                         aws_profile=aws_profile,
                         module_id=module_id,
                         deployment_id=deployment_id,
                         termination_protection=termination_protection,
                         description=f'ModuleId: {module_id}, Cluster: {cluster_name}, Version: {ideaadministrator.props.current_release_version}',
                         tags={
                             constants.IDEA_TAG_MODULE_ID: module_id,
                             constants.IDEA_TAG_MODULE_NAME: constants.MODULE_CLUSTER,
                             constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
                         },
                         env=env)

        # if user wants to use an existing VPC, user may provide and existing VPC ID.
        # in that case, lookup the VPC and optionally, VpcInterface endpoints if specified, using ExistingVpc construct.
        # else, create a new Vpc
        self._vpc: Optional[Vpc] = None
        self._existing_vpc: Optional[ExistingVpc] = None

        # provisioned only for new VPC
        self.vpc_gateway_endpoints: Optional[Dict[str, VpcGatewayEndpoint]] = None
        self.vpc_interface_endpoints: Optional[Dict[str, VpcInterfaceEndpoint]] = None

        self.self_signed_certificate_lambda: Optional[LambdaFunction] = None
        self.external_certificate: Optional[cdk.CustomResource] = None
        self.internal_certificate: Optional[cdk.CustomResource] = None

        self.backup_policies: Optional[Dict[str, ManagedPolicy]] = None
        self.backup_role: Optional[Role] = None
        self.backup_vault: Optional[backup.BackupVault] = None
        self.backup_plan: Optional[BackupPlan] = None

        self.cluster_endpoints_lambda: Optional[LambdaFunction] = None
        self.external_alb: Optional[elbv2.ApplicationLoadBalancer] = None
        self.external_alb_https_listener: Optional[elbv2.CfnListener] = None
        self.internal_alb_dns_record_set: Optional[route53.RecordSet] = None
        self.internal_alb: Optional[elbv2.ApplicationLoadBalancer] = None
        self.internal_alb_https_listener: Optional[elbv2.CfnListener] = None
        self.internal_alb_dcv_broker_client_listener: Optional[elbv2.CfnListener] = None
        self.internal_alb_dcv_broker_agent_listener: Optional[elbv2.CfnListener] = None
        self.internal_alb_dcv_broker_gateway_listener: Optional[elbv2.CfnListener] = None

        self.dcv_host_role_managed_policy: Optional[ManagedPolicy] = None

        self.private_hosted_zone: Optional[PrivateHostedZone] = None
        self.cluster_prefix_list: Optional[ec2.CfnPrefixList] = None
        self.security_groups: Dict[str, SecurityGroup] = {}
        self.roles: Dict[str, Role] = {}
        self.amazon_ssm_managed_instance_core_policy: Optional[ManagedPolicy] = None
        self.cloud_watch_agent_server_policy: Optional[ManagedPolicy] = None
        self.amazon_prometheus_remote_write_policy: Optional[ManagedPolicy] = None

        self.oauth_credentials_lambda: Optional[LambdaFunction] = None
        self.solution_metrics_lambda: Optional[LambdaFunction] = None
        self.solution_metrics_lambda_policy: Optional[Policy] = None
        self.cluster_settings_lambda: Optional[LambdaFunction] = None
        self.cluster_settings_lambda_policy: Optional[Policy] = None

        self.ec2_events_sns_topic: Optional[SNSTopic] = None

        # build backups
        self.build_backups()

        # build common policies
        # these policies are essential available in form of managed policies, but AWS managed policies are too broad
        # from a security perspective and need to scope them down
        self.build_policies()

        # build roles
        self.build_roles()

        # build self-signed certificates lambda function
        self.build_self_signed_certificates_lambda()

        # self-signed certificates
        self.build_self_signed_certificates()

        # cluster settings lambda function
        self.build_cluster_settings_lambda()

        # vpc
        self.build_vpc()

        # cluster prefix list
        self.build_cluster_prefix_list()

        # security groups
        self.build_security_groups()

        # setup private hosted zone
        self.build_private_hosted_zone()

        # ec2-notification module
        self.build_ec2_notification_module()

        # cluster endpoints
        self.build_cluster_endpoints()

        # vpc endpoints
        self.build_vpc_endpoints()

        # solution metrics lambda function
        self.build_solution_metrics_lambda()

        # build outputs
        self.build_cluster_settings()

    @property
    def vpc(self) -> ec2.IVpc:
        if self.context.config().get_bool('cluster.network.use_existing_vpc', False):
            return self._existing_vpc.vpc
        else:
            return self._vpc

    def private_subnets(self, subnet_filter_key: Optional[SubnetFilterKeys] = None) -> List[ec2.ISubnet]:
        if self.context.config().get_bool('cluster.network.use_existing_vpc', False):
            return self._existing_vpc.get_private_subnets(subnet_filter_key)
        else:
            return self.vpc.private_subnets

    def public_subnets(self, subnet_filter_key: Optional[SubnetFilterKeys] = None) -> List[ec2.ISubnet]:
        if self.context.config().get_bool('cluster.network.use_existing_vpc', False):
            return self._existing_vpc.get_public_subnets(subnet_filter_key)
        else:
            return self.vpc.public_subnets

    def build_backups(self):

        enable_backup = self.context.config().get_bool('cluster.backups.enabled', default=False)
        if not enable_backup:
            return

        enable_restore = self.context.config().get_bool('cluster.backups.enable_restore', default=True)

        # role and policies
        # all backup polices must be managed policies and not inline policies.
        # if added as inline policies - the maximum policy size of 10240 bytes exceeded error is raised.
        backup_create_policy = ManagedPolicy(
            self.context, 'backup-create-policy', self.stack,
            managed_policy_name=f'{self.cluster_name}-{self.aws_region}-backup-create',
            description='Provides AWS Backup permission to create backups on your behalf across AWS services',
            policy_template_name='backup-create.yml'
        )
        backup_s3_create_policy = ManagedPolicy(
            self.context, 'backup-s3-create-policy', self.stack,
            managed_policy_name=f'{self.cluster_name}-{self.aws_region}-backup-s3-create',
            description='Policy containing permissions necessary for AWS Backup to backup data in any S3 bucket. '
                        'This includes read access to all S3 objects and any decrypt access for all KMS keys.',
            policy_template_name='backup-s3-create.yml'
        )

        backup_restore_policy = None
        backup_s3_restore_policy = None
        if enable_restore:
            backup_restore_policy = ManagedPolicy(
                self.context, 'backup-restore-policy', self.stack,
                managed_policy_name=f'{self.cluster_name}-{self.aws_region}-backup-restore',
                description='Provides AWS Backup permission to perform restores on your behalf across AWS services. '
                            'This policy includes permissions to create and delete AWS resources, such as EBS volumes, RDS instances, and EFS file systems, which are part of the restore process.',
                policy_template_name='backup-restore.yml'
            )
            backup_s3_restore_policy = ManagedPolicy(
                self.context, 'backup-s3-restore-policy', self.stack,
                managed_policy_name=f'{self.cluster_name}-{self.aws_region}-backup-s3-restore',
                description='Policy containing permissions necessary for AWS Backup to restore a S3 backup to a bucket. '
                            'This includes read/write permissions to all S3 buckets, and permissions to GenerateDataKey and DescribeKey for all KMS keys.',
                policy_template_name='backup-s3-restore.yml'
            )

        backup_role = Role(
            context=self.context,
            name=f'{self.module_id}-backup-role',
            scope=self.stack,
            description='Role used by AWS Backup to authenticate when backing or restoring the resources',
            assumed_by=['backup']
        )
        backup_role.add_managed_policy(backup_create_policy)
        backup_role.add_managed_policy(backup_s3_create_policy)
        if enable_restore:
            backup_role.add_managed_policy(backup_restore_policy)
            backup_role.add_managed_policy(backup_s3_restore_policy)

        # backup vault
        backup_vault_removal_policy = self.context.config().get_string('cluster.backups.backup_vault.removal_policy', default='RETAIN')
        backup_vault_kms_key_id = self.context.config().get_string('cluster.backups.backup_vault.kms_key_id', default=None)
        backup_vault_encryption_key = None
        if Utils.is_not_empty(backup_vault_kms_key_id):
            backup_vault_encryption_key = kms.Key.from_key_arn(self.stack, 'backup-vault-kms-key', self.get_kms_key_arn(key_id=backup_vault_kms_key_id))
        backup_vault = backup.BackupVault(
            self.stack, 'backup-vault',
            backup_vault_name=f'{self.cluster_name}-{self.module_id}-backup-vault',
            encryption_key=backup_vault_encryption_key,
            removal_policy=cdk.RemovalPolicy(backup_vault_removal_policy)
        )

        # backup plan
        backup_plan_config = self.context.config().get_config('cluster.backups.backup_plan')
        # create immutable reference to prevent BackupSelection from automatically adding the AWS Backup related managed policies to the role.
        immutable_backup_role = backup_role.without_policy_updates()
        backup_plan = BackupPlan(
            self.context, 'cluster-backup-plan', self.stack,
            backup_plan_name=f'{self.cluster_name}-{self.module_id}',
            backup_plan_config=backup_plan_config,
            backup_vault=backup_vault,
            backup_role=immutable_backup_role
        )

        backup_plan.backup_selection.node.add_dependency(backup_create_policy)
        backup_plan.backup_selection.node.add_dependency(backup_s3_create_policy)
        if enable_restore:
            backup_plan.backup_selection.node.add_dependency(backup_restore_policy)
            backup_plan.backup_selection.node.add_dependency(backup_s3_restore_policy)
        backup_plan.backup_selection.node.add_dependency(backup_role)

        self.backup_role = backup_role
        self.backup_vault = backup_vault
        self.backup_plan = backup_plan

    def build_policies(self):
        self.amazon_ssm_managed_instance_core_policy = ManagedPolicy(
            self.context, 'amazon-ssm-managed-instance-core', self.stack,
            managed_policy_name=f'{self.cluster_name}-{self.aws_region}-amazon-ssm-managed-instance-core',
            description='The policy for Amazon EC2 Role to enable AWS Systems Manager service core functionality.',
            policy_template_name='amazon-ssm-managed-instance-core.yml'
        )

        self.cloud_watch_agent_server_policy = ManagedPolicy(
            self.context, 'cloud-watch-agent-server-policy', self.stack,
            managed_policy_name=f'{self.cluster_name}-{self.aws_region}-cloud-watch-agent-server-policy',
            description='Permissions required to use AmazonCloudWatchAgent on servers',
            policy_template_name='cloud-watch-agent-server-policy.yml'
        )

        self.dcv_host_role_managed_policy = ManagedPolicy(
                context=self.context,
                name='vdi-host-managed-policy',
                description="Required policy for custom VDI instance profiles",
                managed_policy_name=f'{self.cluster_name}-{self.aws_region}-vdi-host-managed-policy',
                scope=self.stack,
                policy_template_name='virtual-desktop-dcv-host.yml'
        )

        if self.is_metrics_provider_amazon_managed_prometheus():
            self.amazon_prometheus_remote_write_policy = ManagedPolicy(
                self.context, 'amazon-prometheus-remote-write-access', self.stack,
                managed_policy_name=f'{self.cluster_name}-{self.aws_region}-amazon-prometheus-remote-write-access',
                description='Grants write only access to AWS Managed Prometheus workspaces',
                policy_template_name='amazon-prometheus-remote-write-access.yml'
            )

    def build_roles(self):
        lambda_log_retention_role = Role(
            context=self.context,
            name=app_constants.LOG_RETENTION_ROLE_NAME,
            scope=self.stack,
            description='log retention role for CDK custom resources',
            assumed_by=['lambda'],
            inline_policies=[
                Policy(
                    context=self.context,
                    name='LogRetention',
                    scope=self.stack,
                    policy_template_name='log-retention.yml'
                )
            ]
        )
        self.roles[app_constants.LOG_RETENTION_ROLE_NAME] = lambda_log_retention_role

    def build_vpc(self):
        # if the user specifies an existing vpc id in the user config, then do not create any vpc resources
        # it is upto the administrator to manage the user config file for future upgrades and provide the same configuration file
        # each time

        if self.context.config().get_bool('cluster.network.use_existing_vpc', False):
            self._existing_vpc = ExistingVpc(
                context=self.context,
                name='existing-vpc',
                scope=self.stack
            )
        else:
            self._vpc = Vpc(self.context, 'vpc', self.stack)

    def build_private_hosted_zone(self):
        self.private_hosted_zone = PrivateHostedZone(
            context=self.context,
            scope=self.stack,
            vpc=self.vpc
        )

    def build_cluster_prefix_list(self):
        """
        cluster admins need an easy way to allow or deny additional IP addresses.

        instead of managing individual IP addresses in BastionHostSecurityGroup, ExternalALBSecurityGroup and DCVConnectionGatewaySecurityGroup, the `cluster` prefix list provides
        a central place to manage access to cluster from the external world.

        for mature infrastructure deployments, where prefix lists already exist - cluster admins will provide prefix lists to access the cluster.  config key: `cluster.network.prefix_list_ids`

        for cluster deployments that provide IP address to access the cluster, the IP addresses will be automatically added to the new cluster prefix list. config key: `cluster.network.cluster_prefix_list_id`

        All applicable security groups will allow access from `cluster.network.prefix_list_ids[] + cluster.network.cluster_prefix_list_id`

        Note for existing resources:
        `cluster.network.cluster_prefix_list_id` will NOT be reused across clusters and each IDEA cluster will create a new cluster prefix list.
        cluster admins can provide their custom prefix lists as part of `cluster.network.prefix_list_ids` to be reused across clusters

        Managing IP Addresses in cluster.network.cluster_prefix_list_id:
        We need to enable updating the cluster prefix list, outside the CDK stack. If cluster admins need to deploy the cluster stack each time to add a new IP address, the entire point of `easy way` becomes moot.
        The CDK stack will simply create the prefix list and only 'ADD' any new IP address if provided in config.
        Use `res-admin.sh utils cluster-prefix-list --help` to manage external access to the cluster.
        """
        cluster_prefix_list_max_entries = self.context.config().get_int('cluster.network.cluster_prefix_list_max_entries', 10)
        self.cluster_prefix_list = ec2.CfnPrefixList(
            scope=self.stack,
            id='cluster-prefix-list',
            address_family='IPv4',
            max_entries=cluster_prefix_list_max_entries,
            prefix_list_name=f'{self.cluster_name}-prefix-list'
        )
        self.add_common_tags(self.cluster_prefix_list)

        # do not create the custom resource if client_ip is not provided.
        client_ips = self.context.config().get_list('cluster.network.client_ip')
        if Utils.is_empty(client_ips):
            return

        lambda_name = 'update-cluster-prefix-list'
        lambda_policy = Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='custom-resource-update-cluster-prefix-list.yml'
        )
        lambda_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            description=f'Role to manage cluster prefix list Lambda function for Cluster: {self.cluster_name}',
            assumed_by=['lambda'])
        lambda_role.attach_inline_policy(lambda_policy)

        lambda_function = LambdaFunction(
            context=self.context,
            name=lambda_name,
            scope=self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_custom_resource_update_cluster_prefix_list',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            description='Manage Cluster Prefix List',
            timeout_seconds=180,
            role=lambda_role,
            log_retention_role=self.roles[app_constants.LOG_RETENTION_ROLE_NAME]
        )
        lambda_function.node.add_dependency(lambda_policy)
        lambda_function.node.add_dependency(lambda_role)
        lambda_function.node.add_dependency(self.cluster_prefix_list)

        entries = []
        for client_ip in client_ips:
            if '/' not in client_ip:
                client_ip = f'{client_ip}/32'
            entries.append({
                'Cidr': client_ip,
                'Description': 'Allow access to cluster from Client IP'
            })

        cluster_prefix_list_custom_resource = cdk.CustomResource(
            self.stack,
            f'{self.cluster_name}-{self.module_id}-cluster-prefix-list',
            service_token=lambda_function.function_arn,
            properties={
                'prefix_list_id': self.cluster_prefix_list.attr_prefix_list_id,
                'add_entries': entries
            },
            resource_type='Custom::ClusterPrefixList'
        )
        cluster_prefix_list_custom_resource.node.add_dependency(lambda_function)

    def build_security_groups(self):
        # default cluster security group
        cluster_security_group = DefaultClusterSecurityGroup(
            context=self.context,
            name='default-security-group',
            scope=self.stack,
            vpc=self.vpc
        )
        self.security_groups['cluster'] = cluster_security_group

        # bastion host
        bastion_host_security_group = BastionHostSecurityGroup(
            context=self.context,
            name='bastion-host-security-group',
            scope=self.stack,
            vpc=self.vpc,
            cluster_prefix_list_id=self.cluster_prefix_list.attr_prefix_list_id
        )
        self.security_groups['bastion-host'] = bastion_host_security_group

        # external load balancer
        external_loadbalancer_security_group = ExternalLoadBalancerSecurityGroup(
            context=self.context,
            name='external-load-balancer-security-group',
            scope=self.stack,
            vpc=self.vpc,
            bastion_host_security_group=bastion_host_security_group,
            cluster_prefix_list_id=self.cluster_prefix_list.attr_prefix_list_id
        )
        self.security_groups['external-load-balancer'] = external_loadbalancer_security_group

        # internal load balancer
        internal_loadbalancer_security_group = InternalLoadBalancerSecurityGroup(
            context=self.context,
            name='internal-load-balancer-security-group',
            scope=self.stack,
            vpc=self.vpc
        )
        self.security_groups['internal-load-balancer'] = internal_loadbalancer_security_group

        # add nat eips to load balancer security group
        nat_eips = []
        for subnet_info in self.vpc.public_subnets:
            nat_eip_for_subnet = subnet_info.node.try_find_child("EIP")
            if nat_eip_for_subnet is not None:
                nat_eips.append(nat_eip_for_subnet)
        if len(nat_eips) > 0:
            external_loadbalancer_security_group.add_nat_gateway_ips_ingress_rule(nat_eips)

        # vpc endpoint
        use_existing_vpc = self.context.config().get_bool('cluster.network.use_existing_vpc')
        use_vpc_endpoints = self.context.config().get_bool('cluster.network.use_vpc_endpoints')
        if not use_existing_vpc and use_vpc_endpoints:
            vpc_endpoint_security_group = VpcEndpointSecurityGroup(
                context=self.context,
                name='vpc-endpoint-security-group',
                scope=self.stack,
                vpc=self.vpc
            )
            self.security_groups['vpc-endpoint'] = vpc_endpoint_security_group

    def build_vpc_endpoints(self):
        use_vpc_endpoints = self.context.config().get_bool('cluster.network.use_vpc_endpoints', False)
        if not use_vpc_endpoints:
            return

        use_existing_vpc = self.context.config().get_bool('cluster.network.use_existing_vpc', False)
        if use_existing_vpc:
            return

        vpc_gateway_endpoints = {}
        vpc_interface_endpoints = {}

        create_tags = CreateTagsCustomResource(
            context=self.context,
            scope=self.stack,
            lambda_log_retention_role=self.roles[app_constants.LOG_RETENTION_ROLE_NAME]
        )

        gateway_endpoints = self.context.config().get_list('cluster.network.vpc_gateway_endpoints', [])
        for service in gateway_endpoints:
            vpc_gateway_endpoints[service] = VpcGatewayEndpoint(
                context=self.context,
                scope=self.stack,
                service=service,
                vpc=self.vpc,
                create_tags=create_tags
            )

        interface_endpoints = self.context.config().get_config('cluster.network.vpc_interface_endpoints', default={})
        for service in interface_endpoints:
            enabled = Utils.get_value_as_bool('enabled', interface_endpoints[service], default=False)
            if not enabled:
                continue
            vpc_interface_endpoints[service] = VpcInterfaceEndpoint(
                context=self.context,
                scope=self.stack,
                service=service,
                vpc=self.vpc,
                vpc_endpoint_security_group=self.security_groups['vpc-endpoint'],
                create_tags=create_tags
            )

        self.vpc_gateway_endpoints = vpc_gateway_endpoints
        self.vpc_interface_endpoints = vpc_interface_endpoints

    def build_cluster_settings_lambda(self):
        lambda_name = 'cluster-settings'

        cluster_settings_lambda_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            description=f'Role for cluster-settings lambda function for Cluster: {self.cluster_name}',
            assumed_by=['lambda'])

        self.cluster_settings_lambda_policy = Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='custom-resource-update-cluster-settings.yml'
        )

        self.cluster_settings_lambda = LambdaFunction(
            context=self.context,
            name=lambda_name,
            scope=self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_custom_resource_update_cluster_settings',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            description='Update cluster settings during cluster module deployment',
            timeout_seconds=180,
            role=cluster_settings_lambda_role,
            log_retention_role=self.roles[app_constants.LOG_RETENTION_ROLE_NAME]
        )
        cluster_settings_lambda_role.attach_inline_policy(self.cluster_settings_lambda_policy)
        self.cluster_settings_lambda.node.add_dependency(self.cluster_settings_lambda_policy)
        self.cluster_settings_lambda.node.add_dependency(cluster_settings_lambda_role)

    def build_solution_metrics_lambda(self):
        lambda_name = 'solution-metrics'

        solution_metrics_lambda_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            description=f'Role for solution-metrics metrics Lambda function for Cluster: {self.cluster_name}',
            assumed_by=['lambda'])

        self.solution_metrics_lambda_policy = Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='solution-metrics-lambda-function.yml'
        )

        self.solution_metrics_lambda = LambdaFunction(
            context=self.context,
            name=lambda_name,
            scope=self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_solution_metrics',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            description='Send anonymous Metrics to AWS',
            timeout_seconds=180,
            role=solution_metrics_lambda_role,
            log_retention_role=self.roles[app_constants.LOG_RETENTION_ROLE_NAME]
        )
        solution_metrics_lambda_role.attach_inline_policy(self.solution_metrics_lambda_policy)
        self.solution_metrics_lambda.node.add_dependency(self.solution_metrics_lambda_policy)
        self.solution_metrics_lambda.node.add_dependency(solution_metrics_lambda_role)

    def build_self_signed_certificates_lambda(self):
        """
        build self-signed certificates lambda function to be used as a custom resource in downstream modules
        """
        lambda_name = 'self-signed-certificate'

        self_signed_certificate_policy = Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='custom-resource-self-signed-certificate.yml'
        )
        self_signed_certificate_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            description=f'Role for generating self-signed certificates Lambda function for Cluster: {self.cluster_name}',
            assumed_by=['lambda'])
        self_signed_certificate_role.attach_inline_policy(self_signed_certificate_policy)

        self.self_signed_certificate_lambda = LambdaFunction(
            context=self.context,
            name=lambda_name,
            scope=self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_custom_resource_self_signed_certificate',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            description='Manage self-signed certificates for RES environment infrastructure',
            timeout_seconds=180,
            role=self_signed_certificate_role,
            log_retention_role=self.roles[app_constants.LOG_RETENTION_ROLE_NAME]
        )
        # if dependency is not explicitly added, stack deletion fails due to race condition, where policy is deleted before lambda function
        # and deletion fails.
        self.self_signed_certificate_lambda.node.add_dependency(self_signed_certificate_policy)
        self.self_signed_certificate_lambda.node.add_dependency(self_signed_certificate_role)

    def build_self_signed_certificates(self):
        external_certificate_provided = self.context.config().get_bool('cluster.load_balancers.external_alb.certificates.provided', False)
        if not external_certificate_provided:
            # create self-signed certificate for external ALB and NLB
            # all virtual desktop streaming traffic is routed via NLB
            # all API and Web Portal traffic is routed via ALB
            self.external_certificate = cdk.CustomResource(
                self.stack,
                f'{self.cluster_name}-{self.module_id}-external-cert',
                service_token=self.self_signed_certificate_lambda.function_arn,
                properties={
                    'domain_name': f'{self.cluster_name}.idea.default',
                    'certificate_name': f'{self.cluster_name}-external',
                    'create_acm_certificate': True,
                    'kms_key_id': self.context.config().get_string('cluster.secretsmanager.kms_key_id'),
                    'tags': {
                        'Name': f'{self.cluster_name} external alb certs',
                        'res:EnvironmentName': self.cluster_name
                    }
                },
                resource_type='Custom::SelfSignedCertificateExternal'
            )
            self.external_certificate.node.add_dependency(self.self_signed_certificate_lambda)

        # create self-signed certificate for internal ALB
        private_hosted_zone_name = self.context.config().get_string('cluster.route53.private_hosted_zone_name', required=True)
        self.internal_certificate = cdk.CustomResource(
            self.stack,
            f'{self.cluster_name}-{self.module_id}-internal-cert',
            service_token=self.self_signed_certificate_lambda.function_arn,
            properties={
                'domain_name': f'*.{private_hosted_zone_name}',
                'certificate_name': f'{self.cluster_name}-internal',
                'create_acm_certificate': True,
                'kms_key_id': self.context.config().get_string('cluster.secretsmanager.kms_key_id'),
                'tags': {
                    'Name': f'{self.cluster_name} internal alb certs',
                    'res:EnvironmentName': self.cluster_name
                }
            },
            resource_type='Custom::SelfSignedCertificateInternal'
        )
        self.internal_certificate.node.add_dependency(self.self_signed_certificate_lambda)

    def get_alb_listener_default_actions(self, listener_arn: str = None) -> List[elbv2.CfnListener.ActionProperty]:
        """
        ALB listener must be created with a default action.

        after the cluster stack is deployed, the virtual desktop controller stack will update the default action to point to dcv broker
        to avoid replacing the default action set for dcv broker, fetch the default actions if the listener exists.

        Similar is applicable for cluster manager, when cluster manager stack is deployed, it will update the default listener on
        external ALB to point to web portal.

        When cluster stack is updated or re-rerun, the listener exists,
        fetch the existing listener configuration and apply the config to the listener.

        ** Note **
        Currently, only target group forwarding is supported. Additional implementation is required to support
        other types of existing listener configurations.

        :param listener_arn:
        :return:
        """
        default_actions = None
        if Utils.is_not_empty(listener_arn):
            describe_listeners_result = self.context.aws().elbv2().describe_listeners(
                ListenerArns=[listener_arn]
            )
            existing_action = describe_listeners_result['Listeners'][0]['DefaultActions'][0]
            if existing_action['Type'] == 'forward':
                default_actions = [
                    elbv2.CfnListener.ActionProperty(
                        type='forward',
                        forward_config=elbv2.CfnListener.ForwardConfigProperty(
                            target_groups=[
                                elbv2.CfnListener.TargetGroupTupleProperty(
                                    target_group_arn=existing_action['TargetGroupArn']
                                )
                            ]
                        )
                    )
                ]
        if default_actions is None:
            default_actions = [
                elbv2.CfnListener.ActionProperty(
                    type='fixed-response',
                    fixed_response_config=elbv2.CfnListener.FixedResponseConfigProperty(
                        status_code='200',
                        content_type='application/json',
                        message_body=Utils.to_json({
                            'success': True,
                            'message': 'OK'
                        })
                    )
                )
            ]
        return default_actions

    def build_ec2_notification_module(self):
        self.ec2_events_sns_topic = SNSTopic(
            self.context, 'cluster-ec2-state-change-sns-topic', self.stack,
            display_name=f'{self.cluster_name}-{self.module_id}-ec2-state-change-sns-topic',
            topic_name=f'{self.cluster_name}-{self.module_id}-ec2-state-change-sns-topic',
            master_key=self.context.config().get_string('cluster.sns.kms_key_id')
        )
        self.add_common_tags(self.ec2_events_sns_topic)

        lambda_name = f'{self.module_id}-ec2state-event-transformer'
        ec2_state_event_transformation_lambda_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            assumed_by=['lambda'],
            description=f'{lambda_name}-role'
        )

        ec2_state_event_transformation_lambda_role.attach_inline_policy(Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='ec2state-event-transformer.yml'
        ))

        ec2_state_event_transformation_lambda = LambdaFunction(
            context=self.context,
            name=lambda_name,
            description=f'{self.module_id} lambda to intercept all ec2 state change events and transform to the required event object',
            scope=self.stack,
            environment={
                'IDEA_EC2_STATE_SNS_TOPIC_ARN': self.ec2_events_sns_topic.topic_arn,
                'IDEA_CLUSTER_NAME_TAG_KEY': constants.IDEA_TAG_ENVIRONMENT_NAME,
                'IDEA_CLUSTER_NAME_TAG_VALUE': self.context.cluster_name(),
                'IDEA_TAG_PREFIX': constants.IDEA_TAG_PREFIX
            },
            timeout_seconds=180,
            role=ec2_state_event_transformation_lambda_role,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_ec2_state_event_transformation_lambda',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            )
        )

        ec2_monitoring_rule = events.Rule(
            scope=self.stack,
            id=f'{self.cluster_name}-ec2-state-monitoring-rule',
            enabled=True,
            rule_name=f'{self.cluster_name}-{self.module_id}-ec2-state-monitoring-rule',
            description='Event Rule to monitor state changes on EC2 Instances',
            event_pattern=events.EventPattern(
                source=['aws.ec2'],
                detail_type=['EC2 Instance State-change Notification'],
                region=[self.aws_region]
            )
        )
        ec2_monitoring_rule.add_target(events_targets.LambdaFunction(
            ec2_state_event_transformation_lambda
        ))

    def build_cluster_endpoints(self):
        lambda_name = 'cluster-endpoints'

        cluster_endpoints_policy = Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='custom-resource-cluster-endpoints.yml'
        )
        cluster_endpoints_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            description=f'Role for cluster endpoints lambda function for Cluster: {self.cluster_name}',
            assumed_by=['lambda'])

        cluster_endpoints_role.attach_inline_policy(cluster_endpoints_policy)

        self.cluster_endpoints_lambda = LambdaFunction(
            context=self.context,
            name=lambda_name,
            scope=self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_custom_resource_cluster_endpoints',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            description='Manage cluster endpoints exposed via internal and external ALB',
            timeout_seconds=600,
            role=cluster_endpoints_role,
            log_retention_role=self.roles[app_constants.LOG_RETENTION_ROLE_NAME]
        )
        self.cluster_endpoints_lambda.node.add_dependency(cluster_endpoints_policy)
        self.cluster_endpoints_lambda.node.add_dependency(cluster_endpoints_role)

        # external ALB - can be deployed in public or private subnets
        is_public = self.context.config().get_bool('cluster.load_balancers.external_alb.public', default=True)
        external_alb_subnets = self.public_subnets(SubnetFilterKeys.LOAD_BALANCER_SUBNETS) if is_public is True else self.private_subnets(SubnetFilterKeys.LOAD_BALANCER_SUBNETS)
        self.external_alb = elbv2.ApplicationLoadBalancer(
            self.stack,
            f'{self.cluster_name}-external-alb',
            load_balancer_name=f'{self.cluster_name}-external-alb',
            security_group=self.security_groups['external-load-balancer'],
            http2_enabled=True,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=external_alb_subnets),
            internet_facing=is_public
        )
        if self.external_certificate is not None:
            self.external_alb.node.add_dependency(self.external_certificate)

        # internal ALB - will always be deployed in private subnets
        self.internal_alb = elbv2.ApplicationLoadBalancer(
            self.stack,
            f'{self.cluster_name}-internal-alb',
            load_balancer_name=f'{self.cluster_name}-internal-alb',
            security_group=self.security_groups['internal-load-balancer'],
            http2_enabled=True,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets()),
            internet_facing=False
        )

        # Manage Access Logs for external/internal Application Load Balancer
        # https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html
        external_alb_enable_access_log = self.context.config().get_bool('cluster.load_balancers.external_alb.access_logs', default=False)
        internal_alb_enable_access_log = self.context.config().get_bool('cluster.load_balancers.internal_alb.access_logs', default=False)

        cluster_s3_bucket = None
        if external_alb_enable_access_log or internal_alb_enable_access_log:
            cluster_s3_bucket = s3.Bucket.from_bucket_name(scope=self.stack, id='cluster-s3-bucket', bucket_name=self.context.config().get_string('cluster.cluster_s3_bucket', required=True))

        if external_alb_enable_access_log:
            self.external_alb.log_access_logs(cluster_s3_bucket, f'logs/{self.module_id}/alb-access-logs/external-alb')
        if internal_alb_enable_access_log:
            self.internal_alb.log_access_logs(cluster_s3_bucket, f'logs/{self.module_id}/alb-access-logs/internal-alb')

        # Drop invalid headers from requests to the ALB as a security measure
        self.external_alb.set_attribute('routing.http.drop_invalid_header_fields.enabled', 'true')
        self.internal_alb.set_attribute('routing.http.drop_invalid_header_fields.enabled', 'true')

        elbv2.CfnListener(
            self.external_alb,
            'http-listener',
            port=80,
            load_balancer_arn=self.external_alb.load_balancer_arn,
            protocol='HTTP',
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type='redirect',
                    redirect_config=elbv2.CfnListener.RedirectConfigProperty(
                        host='#{host}',
                        path='/#{path}',
                        port='443',
                        protocol='HTTPS',
                        query='#{query}',
                        status_code='HTTP_301'
                    )
                )
            ]
        )

        # ALB listener must be created with a default action.
        # after the cluster stack is deployed, the cluster manager stack can update the default action to point to web portal
        # to avoid replacing the default action set for web-portal, fetch the default actions if the listener exists
        external_alb_listener_arn = self.context.config().get_string('cluster.load_balancers.external_alb.https_listener_arn')
        external_alb_default_actions = self.get_alb_listener_default_actions(external_alb_listener_arn)

        if self.external_certificate is None:
            external_acm_certificate_arn = self.context.config().get_string('cluster.load_balancers.external_alb.certificates.acm_certificate_arn', required=True)
        else:
            external_acm_certificate_arn = self.external_certificate.get_att_string('acm_certificate_arn')

        self.external_alb_https_listener = elbv2.CfnListener(
            self.external_alb,
            'https-listener',
            port=443,
            ssl_policy=self.context.config().get_string('cluster.load_balancers.external_alb.ssl_policy', default='ELBSecurityPolicy-TLS13-1-2-2021-06'),
            load_balancer_arn=self.external_alb.load_balancer_arn,
            protocol='HTTPS',
            certificates=[
                elbv2.CfnListener.CertificateProperty(
                    certificate_arn=external_acm_certificate_arn
                )
            ],
            default_actions=external_alb_default_actions
        )
        if self.external_certificate is not None:
            self.external_alb_https_listener.node.add_dependency(self.external_certificate)

        self.internal_alb.node.add_dependency(self.internal_certificate)

        internal_acm_certificate_arn = self.internal_certificate.get_att_string('acm_certificate_arn')
        self.internal_alb_https_listener = elbv2.CfnListener(
            self.internal_alb,
            'https-listener',
            port=443,
            ssl_policy=self.context.config().get_string('cluster.load_balancers.internal_alb.ssl_policy', default='ELBSecurityPolicy-TLS13-1-2-2021-06'),
            load_balancer_arn=self.internal_alb.load_balancer_arn,
            protocol='HTTPS',
            certificates=[
                elbv2.CfnListener.CertificateProperty(
                    certificate_arn=internal_acm_certificate_arn
                )
            ],
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type='fixed-response',
                    fixed_response_config=elbv2.CfnListener.FixedResponseConfigProperty(
                        status_code='200',
                        content_type='application/json',
                        message_body=Utils.to_json({
                            'success': True,
                            'message': 'OK'
                        })
                    )
                )
            ]
        )
        self.internal_alb_https_listener.node.add_dependency(self.internal_certificate)
        if self.aws_region in Utils.get_value_as_list('ROUTE53_CROSS_ZONE_ALIAS_RESTRICTED_REGION_LIST', constants.CAVEATS, []):
            self.internal_alb_dns_record_set = route53.CnameRecord(
                self.stack,
                'internal-alb-dns-record',
                record_name=f'internal-alb.{self.private_hosted_zone.zone_name}',
                zone=self.private_hosted_zone,
                domain_name=self.internal_alb.load_balancer_dns_name,
                ttl=cdk.Duration.minutes(5)
            )
        else:
            self.internal_alb_dns_record_set = route53.RecordSet(
                self.stack,
                'internal-alb-dns-record',
                record_type=route53.RecordType.A,
                target=route53.RecordTarget.from_alias(route53_targets.LoadBalancerTarget(self.internal_alb)),
                ttl=cdk.Duration.minutes(5),
                record_name=f'internal-alb.{self.private_hosted_zone.zone_name}',
                zone=self.private_hosted_zone
            )

        if self.context.config().is_module_enabled(constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER):
            dcv_broker_client_listener_arn = self.context.config().get_string('cluster.external_alb.dcv_broker_client_listener_arn')
            dcv_broker_client_listener_default_actions = self.get_alb_listener_default_actions(dcv_broker_client_listener_arn)
            dcv_broker_client_communication_port = self.context.config().get_int('virtual-desktop-controller.dcv_broker.client_communication_port', required=True)
            self.internal_alb_dcv_broker_client_listener = elbv2.CfnListener(
                self.internal_alb,
                'dcv-broker-client-listener',
                port=dcv_broker_client_communication_port,
                ssl_policy=self.context.config().get_string('virtual-desktop-controller.dcv_broker.ssl_policy', default='ELBSecurityPolicy-TLS13-1-2-2021-06'),
                load_balancer_arn=self.internal_alb.load_balancer_arn,
                protocol='HTTPS',
                certificates=[
                    elbv2.CfnListener.CertificateProperty(
                        certificate_arn=internal_acm_certificate_arn
                    )
                ],
                default_actions=dcv_broker_client_listener_default_actions
            )
            self.internal_alb_dcv_broker_client_listener.node.add_dependency(self.internal_certificate)
            self.security_groups['internal-load-balancer'].add_ingress_rule(
                ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                ec2.Port.tcp(dcv_broker_client_communication_port),
                description='Allow HTTPS traffic from DCV Clients to DCV Broker'
            )

            dcv_broker_agent_listener_arn = self.context.config().get_string('cluster.external_alb.dcv_broker_agent_listener_arn')
            dcv_broker_agent_listener_default_actions = self.get_alb_listener_default_actions(dcv_broker_agent_listener_arn)
            dcv_broker_agent_communication_port = self.context.config().get_int('virtual-desktop-controller.dcv_broker.agent_communication_port', required=True)
            self.internal_alb_dcv_broker_agent_listener = elbv2.CfnListener(
                self.internal_alb,
                'dcv-broker-agent-listener',
                port=dcv_broker_agent_communication_port,
                ssl_policy=self.context.config().get_string('virtual-desktop-controller.dcv_broker.ssl_policy', default='ELBSecurityPolicy-TLS13-1-2-2021-06'),
                load_balancer_arn=self.internal_alb.load_balancer_arn,
                protocol='HTTPS',
                certificates=[
                    elbv2.CfnListener.CertificateProperty(
                        certificate_arn=internal_acm_certificate_arn
                    )
                ],
                default_actions=dcv_broker_agent_listener_default_actions
            )
            self.internal_alb_dcv_broker_agent_listener.node.add_dependency(self.internal_certificate)
            self.security_groups['internal-load-balancer'].add_ingress_rule(
                ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                ec2.Port.tcp(dcv_broker_agent_communication_port),
                description='Allow HTTPS traffic from DCV Agents to DCV Broker'
            )

            dcv_broker_gateway_listener_arn = self.context.config().get_string('cluster.external_alb.dcv_broker_gateway_listener_arn')
            dcv_broker_gateway_listener_default_actions = self.get_alb_listener_default_actions(dcv_broker_gateway_listener_arn)
            dcv_broker_gateway_communication_port = self.context.config().get_int('virtual-desktop-controller.dcv_broker.gateway_communication_port', required=True)
            self.internal_alb_dcv_broker_gateway_listener = elbv2.CfnListener(
                self.internal_alb,
                'dcv-broker-gateway-listener',
                port=dcv_broker_gateway_communication_port,
                ssl_policy=self.context.config().get_string('virtual-desktop-controller.dcv_broker.ssl_policy', default='ELBSecurityPolicy-TLS13-1-2-2021-06'),
                load_balancer_arn=self.internal_alb.load_balancer_arn,
                protocol='HTTPS',
                certificates=[
                    elbv2.CfnListener.CertificateProperty(
                        certificate_arn=internal_acm_certificate_arn
                    )
                ],

                default_actions=dcv_broker_gateway_listener_default_actions
            )
            self.internal_alb_dcv_broker_gateway_listener.node.add_dependency(self.internal_certificate)
            self.security_groups['internal-load-balancer'].add_ingress_rule(
                ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
                ec2.Port.tcp(dcv_broker_gateway_communication_port),
                description='Allow HTTPS traffic from DCV Connection Gateway to DCV Broker'
            )

    def build_cluster_settings(self):
        # cluster settings are applied in the current module_id scope. module_id should not be provided in the key for settings.
        cluster_settings = {
            'deployment_id': self.deployment_id,
            'network.vpc_id': self.vpc.vpc_id,
            'network.cluster_prefix_list_id': self.cluster_prefix_list.attr_prefix_list_id
        }

        public_subnets = self.context.config().get_list('cluster.network.public_subnets', [])
        is_external_alb_public = self.context.config().get_bool('cluster.load_balancers.external_alb.public', default=True)
        if Utils.is_empty(public_subnets):
            if is_external_alb_public:
                for subnet in self.vpc.public_subnets:
                    public_subnets.append(subnet.subnet_id)
        cluster_settings['network.public_subnets'] = public_subnets

        load_balancer_subnets = self.context.config().get_list("cluster.network.load_balancer_subnets", [])
        if Utils.is_not_empty(load_balancer_subnets):
            cluster_settings['network.load_balancer_subnets'] = load_balancer_subnets

        infrastructure_host_subnets = self.context.config().get_list("cluster.network.infrastructure_host_subnets", [])
        if Utils.is_not_empty(load_balancer_subnets):
            cluster_settings['network.infrastructure_host_subnets'] = infrastructure_host_subnets

        private_subnets = self.context.config().get_list('cluster.network.private_subnets', [])
        if Utils.is_empty(private_subnets):
            for subnet in self.vpc.private_subnets:
                private_subnets.append(subnet.subnet_id)
        cluster_settings['network.private_subnets'] = private_subnets

        if not self.context.config().get_bool('cluster.network.use_existing_vpc', False):
            cluster_settings['network.nat_gateway_ips'] = []
            for eip in self.vpc.nat_gateway_ips:
                cluster_settings['network.nat_gateway_ips'].append(f'{eip.ref}')

        # SecurityGroupIds
        for name, security_group in self.security_groups.items():
            cluster_settings[f'network.security_groups.{name}'] = security_group.security_group_id

        # RoleArns
        for name, role in self.roles.items():
            cluster_settings[f'iam.roles.{name}'] = role.role_arn
        # Policy Arns
        cluster_settings['iam.policies.amazon_ssm_managed_instance_core_arn'] = self.amazon_ssm_managed_instance_core_policy.managed_policy_arn
        cluster_settings['iam.policies.cloud_watch_agent_server_arn'] = self.cloud_watch_agent_server_policy.managed_policy_arn
        cluster_settings['iam.policies.dcv_host_role_managed_policy_arn'] = self.dcv_host_role_managed_policy.managed_policy_arn
        if self.amazon_prometheus_remote_write_policy is not None:
            cluster_settings['iam.policies.amazon_prometheus_remote_write_arn'] = self.amazon_prometheus_remote_write_policy.managed_policy_arn

        cluster_settings['solution.solution_metrics_lambda_arn'] = self.solution_metrics_lambda.function_arn
        cluster_settings['cluster_settings_lambda_arn'] = self.cluster_settings_lambda.function_arn
        cluster_settings['self_signed_certificate_lambda_arn'] = self.self_signed_certificate_lambda.function_arn

        # route53 - private hosted zone settings
        cluster_settings['route53.private_hosted_zone_id'] = self.private_hosted_zone.hosted_zone_id
        cluster_settings['route53.private_hosted_zone_arn'] = self.private_hosted_zone.hosted_zone_arn

        # certificates
        if not self.context.config().get_bool('cluster.load_balancers.external_alb.certificates.provided', required=True):
            cluster_settings['load_balancers.external_alb.certificates.certificate_secret_arn'] = self.external_certificate.get_att_string('certificate_secret_arn')
            cluster_settings['load_balancers.external_alb.certificates.private_key_secret_arn'] = self.external_certificate.get_att_string('private_key_secret_arn')
            cluster_settings['load_balancers.external_alb.certificates.acm_certificate_arn'] = self.external_certificate.get_att_string('acm_certificate_arn')
        else:
            cluster_settings['load_balancers.external_alb.certificates.provided'] = self.context.config().get_string('cluster.load_balancers.external_alb.certificates.provided', required=True)
            cluster_settings['load_balancers.external_alb.certificates.acm_certificate_arn'] = self.context.config().get_string('cluster.load_balancers.external_alb.certificates.acm_certificate_arn', required=True)

        cluster_settings['load_balancers.internal_alb.certificates.certificate_secret_arn'] = self.internal_certificate.get_att_string('certificate_secret_arn')
        cluster_settings['load_balancers.internal_alb.certificates.private_key_secret_arn'] = self.internal_certificate.get_att_string('private_key_secret_arn')
        cluster_settings['load_balancers.internal_alb.certificates.acm_certificate_arn'] = self.internal_certificate.get_att_string('acm_certificate_arn')
        cluster_settings['load_balancers.internal_alb.certificates.custom_dns_name'] = f'internal-alb.{self.private_hosted_zone.zone_name}'

        # cluster endpoints
        cluster_settings['cluster_endpoints_lambda_arn'] = self.cluster_endpoints_lambda.function_arn
        cluster_settings['load_balancers.external_alb.load_balancer_arn'] = self.external_alb.load_balancer_arn
        cluster_settings['load_balancers.external_alb.load_balancer_dns_name'] = self.external_alb.load_balancer_dns_name
        cluster_settings['load_balancers.external_alb.https_listener_arn'] = self.external_alb_https_listener.attr_listener_arn

        cluster_settings['load_balancers.internal_alb.load_balancer_arn'] = self.internal_alb.load_balancer_arn
        cluster_settings['load_balancers.internal_alb.load_balancer_dns_name'] = self.internal_alb.load_balancer_dns_name
        cluster_settings['load_balancers.internal_alb.https_listener_arn'] = self.internal_alb_https_listener.attr_listener_arn

        cluster_settings['ec2.state_change_notifications_sns_topic_arn'] = self.ec2_events_sns_topic.topic_arn
        cluster_settings['ec2.state_change_notifications_sns_topic_name'] = self.ec2_events_sns_topic.topic_name

        if self.internal_alb_dcv_broker_client_listener:
            cluster_settings['load_balancers.internal_alb.dcv_broker_client_listener_arn'] = self.internal_alb_dcv_broker_client_listener.attr_listener_arn
        if self.internal_alb_dcv_broker_agent_listener:
            cluster_settings['load_balancers.internal_alb.dcv_broker_agent_listener_arn'] = self.internal_alb_dcv_broker_agent_listener.attr_listener_arn
        if self.internal_alb_dcv_broker_gateway_listener:
            cluster_settings['load_balancers.internal_alb.dcv_broker_gateway_listener_arn'] = self.internal_alb_dcv_broker_gateway_listener.attr_listener_arn

        # vpc interface endpoints endpoint_url configuration
        # vpc interface endpoint url will be updated only once during provisioning.
        # if admin has updated the configuration, the endpoint_url for the endpoint will not be updated.
        # gateway endpoints do not need any additional configuration as traffic to applicable services will be routed automatically once provisioned
        if self.vpc_interface_endpoints is not None:
            for service in self.vpc_interface_endpoints:
                endpoint_config_key = f'network.vpc_interface_endpoints.{service}.endpoint_url'
                existing_endpoint_url = self.context.config().get_string(f'cluster.{endpoint_config_key}')
                if Utils.is_empty(existing_endpoint_url):
                    endpoint = self.vpc_interface_endpoints[service]
                    cluster_settings[endpoint_config_key] = endpoint.get_endpoint_url()
                else:
                    cluster_settings[endpoint_config_key] = existing_endpoint_url

        # backups
        if self.context.config().get_bool('cluster.backups.enabled', default=False):
            cluster_settings['backups.role_arn'] = self.backup_role.role_arn
            cluster_settings['backups.backup_vault.arn'] = self.backup_vault.backup_vault_arn
            cluster_settings['backups.backup_plan.arn'] = self.backup_plan.get_backup_plan_arn()

        cdk.CustomResource(
            self.stack,
            f'{self.cluster_name}-{self.module_id}-settings',
            service_token=self.cluster_settings_lambda.function_arn,
            properties={
                'cluster_name': self.cluster_name,
                'module_id': self.module_id,
                'version': self.release_version,
                'settings': cluster_settings
            },
            resource_type='Custom::ClusterSettings'
        )
