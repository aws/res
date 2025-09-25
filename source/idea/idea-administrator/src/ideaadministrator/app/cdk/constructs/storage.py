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

__all__ = (
    'AmazonEFS',
)

from ideasdk.utils import Utils

from ideaadministrator.app.cdk.constructs import SocaBaseConstruct
from ideaadministrator.app_context import AdministratorContext

from typing import List, Optional, Tuple, Dict

import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_efs as efs,
)


class AmazonEFS(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc,
                 security_group: ec2.SecurityGroup,
                 efs_config: Dict,
                 subnets: List[ec2.ISubnet] = None,
                 ):
        super().__init__(context, name, scope)

        self.scope = scope
        self.vpc = vpc
        self.security_group = security_group
        self.kms_key_id = Utils.get_value_as_string('kms_key_id', efs_config)
        self.subnets = subnets
        removal_policy = Utils.get_value_as_string('removal_policy', efs_config)
        if removal_policy == 'DESTROY':
            removal_policy = 'DELETE'
        self.deletion_policy = cdk.CfnDeletionPolicy(removal_policy)
        self.transition_to_ia = Utils.get_value_as_string('transition_to_ia', efs_config)
        self.encrypted = Utils.get_value_as_bool('encrypted', efs_config, True)
        self.throughput_mode = Utils.get_value_as_string('throughput_mode', efs_config, 'bursting')
        self.performance_mode = Utils.get_value_as_string('performance_mode', efs_config, 'generalPurpose')

        file_system, mount_targets = self.build_file_system()
        self.file_system = file_system
        self.mount_targets = mount_targets


    def get_subnets(self) -> List[ec2.ISubnet]:
        if self.subnets is not None:
            return self.subnets
        else:
            return self.vpc.private_subnets

    def build_file_system(self) -> Tuple[efs.CfnFileSystem, List[efs.CfnMountTarget]]:

        lifecycle_policies = None
        if Utils.is_not_empty(self.transition_to_ia):
            lifecycle_policies = [efs.CfnFileSystem.LifecyclePolicyProperty(transition_to_ia=self.transition_to_ia)]

        file_system = efs.CfnFileSystem(
            scope=self.scope,
            id=self.build_resource_name(self.name),
            encrypted=self.encrypted,
            file_system_tags=[
                efs.CfnFileSystem.ElasticFileSystemTagProperty(
                    key='Name',
                    value=self.build_resource_name(self.name)
                )
            ],
            kms_key_id=self.kms_key_id,
            throughput_mode=self.throughput_mode,
            performance_mode=self.performance_mode,
            lifecycle_policies=lifecycle_policies,
            file_system_policy={
                "Version": "2012-10-17",
                "Id": "efs-prevent-anonymous-access-policy",
                "Statement": [
                    {
                        "Sid": "efs-statement",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": "*"
                        },
                        "Action": [
                            "elasticfilesystem:ClientRootAccess",
                            "elasticfilesystem:ClientWrite",
                            "elasticfilesystem:ClientMount"
                        ],
                        "Condition": {
                            "Bool": {
                                "elasticfilesystem:AccessedViaMountTarget": "true"
                            }
                        }
                    },
                    {
                        "Sid": "efs-enforce-tls",
                        "Effect": "Deny",
                        "Principal": {
                            "AWS": "*"
                        },
                        "Action": "*",
                        "Condition": {
                            "Bool": {
                                "aws:SecureTransport": "false"
                            }
                        }
                    }
                ]
            }
        )
        self.add_common_tags(file_system)
        self.add_backup_tags(file_system)
        file_system.cfn_options.deletion_policy = self.deletion_policy

        security_group_ids = [self.security_group.security_group_id]

        mount_targets = []
        for index, subnet in enumerate(self.get_subnets()):
            mount_target_construct_id = f'{self.construct_id}-mount-target-{index + 1}'
            mount_target = efs.CfnMountTarget(
                scope=file_system,
                id=mount_target_construct_id,
                file_system_id=file_system.ref,
                security_groups=security_group_ids,
                subnet_id=subnet.subnet_id
            )
            self.add_common_tags(mount_target)
            mount_targets.append(mount_target)

        return file_system, mount_targets
