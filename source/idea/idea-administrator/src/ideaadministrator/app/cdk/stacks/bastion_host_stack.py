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
    constants
)
from ideasdk.bootstrap import BootstrapUserDataBuilder
from ideasdk.utils import Utils

import ideaadministrator
from ideaadministrator.app.cdk.stacks import IdeaBaseStack
from ideaadministrator.app.cdk.constructs import (
    ExistingSocaCluster,
    InstanceProfile,
    IdeaNagSuppression,
    Role,
    Policy
)

from typing import Optional
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_route53 as route53,
    aws_kms as kms
)
import constructs


class BastionHostStack(IdeaBaseStack):
    """
    Bastion Host Stack
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
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_BASTION_HOST,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.bootstrap_package_uri = self.stack.node.try_get_context('bootstrap_package_uri')

        self.cluster = ExistingSocaCluster(self.context, self.stack)
        self.bastion_host_role: Optional[Role] = None
        self.bastion_host_instance_profile: Optional[InstanceProfile] = None
        self.ec2_instance: Optional[ec2.Instance] = None
        self.cluster_dns_record_set: Optional[route53.RecordSet] = None

        self.build_iam_roles()
        self.build_ec2_instance()
        self.build_route53_record_set()
        self.build_cluster_settings()

    def build_iam_roles(self):

        ec2_managed_policies = self.get_ec2_instance_managed_policies()

        self.bastion_host_role = Role(
            context=self.context,
            name=f'{self.module_id}-role',
            scope=self.stack,
            description='IAM role assigned to the bastion-host',
            assumed_by=['ssm', 'ec2'],
            managed_policies=ec2_managed_policies
        )
        self.bastion_host_role.attach_inline_policy(
            Policy(
                context=self.context,
                name='bastion-host-policy',
                scope=self.stack,
                policy_template_name='bastion-host.yml'
            )
        )
        self.bastion_host_instance_profile = InstanceProfile(
            context=self.context,
            name=f'{self.module_id}-instance-profile',
            scope=self.stack,
            roles=[self.bastion_host_role]
        )
        # Make sure the role exists before trying to create the instance profile
        self.bastion_host_instance_profile.node.add_dependency(self.bastion_host_role)

    def build_ec2_instance(self):

        is_public = self.context.config().get_bool('bastion-host.public', default=False)
        base_os = self.context.config().get_string('bastion-host.base_os', required=True)
        instance_ami = self.context.config().get_string('bastion-host.instance_ami', required=True)
        instance_type = self.context.config().get_string('bastion-host.instance_type', required=True)
        volume_size = self.context.config().get_int('bastion-host.volume_size', default=200)
        key_pair_name = self.context.config().get_string('cluster.network.ssh_key_pair', required=True)
        enable_detailed_monitoring = self.context.config().get_bool('bastion-host.ec2.enable_detailed_monitoring', default=False)
        enable_termination_protection = self.context.config().get_bool('bastion-host.ec2.enable_termination_protection', default=False)
        metadata_http_tokens = self.context.config().get_string('bastion-host.ec2.metadata_http_tokens', required=True)
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

        instance_profile_name = self.bastion_host_instance_profile.instance_profile_name
        security_group = self.cluster.get_security_group(constants.MODULE_BASTION_HOST)

        if is_public and len(self.cluster.public_subnets) > 0:
            subnet_ids = self.cluster.existing_vpc.get_public_subnet_ids()
        else:
            subnet_ids = self.cluster.existing_vpc.get_private_subnet_ids()

        block_device_name = Utils.get_ec2_block_device_name(base_os)

        user_data = BootstrapUserDataBuilder(
            aws_region=self.aws_region,
            bootstrap_package_uri=self.bootstrap_package_uri,
            install_commands=[
                '/bin/bash bastion-host/setup.sh'
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
                        encrypted=True,
                        volume_size=volume_size,
                        volume_type='gp3'
                    )
                )
            ],
            disable_api_termination=enable_termination_protection,
            iam_instance_profile=instance_profile_name,
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
                    group_set=[security_group.security_group_id],
                    subnet_id=subnet_ids[0],
                )
            ],
            user_data=cdk.Fn.base64(cdk.Fn.sub(user_data)),
            monitoring=enable_detailed_monitoring
        )
        cdk.Tags.of(self.ec2_instance).add('Name', self.build_resource_name(self.module_id))
        cdk.Tags.of(self.ec2_instance).add(constants.IDEA_TAG_NODE_TYPE, constants.NODE_TYPE_INFRA)
        self.add_backup_tags(self.ec2_instance)
        self.ec2_instance.node.add_dependency(self.bastion_host_instance_profile)

        if not enable_detailed_monitoring:
            self.add_nag_suppression(
                construct=self.ec2_instance,
                suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-EC28', reason='Detailed monitoring is a configurable option to save costs.')]
            )

        if not enable_termination_protection:
            self.add_nag_suppression(
                construct=self.ec2_instance,
                suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-EC29', reason='termination protection is a configurable option. Enable termination protection via AWS EC2 console after deploying the cluster if required.')]
            )

    def build_route53_record_set(self):
        hostname = self.context.config().get_string('bastion-host.hostname', required=True)
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

    def build_cluster_settings(self):

        cluster_settings = {}  # noqa
        cluster_settings['deployment_id'] = self.deployment_id
        cluster_settings['private_ip'] = self.ec2_instance.attr_private_ip
        cluster_settings['private_dns_name'] = self.ec2_instance.attr_private_dns_name

        is_public = self.context.config().get_bool('bastion-host.public', False)
        if is_public:
            cluster_settings['public_ip'] = self.ec2_instance.attr_public_ip
        cluster_settings['instance_id'] = self.ec2_instance.ref
        cluster_settings['iam_role_arn'] = self.bastion_host_role.role_arn
        cluster_settings['instance_profile_arn'] = self.bastion_host_instance_profile.ref

        self.update_cluster_settings(cluster_settings)
