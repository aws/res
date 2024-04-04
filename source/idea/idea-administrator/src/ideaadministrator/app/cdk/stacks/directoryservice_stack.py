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
    Role,
    Policy,
    InstanceProfile,
    OpenLDAPServerSecurityGroup,
    DirectoryServiceCredentials,
    ActiveDirectory,
    SQSQueue,
    IdeaNagSuppression
)
from typing import Optional
import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_route53 as route53,
    aws_sqs as sqs,
    aws_kms as kms
)
import constructs


class DirectoryServiceStack(IdeaBaseStack):
    """
    Directory Service Stack

    Based on directory service provider, provisions one of:
    1. OpenLDAP Server
    2. Microsoft AD
        a) AWS Managed Microsoft AD (if new)
        b) Infrastructure for AD Automation (SQS Queue)
    3. Secrets for OpenLDAP Root Account or AD Service Account (if not secret ARNs are not provided)
    4. Applicable cluster settings
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
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_DIRECTORYSERVICE,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.cluster = ExistingSocaCluster(self.context, self.stack)

        self.bootstrap_package_uri: Optional[str] = None
        self.openldap_role: Optional[Role] = None
        self.openldap_instance_profile: Optional[InstanceProfile] = None
        self.openldap_security_group: Optional[OpenLDAPServerSecurityGroup] = None
        self.openldap_certs: Optional[cdk.CustomResource] = None
        self.openldap_ec2_instance: Optional[ec2.CfnInstance] = None
        self.openldap_cluster_dns_record_set: Optional[route53.RecordSet] = None
        self.openldap_credentials: Optional[DirectoryServiceCredentials] = None

        self.activedirectory: Optional[ActiveDirectory] = None

        self.ad_automation_sqs_queue: Optional[SQSQueue] = None

        provider = self.context.config().get_string('directoryservice.provider', required=True)
        if provider == constants.DIRECTORYSERVICE_OPENLDAP:

            root_credentials_provided = self.context.config().get_bool('directoryservice.root_credentials_provided', default=False)
            if root_credentials_provided:
                root_username_secret_arn = self.context.config().get_string('directoryservice.root_username_secret_arn')
                assert Utils.is_not_empty(root_username_secret_arn)
                root_password_secret_arn = self.context.config().get_string('directoryservice.root_password_secret_arn')
                assert Utils.is_not_empty(root_password_secret_arn)

            self.bootstrap_package_uri = self.stack.node.try_get_context('bootstrap_package_uri')
            self.openldap_credentials = DirectoryServiceCredentials(
                context=self.context,
                name=f'{self.module_id}-openldap-credentials',
                scope=self.stack,
                admin_username='Admin'
            )
            self.build_iam_roles()
            self.build_security_groups()
            self.build_openldap_certs()
            self.build_ec2_instance()
            self.build_route53_record_set()
            self.build_openldap_cluster_settings()

        elif provider == constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY:

            root_credentials_provided = self.context.config().get_bool('directoryservice.root_credentials_provided', default=False)
            if root_credentials_provided:
                root_username_secret_arn = self.context.config().get_string('directoryservice.root_username_secret_arn')
                assert Utils.is_not_empty(root_username_secret_arn)
                root_password_secret_arn = self.context.config().get_string('directoryservice.root_password_secret_arn')
                assert Utils.is_not_empty(root_password_secret_arn)

            use_existing = self.context.config().get_bool('directoryservice.use_existing', default=False)
            if use_existing:
                directory_id = self.context.config().get_string('directoryservice.directory_id')
                assert Utils.is_not_empty(directory_id)
            else:
                self.activedirectory = ActiveDirectory(
                    context=self.context,
                    name='active-directory',
                    scope=self.stack,
                    cluster=self.cluster,
                    enable_sso=False
                )
            self.build_ad_automation_sqs_queue()
            self.build_aws_managed_ad_cluster_settings()

        # ActiveDirectory that is self-managed
        # Additional configuration is required to bootstrap a clusteradmin
        # as we do not have write-access to create users after installation
        # This is done with the directoryservice helper
        elif provider == constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY:

            root_credentials_provided = self.context.config().get_bool('directoryservice.root_credentials_provided', default=False)
            assert root_credentials_provided is True
            root_username_secret_arn = self.context.config().get_string('directoryservice.root_username_secret_arn')
            assert Utils.is_not_empty(root_username_secret_arn)
            root_password_secret_arn = self.context.config().get_string('directoryservice.root_password_secret_arn')
            assert Utils.is_not_empty(root_password_secret_arn)

            self.build_ad_automation_sqs_queue()
            self.build_activedirectory_cluster_settings()

    def build_iam_roles(self):
        ec2_managed_policies = self.get_ec2_instance_managed_policies()

        self.openldap_role = Role(
            context=self.context,
            name=f'{self.module_id}-openldap-role',
            scope=self.stack,
            description='IAM role assigned to the OpenLDAP server',
            assumed_by=['ssm', 'ec2'],
            managed_policies=ec2_managed_policies
        )
        self.openldap_role.attach_inline_policy(
            Policy(
                context=self.context,
                name='openldap-server-policy',
                scope=self.stack,
                policy_template_name='openldap-server.yml'
            )
        )
        self.openldap_instance_profile = InstanceProfile(
            context=self.context,
            name=f'{self.module_id}-openldap-instance-profile',
            scope=self.stack,
            roles=[self.openldap_role]
        )

    def build_security_groups(self):
        self.openldap_security_group = OpenLDAPServerSecurityGroup(
            context=self.context,
            name=f'{self.module_id}-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc,
            bastion_host_security_group=self.cluster.get_security_group('bastion-host')
        )

    def build_openldap_certs(self):
        """
        build openldap tls certs and save to secrets manager
        * only openldap server will have access to private key
        * all cluster nodes will have access to certificate in order to join directory service
        """
        hostname = self.context.config().get_string('directoryservice.hostname', required=True)
        self_signed_certificate_lambda_arn = self.context.config().get_string('cluster.self_signed_certificate_lambda_arn', required=True)
        self.openldap_certs = cdk.CustomResource(
            self.stack,
            'openldap-server-certs',
            service_token=self_signed_certificate_lambda_arn,
            properties={
                'domain_name': hostname,
                'certificate_name': f'{self.cluster_name}-{self.module_id}',
                'create_acm_certificate': False,
                'kms_key_id': self.context.config().get_string('cluster.secretsmanager.kms_key_id'),
                'tags': {
                    'Name': f'{self.cluster_name}-{self.module_id}',
                    'res:EnvironmentName': self.cluster_name,
                    'res:ModuleName': constants.MODULE_DIRECTORYSERVICE
                }
            },
            resource_type='Custom::SelfSignedCertificateOpenLDAPServer'
        )

    def build_ec2_instance(self):

        is_public = self.context.config().get_bool('directoryservice.public', False)
        base_os = self.context.config().get_string('directoryservice.base_os', required=True)
        instance_ami = self.context.config().get_string('directoryservice.instance_ami', required=True)
        instance_type = self.context.config().get_string('directoryservice.instance_type', required=True)
        volume_size = self.context.config().get_int('directoryservice.volume_size', 200)
        key_pair_name = self.context.config().get_string('cluster.network.ssh_key_pair', required=True)
        enable_detailed_monitoring = self.context.config().get_bool('directoryservice.ec2.enable_detailed_monitoring', default=False)
        enable_termination_protection = self.context.config().get_bool('directoryservice.ec2.enable_termination_protection', default=False)
        metadata_http_tokens = self.context.config().get_string('directoryservice.ec2.metadata_http_tokens', required=True)
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
                '/bin/bash openldap-server/setup.sh'
            ],
            base_os=base_os,
            infra_config={
                'LDAP_ROOT_USERNAME_SECRET_ARN': '${__LDAP_ROOT_USERNAME_SECRET_ARN__}',
                'LDAP_ROOT_PASSWORD_SECRET_ARN': '${__LDAP_ROOT_PASSWORD_SECRET_ARN__}',
                'LDAP_TLS_CERTIFICATE_SECRET_ARN': '${__LDAP_TLS_CERTIFICATE_SECRET_ARN__}',
                'LDAP_TLS_PRIVATE_KEY_SECRET_ARN': '${__LDAP_TLS_PRIVATE_KEY_SECRET_ARN__}'
            },
            proxy_config=proxy_config
        ).build()

        substituted_userdata = cdk.Fn.sub(user_data, {
            '__LDAP_ROOT_USERNAME_SECRET_ARN__': self.openldap_credentials.get_username_secret_arn(),
            '__LDAP_ROOT_PASSWORD_SECRET_ARN__': self.openldap_credentials.get_password_secret_arn(),
            '__LDAP_TLS_CERTIFICATE_SECRET_ARN__': self.openldap_certs.get_att_string('certificate_secret_arn'),
            '__LDAP_TLS_PRIVATE_KEY_SECRET_ARN__': self.openldap_certs.get_att_string('private_key_secret_arn')
        })

        launch_template = ec2.LaunchTemplate(
            self.stack, f'{self.module_id}-lt',
            instance_type=ec2.InstanceType(instance_type),
            machine_image=ec2.MachineImage.generic_linux({
                self.aws_region: instance_ami
                }
            ),
            user_data=ec2.UserData.custom(substituted_userdata),
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
            require_imdsv2=True if metadata_http_tokens == "required" else False,
            associate_public_ip_address=is_public
            )

        self.openldap_ec2_instance = ec2.CfnInstance(
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
            iam_instance_profile=self.openldap_instance_profile.instance_profile_name,
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
                    group_set=[self.openldap_security_group.security_group_id],
                    subnet_id=subnet_ids[0],
                )
            ],
            user_data=cdk.Fn.base64(substituted_userdata),
            monitoring=enable_detailed_monitoring
        )
        cdk.Tags.of(self.openldap_ec2_instance).add('Name', self.build_resource_name(self.module_id))
        cdk.Tags.of(self.openldap_ec2_instance).add(constants.IDEA_TAG_NODE_TYPE, constants.NODE_TYPE_INFRA)
        self.add_backup_tags(self.openldap_ec2_instance)

        if not enable_detailed_monitoring:
            self.add_nag_suppression(
                construct=self.openldap_ec2_instance,
                suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-EC28', reason='detailed monitoring is a configurable option to save costs')]
            )

        if not enable_termination_protection:
            self.add_nag_suppression(
                construct=self.openldap_ec2_instance,
                suppressions=[IdeaNagSuppression(rule_id='AwsSolutions-EC29', reason='termination protection not supported in CDK L2 construct. enable termination protection via AWS EC2 console after deploying the cluster.')]
            )

    def build_route53_record_set(self):
        hostname = self.context.config().get_string('directoryservice.hostname', required=True)
        private_hosted_zone_id = self.context.config().get_string('cluster.route53.private_hosted_zone_id', required=True)
        private_hosted_zone_name = self.context.config().get_string('cluster.route53.private_hosted_zone_name', required=True)
        self.openldap_cluster_dns_record_set = route53.RecordSet(
            self.stack,
            f'{self.module_id}-dns-record',
            record_type=route53.RecordType.A,
            target=route53.RecordTarget.from_ip_addresses(self.openldap_ec2_instance.attr_private_ip),
            ttl=cdk.Duration.minutes(5),
            record_name=hostname,
            zone=route53.HostedZone.from_hosted_zone_attributes(
                scope=self.stack,
                id='cluster-dns',
                hosted_zone_id=private_hosted_zone_id,
                zone_name=private_hosted_zone_name
            )
        )

    def build_ad_automation_sqs_queue(self):
        kms_key_id = self.context.config().get_string('cluster.sqs.kms_key_id')

        self.ad_automation_sqs_queue = SQSQueue(
            self.context, 'ad-automation-sqs-queue', self.stack,
            queue_name=f'{self.cluster_name}-{self.module_id}-ad-automation.fifo',
            fifo=True,
            content_based_deduplication=True,
            encryption_master_key=kms_key_id,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=30,
                queue=SQSQueue(
                    self.context, 'ad-automation-sqs-queue-dlq', self.stack,
                    queue_name=f'{self.cluster_name}-{self.module_id}-ad-automation-dlq.fifo',
                    fifo=True,
                    content_based_deduplication=True,
                    encryption_master_key=kms_key_id,
                    is_dead_letter_queue=True
                )
            )
        )
        self.add_common_tags(self.ad_automation_sqs_queue)
        self.add_common_tags(self.ad_automation_sqs_queue.dead_letter_queue.queue)

    def build_openldap_cluster_settings(self):

        cluster_settings = {
            'deployment_id': self.deployment_id,
            'private_ip': self.openldap_ec2_instance.attr_private_ip,
            'private_dns_name': self.openldap_ec2_instance.attr_private_dns_name,
            'instance_id': self.openldap_ec2_instance.ref,
            'security_group_id': self.openldap_security_group.security_group_id,
            'iam_role_arn': self.openldap_role.role_arn,
            'instance_profile_arn': self.openldap_instance_profile.ref,
            'root_username_secret_arn': self.openldap_credentials.admin_username.ref,
            'root_password_secret_arn': self.openldap_credentials.admin_password.ref,
            'tls_certificate_secret_arn': self.openldap_certs.get_att_string('certificate_secret_arn'),
            'tls_private_key_secret_arn': self.openldap_certs.get_att_string('private_key_secret_arn')
        }

        is_public = self.context.config().get_bool('directoryservice.public', False)
        if is_public:
            cluster_settings['public_ip'] = self.openldap_ec2_instance.attr_public_ip

        self.update_cluster_settings(cluster_settings)

    def build_aws_managed_ad_cluster_settings(self):
        cluster_settings = {
            'deployment_id': self.deployment_id,
            'ad_automation.sqs_queue_url': self.ad_automation_sqs_queue.queue_url,
            'ad_automation.sqs_queue_arn': self.ad_automation_sqs_queue.queue_arn
        }
        if self.activedirectory is not None:
            cluster_settings['directory_id'] = self.activedirectory.ad.ref
            cluster_settings['root_username_secret_arn'] = self.activedirectory.credentials.get_username_secret_arn()
            cluster_settings['root_password_secret_arn'] = self.activedirectory.credentials.get_password_secret_arn()

        self.update_cluster_settings(cluster_settings)

    def build_activedirectory_cluster_settings(self):
        cluster_settings = {
            'deployment_id': self.deployment_id,
            'ad_automation.sqs_queue_url': self.ad_automation_sqs_queue.queue_url,
            'ad_automation.sqs_queue_arn': self.ad_automation_sqs_queue.queue_arn
        }
        self.update_cluster_settings(cluster_settings)
