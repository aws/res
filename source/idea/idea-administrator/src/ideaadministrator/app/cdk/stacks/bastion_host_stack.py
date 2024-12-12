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

    def build_cluster_settings(self):

        cluster_settings = {}  # noqa
        cluster_settings['deployment_id'] = self.deployment_id

        is_public = self.context.config().get_bool('bastion-host.public', False)
        base_os = self.context.config().get_string('bastion-host.base_os', required=True)
        cluster_settings['public'] = is_public
        cluster_settings['iam_role_arn'] = self.bastion_host_role.role_arn
        cluster_settings['instance_profile_arn'] = self.bastion_host_instance_profile.ref

        kms_key_id = self.context.config().get_string('cluster.ebs.kms_key_id', required=False, default=None)
        if kms_key_id is not None:
             kms_key_arn = self.get_kms_key_arn(kms_key_id)
             ebs_kms_key = kms.Key.from_key_arn(scope=self.stack, id=f'ebs-kms-key', key_arn=kms_key_arn)
        else:
             ebs_kms_key = kms.Alias.from_alias_name(scope=self.stack, id=f'ebs-kms-key-default', alias_name='alias/aws/ebs')
        cluster_settings['kms_key_id'] = ebs_kms_key.key_id
        
        https_proxy = self.context.config().get_string('cluster.network.https_proxy', required=False, default='')
        proxy_config = {}
        if Utils.is_not_empty(https_proxy):
            proxy_config = {
                    'http_proxy': https_proxy,
                    'https_proxy': https_proxy,
                    'no_proxy': self.context.config().get_string('cluster.network.no_proxy', required=False, default='')
                    }

        user_data = BootstrapUserDataBuilder(
            aws_region=self.aws_region,
            bootstrap_package_uri=self.bootstrap_package_uri,
            install_commands=[
                '/bin/bash bastion-host/setup.sh'
            ],
            proxy_config=proxy_config,
            base_os=base_os,
            bootstrap_source_dir_path=ideaadministrator.props.bootstrap_source_dir
        ).build()
        user_data_formatted=ec2.UserData.custom(cdk.Fn.sub(user_data))
        user_data_base64=cdk.Fn.base64(user_data_formatted.render())
        cluster_settings['user_data'] = user_data_base64

        self.update_cluster_settings(cluster_settings)
