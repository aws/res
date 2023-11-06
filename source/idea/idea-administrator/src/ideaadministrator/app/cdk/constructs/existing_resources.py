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
    'ExistingVpc',
    'ExistingSocaCluster'
)

from ideasdk.utils import Utils

from ideaadministrator.app_context import AdministratorContext

from ideaadministrator.app.cdk.constructs import (
    SocaBaseConstruct
)

from typing import List, Optional, Dict

import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam
)


class ExistingVpc(SocaBaseConstruct):
    """
    Class encapsulating Existing VPC
    Acts as an intermediate entity to retrieve subnets that are configured in cluster config, instead of returning all subnets in Vpc.
    Downstream stacks should use ExistingVpc instead of ec2.Vpc to retrieve subnet information.
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct):
        super().__init__(context, name)
        self.scope = scope
        self.vpc_id = self.context.config().get_string('cluster.network.vpc_id', required=True)
        self.vpc = ec2.Vpc.from_lookup(self.scope, 'vpc', vpc_id=self.vpc_id)
        self._private_subnets: Optional[List[ec2.ISubnet]] = None
        self._public_subnets: Optional[List[ec2.ISubnet]] = None

    def lookup_vpc(self):
        self.vpc = ec2.Vpc.from_lookup(self.scope, 'vpc', vpc_id=self.vpc_id)

    def get_public_subnet_ids(self) -> List[str]:
        return self.context.config().get_list('cluster.network.public_subnets', [])

    def get_private_subnet_ids(self) -> List[str]:
        return self.context.config().get_list('cluster.network.private_subnets', [])

    def get_public_subnets(self) -> List[ec2.ISubnet]:
        """
        filter subnets from Vpc based on subnet ids configured in `cluster.network.public_subnets`
        the result is sorted based on the order of subnet ids provided in the configuration.
        """
        if self._public_subnets is not None:
            return self._public_subnets

        public_subnet_ids = self.get_public_subnet_ids()
        if Utils.is_empty(public_subnet_ids):
            self._public_subnets = []
            return self._public_subnets

        result = []
        if self.vpc.public_subnets is not None:
            for subnet in self.vpc.public_subnets:
                if subnet.subnet_id in public_subnet_ids:
                    result.append(subnet)

        # sort based on index in public_subnets[] configuration
        result.sort(key=lambda x: public_subnet_ids.index(x.subnet_id))

        self._public_subnets = result
        return self._public_subnets

    def get_private_subnets(self) -> List[ec2.ISubnet]:
        """
        filter subnets from Vpc based on subnet ids configured in `cluster.network.private_subnets`
        the result is sorted based on the order of subnet ids provided in the configuration.

        The order of subnets is important in below use cases:
        * private_subnets[0] is anchored for single-zone file systems.
        * Amazon EFS mount points are provisioned based on the order of subnets in configuration. if the order is changed, that could result in upgrade failures for net-new shared-storage module configurations.

        Note for Isolated Subnets:
        * IDEA does not support pure isolated subnets. The expectation is internet access is available for all nodes either via TransitGateway or by some other means in the associated RouteTable for the subnet.
        * CDK automagically buckets the subnets under private and isolated based on NAT Gateway configuration. This scenario is applicable when admin uses existing resources flow, where
          Isolated Subnets (subnets without NAT gateway attached to RouteTable) are configured as IDEA "private subnets".
        * After lookup, ec2.IVpc buckets the subnets under public_subnets, private_subnets and isolated_subnets.
        * To ensure all configured subnets are selected, both vpc.private_subnets and vpc.isolated_subnets are checked to resolve ec2.ISubnet
        """
        if self._private_subnets is not None:
            return self._private_subnets

        private_subnet_ids = self.get_private_subnet_ids()
        if Utils.is_empty(private_subnet_ids):
            self._private_subnets = []
            return self._private_subnets

        result = []
        if self.vpc.private_subnets is not None:
            for subnet in self.vpc.private_subnets:
                if subnet.subnet_id in private_subnet_ids:
                    result.append(subnet)
        if self.vpc.isolated_subnets is not None:
            for subnet in self.vpc.isolated_subnets:
                if subnet.subnet_id in private_subnet_ids:
                    result.append(subnet)
        # sort based on index in private_subnets[] configuration
        result.sort(key=lambda x: private_subnet_ids.index(x.subnet_id))

        self._private_subnets = result
        return self._private_subnets


class ExistingSocaCluster(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, scope: constructs.Construct):
        super().__init__(context, 'existing-cluster')

        self.scope = scope

        self.existing_vpc = ExistingVpc(
            context=self.context,
            name='existing-vpc',
            scope=self.scope
        )
        self.security_groups: Dict[str, ec2.ISecurityGroup] = {}
        self.roles: Dict[str, iam.IRole] = {}

        # IAM roles
        self.lookup_roles()

        # security groups
        self.lookup_security_groups()

    @property
    def vpc(self) -> ec2.IVpc:
        return self.existing_vpc.vpc

    @property
    def public_subnets(self) -> List[ec2.ISubnet]:
        return self.existing_vpc.get_public_subnets()

    @property
    def private_subnets(self) -> List[ec2.ISubnet]:
        return self.existing_vpc.get_private_subnets()

    def lookup_roles(self):
        roles = self.context.config().get_config('cluster.iam.roles', required=True)
        for name in roles:
            self.roles[name] = iam.Role.from_role_arn(
                self.scope,
                f'{name}-role',
                role_arn=roles[name]
            )

    def get_role(self, name: str) -> iam.IRole:
        if not Utils.value_exists(name, self.roles):
            pass
        return Utils.get_any_value(name, self.roles)

    def lookup_security_groups(self):
        security_groups = self.context.config().get_config('cluster.network.security_groups', required=True)
        for name in security_groups:
            self.security_groups[name] = ec2.SecurityGroup.from_security_group_id(
                self.scope,
                f'{name}-security-group',
                security_group_id=security_groups[name]
            )

    def get_security_group(self, name: str) -> Optional[ec2.ISecurityGroup]:
        return Utils.get_any_value(name, self.security_groups)
