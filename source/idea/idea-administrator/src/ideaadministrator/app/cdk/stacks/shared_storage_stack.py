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

from ideadatamodel import constants

import ideaadministrator
from ideaadministrator.app.cdk.stacks import IdeaBaseStack

from ideaadministrator.app.cdk.constructs import (
    AmazonEFS,
    SharedStorageSecurityGroup,
)
from typing import Optional, Dict
import aws_cdk as cdk
import constructs

from aws_cdk import aws_ec2 as ec2


class SharedStorageStack(IdeaBaseStack):
    """
    Shared Storage Stack
     * Internal shared storage security group and file system.
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
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_SHARED_STORAGE,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.security_group: Optional[SharedStorageSecurityGroup] = None
        self.internal_efs: Optional[AmazonEFS] = None
        
        # build security group
        self.build_security_group()

        # build internal shared storage file systems
        self.build_internal_shared_storage()

        # build cluster settings
        self.build_cluster_settings()

    def build_security_group(self):
        vpc_id = self.context.config().get_string('cluster.network.vpc_id', required=True)
        self.vpc = ec2.Vpc.from_lookup(self.stack, 'vpc', vpc_id=vpc_id)   
        self.security_group = SharedStorageSecurityGroup(
            context=self.context,
            name='shared-storage-security-group',
            scope=self.stack,
            vpc=self.vpc
        )


    def build_internal_shared_storage(self):
        """
        provision new internal EFS
        """
        private_subnet_ids = self.context.config().get_list(f'cluster.network.infrastructure_host_subnets', [])
        private_subnets = [ec2.Subnet.from_subnet_id(self.stack, f"PrivateSubnet{i}", subnet_id) for i, subnet_id in enumerate(private_subnet_ids)]
        storage_configs = self.context.config().get_config('shared-storage', required=True)
        internal_storage_configs = storage_configs.get("internal")

        if not isinstance(internal_storage_configs, Dict):
            return

        self.internal_efs = AmazonEFS(
            context=self.context,
            name='internal-storage-efs',
            scope=self.stack,
            vpc=self.vpc,
            efs_config=internal_storage_configs.get('efs'),
            security_group=self.security_group,
            subnets=private_subnets
        )


    def build_cluster_settings(self):

        cluster_settings = {
            'deployment_id': self.deployment_id,
            'security_group_id': self.security_group.security_group_id
        }

        aws_dns_suffix = self.context.config().get_string('cluster.aws.dns_suffix', required=True)
        home_efs_id = self.context.config().get_string('shared-storage.home.efs.file_system_id', required=True)
        cluster_settings['home.efs.dns'] = f'{home_efs_id}.efs.{self.aws_region}.{aws_dns_suffix}'

        cluster_settings['internal.efs.dns'] = f'{self.internal_efs.file_system.ref}.efs.{self.aws_region}.{aws_dns_suffix}'
        cluster_settings['internal.efs.file_system_id'] = self.internal_efs.file_system.ref

        self.update_cluster_settings(cluster_settings)
