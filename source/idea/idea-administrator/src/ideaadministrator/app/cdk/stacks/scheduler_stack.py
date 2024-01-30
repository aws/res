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

from ideadatamodel import (
    constants,
    SocaAnyPayload
)
from ideasdk.bootstrap import BootstrapUserDataBuilder
from ideasdk.utils import Utils

import ideaadministrator
from ideaadministrator.app.cdk.constructs import (
    ExistingSocaCluster,
    OAuthClientIdAndSecret,
    SQSQueue,
    Policy,
    Role,
    InstanceProfile,
    ComputeNodeSecurityGroup,
    SchedulerSecurityGroup,
    IdeaNagSuppression
)
from ideaadministrator.app.cdk.stacks import IdeaBaseStack

from typing import Optional

import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_cognito as cognito,
    aws_sqs as sqs,
    aws_route53 as route53,
    aws_elasticloadbalancingv2 as elbv2,
    aws_kms as kms
)


class SchedulerStack(IdeaBaseStack):
    """
    Scheduler Stack

    Provisions infrastructure for Scale-Out Computing on AWS / HPC Scheduler module.
    """

    def __init__(self, scope: constructs.Construct,
                 cluster_name: str,
                 aws_region: str,
                 aws_profile: str,
                 module_id: str,
                 deployment_id: str,
                 termination_protection: bool = True,
                 env: cdk.Environment = None):

        super().__init__(
            scope=scope,
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            module_id=module_id,
            deployment_id=deployment_id,
            termination_protection=termination_protection,
            description=f'ModuleId: {module_id}, Cluster: {cluster_name}, Version: {ideaadministrator.props.current_release_version}',
            tags={
                constants.IDEA_TAG_MODULE_ID: module_id,
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_SCHEDULER,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.bootstrap_package_uri = self.stack.node.try_get_context('bootstrap_package_uri')
        self.cluster = ExistingSocaCluster(self.context, self.stack)

        self.oauth2_client_secret: Optional[OAuthClientIdAndSecret] = None
        self.scheduler_role: Optional[Role] = None
        self.scheduler_instance_profile: Optional[InstanceProfile] = None
        self.compute_node_role: Optional[Role] = None
        self.compute_node_instance_profile: Optional[InstanceProfile] = None
        self.spot_fleet_request_role: Optional[Role] = None
        self.scheduler_security_group: Optional[SchedulerSecurityGroup] = None
        self.compute_node_security_group: Optional[ComputeNodeSecurityGroup] = None
        self.job_status_sqs_queue: Optional[SQSQueue] = None
        self.ec2_instance: Optional[ec2.CfnInstance] = None
        self.cluster_dns_record_set: Optional[route53.RecordSet] = None
        self.external_endpoint: Optional[cdk.CustomResource] = None
        self.internal_endpoint: Optional[cdk.CustomResource] = None

        self.user_pool = self.lookup_user_pool()

        self.build_oauth2_client()
        self.build_sqs_queue()
        self.build_iam_roles()
        self.build_security_groups()
        self.build_ec2_instance()
        self.build_route53_record_set()
        self.build_endpoints()
        self.build_cluster_settings()

    def build_oauth2_client(self):
        # add resource server
        resource_server = self.user_pool.add_resource_server(
            id='resource-server',
            identifier=self.module_id,
            scopes=[
                cognito.ResourceServerScope(scope_name='read', scope_description='Allow Read Access'),
                cognito.ResourceServerScope(scope_name='write', scope_description='Allow Write Access')
            ]
        )

        # add new client to user pool
        client = self.user_pool.add_client(
            id=f'{self.module_id}-client',
            access_token_validity=cdk.Duration.hours(1),
            generate_secret=True,
            id_token_validity=cdk.Duration.hours(1),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(client_credentials=True),
                scopes=[
                    cognito.OAuthScope.custom(f'{self.module_id}/read'),
                    cognito.OAuthScope.custom(f'{self.module_id}/write'),
                    cognito.OAuthScope.custom(f'{self.context.config().get_module_id(constants.MODULE_CLUSTER_MANAGER)}/read')
                ]
            ),
            refresh_token_validity=cdk.Duration.days(30),
            user_pool_client_name=self.module_id
        )
        client.node.add_dependency(resource_server)

        # read secret value by invoking custom resource
        oauth_credentials_lambda_arn = self.context.config().get_string('identity-provider.cognito.oauth_credentials_lambda_arn', required=True)
        client_secret = cdk.CustomResource(
            scope=self.stack,
            id=f'{self.module_id}-creds',
            service_token=oauth_credentials_lambda_arn,
            properties={
                'UserPoolId': self.user_pool.user_pool_id,
                'ClientId': client.user_pool_client_id
            },
            resource_type='Custom::GetOAuthCredentials'
        )

        # save client id and client secret to AWS Secrets Manager
        self.oauth2_client_secret = OAuthClientIdAndSecret(
            context=self.context,
            secret_name_prefix=self.module_id,
            module_name=constants.MODULE_SCHEDULER,
            scope=self.stack,
            client_id=client.user_pool_client_id,
            client_secret=client_secret.get_att_string('ClientSecret')
        )

    def build_iam_roles(self):

        ec2_managed_policies = self.get_ec2_instance_managed_policies()

        # scheduler
        scheduler_policy_arns = self.context.config().get_list('cluster.iam.scheduler_iam_policy_arns', [])
        scheduler_policy_arns += ec2_managed_policies
        scheduler_policy_arns = list(set(scheduler_policy_arns))
        self.scheduler_role = Role(
            context=self.context,
            name=f'{self.module_id}-role',
            scope=self.stack,
            description='IAM role assigned to the scheduler',
            assumed_by=['ssm', 'ec2'],
            managed_policies=scheduler_policy_arns
        )
        self.scheduler_instance_profile = InstanceProfile(
            context=self.context,
            name=f'{self.module_id}-scheduler-instance-profile',
            scope=self.stack,
            roles=[self.scheduler_role]
        )

        # compute node
        compute_node_policy_arns = self.context.config().get_list('cluster.iam.compute_node_iam_policy_arns', [])
        compute_node_policy_arns += ec2_managed_policies
        compute_node_policy_arns = list(set(compute_node_policy_arns))
        self.compute_node_role = Role(
            context=self.context,
            name=f'{self.module_id}-compute-node-role',
            scope=self.stack,
            description='IAM role assigned to the compute nodes',
            assumed_by=['ssm', 'ec2'],
            managed_policies=compute_node_policy_arns
        )
        self.compute_node_instance_profile = InstanceProfile(
            context=self.context,
            name=f'{self.module_id}-compute-node-instance-profile',
            scope=self.stack,
            roles=[self.compute_node_role]
        )

        # spot fleet request
        self.spot_fleet_request_role = Role(
            context=self.context,
            name=f'{self.module_id}-spot-fleet-request-role',
            scope=self.stack,
            description='IAM role to manage SpotFleet requests',
            assumed_by=['spotfleet']
        )

        variables = SocaAnyPayload()
        variables.scheduler_role_arn = self.scheduler_role.role_arn
        variables.compute_node_role_arn = self.compute_node_role.role_arn
        variables.spot_fleet_request_role_arn = self.spot_fleet_request_role.role_arn

        self.scheduler_role.attach_inline_policy(
            Policy(
                context=self.context,
                name='scheduler-policy',
                scope=self.stack,
                policy_template_name='scheduler.yml',
                vars=variables,
                module_id=self.module_id
            )
        )
        self.compute_node_role.attach_inline_policy(
            Policy(
                context=self.context,
                name='compute-node-policy',
                scope=self.stack,
                policy_template_name='compute-node.yml',
                vars=variables,
                module_id=self.module_id
            )
        )
        self.spot_fleet_request_role.attach_inline_policy(
            Policy(
                context=self.context,
                name='spot-fleet-policy',
                scope=self.stack,
                policy_template_name='spot-fleet-request.yml',
                vars=variables,
                module_id=self.module_id
            )
        )

    def build_sqs_queue(self):
        kms_key_id = self.context.config().get_string('cluster.sqs.kms_key_id')

        self.job_status_sqs_queue = SQSQueue(
            self.context, 'job-status-events', self.stack,
            queue_name=f'{self.cluster_name}-{self.module_id}-job-status-events',
            encryption_master_key=kms_key_id,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=10,
                queue=SQSQueue(
                    self.context, 'job-status-events-dlq', self.stack,
                    queue_name=f'{self.cluster_name}-{self.module_id}-job-status-events-dlq',
                    encryption_master_key=kms_key_id,
                    is_dead_letter_queue=True
                )
            )
        )
        self.add_common_tags(self.job_status_sqs_queue)
        self.add_common_tags(self.job_status_sqs_queue.dead_letter_queue.queue)

    def build_security_groups(self):
        self.scheduler_security_group = SchedulerSecurityGroup(
            context=self.context,
            name=f'{self.module_id}-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc,
            bastion_host_security_group=self.cluster.get_security_group('bastion-host'),
            loadbalancer_security_group=self.cluster.get_security_group('external-load-balancer')
        )

        self.compute_node_security_group = ComputeNodeSecurityGroup(
            context=self.context,
            name=f'{self.module_id}-compute-node-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc
        )

    def build_ec2_instance(self):

        is_public = self.context.config().get_bool('scheduler.public', False)
        base_os = self.context.config().get_string('scheduler.base_os', required=True)
        instance_ami = self.context.config().get_string('scheduler.instance_ami', required=True)
        instance_type = self.context.config().get_string('scheduler.instance_type', required=True)
        volume_size = self.context.config().get_int('scheduler.volume_size', 200)
        key_pair_name = self.context.config().get_string('cluster.network.ssh_key_pair', required=True)
        enable_detailed_monitoring = self.context.config().get_bool('scheduler.ec2.enable_detailed_monitoring', default=False)
        enable_termination_protection = self.context.config().get_bool('scheduler.ec2.enable_termination_protection', default=False)
        metadata_http_tokens = self.context.config().get_string('scheduler.ec2.metadata_http_tokens', required=True)
        https_proxy = self.context.config().get_string('cluster.network.https_proxy', required=False, default='')
        no_proxy = self.context.config().get_string('cluster.network.no_proxy', required=False, default='')
        proxy_config = {}
        if Utils.is_not_empty(https_proxy):
            proxy_config = {
                    'http_proxy': https_proxy,
                    'https_proxy': https_proxy,
                    'no_proxy': no_proxy
                    }
        kms_key_id = self.context.config().get_string('cluster.ebs.kms_key_id', required=False, default=None)
        if kms_key_id is not None:
             kms_key_arn = self.get_kms_key_arn(kms_key_id)
             ebs_kms_key = kms.Key.from_key_arn(scope=self.stack, id=f'ebs-kms-key', key_arn=kms_key_arn)
        else:
             ebs_kms_key = kms.Alias.from_alias_name(scope=self.stack, id=f'ebs-kms-key-default', alias_name='alias/aws/ebs')

        if is_public and len(self.cluster.public_subnets) > 0:
            subnet_ids = self.cluster.existing_vpc.get_public_subnet_ids()
        else:
            subnet_ids = self.cluster.existing_vpc.get_private_subnet_ids()

        block_device_name = Utils.get_ec2_block_device_name(base_os)

        user_data = BootstrapUserDataBuilder(
            aws_region=self.aws_region,
            bootstrap_package_uri=self.bootstrap_package_uri,
            install_commands=[
                '/bin/bash scheduler/setup.sh'
            ],
            proxy_config=proxy_config,
            base_os=base_os
        ).build()

        launch_template = ec2.LaunchTemplate(
            self.stack, f'{self.module_id}-lt',
            instance_type=ec2.InstanceType(instance_type),
            machine_image=ec2.MachineImage.generic_linux({
                self.aws_region: instance_ami
            }),
            user_data=ec2.UserData.custom(cdk.Fn.sub(user_data)),
            key_name=key_pair_name,
            block_devices=[ec2.BlockDevice(
                device_name=block_device_name,
                volume=ec2.BlockDeviceVolume(ebs_device=ec2.EbsDeviceProps(
                    encrypted=True,
                    kms_key=ebs_kms_key,
                    volume_size=volume_size,
                    volume_type=ec2.EbsDeviceVolumeType.GP3
                    )
                )
            )],
            require_imdsv2=True if metadata_http_tokens == "required" else False
            )

        self.ec2_instance = ec2.CfnInstance(
            self.stack,
            f'{self.module_id}-instance',
            block_device_mappings=[
                ec2.CfnInstance.BlockDeviceMappingProperty(
                    device_name=block_device_name,
                    ebs=ec2.CfnInstance.EbsProperty(
                        volume_size=volume_size,
                        volume_type='gp3'
                    )
                )
            ],
            disable_api_termination=enable_termination_protection,
            iam_instance_profile=self.scheduler_instance_profile.instance_profile_name,
            instance_type=instance_type,
            image_id=instance_ami,
            key_name=key_pair_name,
            launch_template=ec2.CfnInstance.LaunchTemplateSpecificationProperty(
                version=launch_template.latest_version_number,
                launch_template_id=launch_template.launch_template_id),
            network_interfaces=[
                ec2.CfnInstance.NetworkInterfaceProperty(
                    device_index='0',
                    associate_public_ip_address=is_public,
                    group_set=[self.scheduler_security_group.security_group_id],
                    subnet_id=subnet_ids[0],
                )
            ],
            user_data=cdk.Fn.base64(cdk.Fn.sub(user_data)),
            monitoring=enable_detailed_monitoring
        )
        cdk.Tags.of(self.ec2_instance).add('Name', self.build_resource_name(self.module_id))
        cdk.Tags.of(self.ec2_instance).add(constants.IDEA_TAG_NODE_TYPE, constants.NODE_TYPE_APP)
        self.add_backup_tags(self.ec2_instance)

        if not enable_detailed_monitoring:
            self.add_nag_suppression(
                construct=self.ec2_instance,
                suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-EC28', reason='detailed monitoring is a configurable option to save costs')]
            )

        if not enable_termination_protection:
            self.add_nag_suppression(
                construct=self.ec2_instance,
                suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-EC29', reason='termination protection not supported in CDK L2 construct. enable termination protection via AWS EC2 console after deploying the cluster.')]
            )

    def build_route53_record_set(self):
        hostname = self.context.config().get_string('scheduler.hostname', required=True)
        private_hosted_zone_id = self.context.config().get_string('cluster.route53.private_hosted_zone_id', required=True)
        private_hosted_zone_name = self.context.config().get_string('cluster.route53.private_hosted_zone_name', required=True)
        self.cluster_dns_record_set = route53.RecordSet(
            self.stack,
            f'{self.module_id}-dns-record',
            record_type=route53.RecordType.A,
            target=route53.RecordTarget.from_ip_addresses(self.ec2_instance.attr_private_ip),
            ttl=cdk.Duration.minutes(5),
            record_name=hostname,
            zone=route53.HostedZone.from_hosted_zone_attributes(
                scope=self.stack,
                id='cluster-dns',
                hosted_zone_id=private_hosted_zone_id,
                zone_name=private_hosted_zone_name
            )
        )

    def build_endpoints(self):
        external_target_group = elbv2.CfnTargetGroup(
            self.stack,
            f'{self.module_id}-external-target-group',
            port=8443,
            protocol='HTTPS',
            target_type='ip',
            vpc_id=self.cluster.vpc.vpc_id,
            name=self.get_target_group_name('sched-ext'),
            targets=[elbv2.CfnTargetGroup.TargetDescriptionProperty(
                id=self.ec2_instance.attr_private_ip
            )],
            health_check_path='/healthcheck'
        )
        cluster_endpoints_lambda_arn = self.context.config().get_string('cluster.cluster_endpoints_lambda_arn', required=True)
        external_https_listener_arn = self.context.config().get_string('cluster.load_balancers.external_alb.https_listener_arn', required=True)
        external_endpoint_priority = self.context.config().get_int('scheduler.endpoints.external.priority', required=True)
        external_endpoint_path_patterns = self.context.config().get_list('scheduler.endpoints.external.path_patterns', required=True)

        self.external_endpoint = cdk.CustomResource(
            self.stack,
            'external-endpoint',
            service_token=cluster_endpoints_lambda_arn,
            properties={
                'endpoint_name': f'{self.module_id}-external-endpoint',
                'listener_arn': external_https_listener_arn,
                'priority': external_endpoint_priority,
                'target_group_arn': external_target_group.ref,
                'conditions': [
                    {
                        'Field': 'path-pattern',
                        'Values': external_endpoint_path_patterns
                    }
                ],
                'actions': [
                    {
                        'Type': 'forward',
                        'TargetGroupArn': external_target_group.ref
                    }
                ],
                'tags': {
                    constants.IDEA_TAG_ENVIRONMENT_NAME: self.cluster_name,
                    constants.IDEA_TAG_MODULE_ID: self.module_id,
                    constants.IDEA_TAG_MODULE_NAME: constants.MODULE_SCHEDULER
                }
            },
            resource_type='Custom::SchedulerEndpointExternal'
        )

        internal_https_listener_arn = self.context.config().get_string('cluster.load_balancers.internal_alb.https_listener_arn',
                                                                       required=True)
        internal_endpoint_priority = self.context.config().get_int('scheduler.endpoints.internal.priority', required=True)
        internal_endpoint_path_patterns = self.context.config().get_list('scheduler.endpoints.internal.path_patterns', required=True)

        internal_target_group = elbv2.CfnTargetGroup(
            self.stack,
            f'{self.module_id}-internal-target-group',
            port=8443,
            protocol='HTTPS',
            target_type='ip',
            vpc_id=self.cluster.vpc.vpc_id,
            name=self.get_target_group_name('sched-int'),
            targets=[elbv2.CfnTargetGroup.TargetDescriptionProperty(
                id=self.ec2_instance.attr_private_ip
            )],
            health_check_path='/healthcheck'
        )

        self.internal_endpoint = cdk.CustomResource(
            self.stack,
            'internal-endpoint',
            service_token=cluster_endpoints_lambda_arn,
            properties={
                'endpoint_name': f'{self.module_id}-internal-endpoint',
                'listener_arn': internal_https_listener_arn,
                'priority': internal_endpoint_priority,
                'target_group_arn': internal_target_group.ref,
                'conditions': [
                    {
                        'Field': 'path-pattern',
                        'Values': internal_endpoint_path_patterns
                    }
                ],
                'actions': [
                    {
                        'Type': 'forward',
                        'TargetGroupArn': internal_target_group.ref
                    }
                ],
                'tags': {
                    constants.IDEA_TAG_ENVIRONMENT_NAME: self.cluster_name,
                    constants.IDEA_TAG_MODULE_ID: self.module_id,
                    constants.IDEA_TAG_MODULE_NAME: constants.MODULE_SCHEDULER
                }
            },
            resource_type='Custom::SchedulerEndpointInternal'
        )

    def build_cluster_settings(self):
        cluster_settings = {}
        cluster_settings['deployment_id'] = self.deployment_id
        cluster_settings['private_ip'] = self.ec2_instance.attr_private_ip
        cluster_settings['private_dns_name'] = self.ec2_instance.attr_private_dns_name

        is_public = self.context.config().get_bool('scheduler.public', False)
        if is_public:
            cluster_settings['public_ip'] = self.ec2_instance.attr_public_ip
        cluster_settings['instance_id'] = self.ec2_instance.ref
        cluster_settings['client_id'] = self.oauth2_client_secret.client_id.ref
        cluster_settings['client_secret'] = self.oauth2_client_secret.client_secret.ref
        cluster_settings['security_group_id'] = self.scheduler_security_group.security_group_id
        cluster_settings['iam_role_arn'] = self.scheduler_role.role_arn
        cluster_settings['compute_node_security_group_ids'] = [self.compute_node_security_group.security_group_id]
        cluster_settings['compute_node_iam_role_arn'] = self.compute_node_role.role_arn
        cluster_settings['compute_node_instance_profile_arn'] = self.compute_node_instance_profile.ref
        cluster_settings['spot_fleet_request_iam_role_arn'] = self.spot_fleet_request_role.role_arn
        cluster_settings['job_status_sqs_queue_url'] = self.job_status_sqs_queue.queue_url

        self.update_cluster_settings(cluster_settings)
