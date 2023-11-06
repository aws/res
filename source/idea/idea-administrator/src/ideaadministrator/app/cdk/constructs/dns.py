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
    'DNSResolverEndpoint',
    'DNSResolverRule',
    'PrivateHostedZone'
)

from ideaadministrator.app.cdk.constructs import (
    SocaBaseConstruct
)
from ideaadministrator.app_context import AdministratorContext

from typing import List, Optional
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_route53 as route53,
    aws_route53resolver as route53resolver
)


class DNSResolverEndpoint(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 vpc: ec2.IVpc,
                 security_group_ids: List[str],
                 subnet_ids: Optional[List[str]],
                 direction: str = 'OUTBOUND'):
        super().__init__(context, name)
        self.scope = scope
        self.vpc = vpc
        self.subnet_ids = subnet_ids
        self.security_group_ids = security_group_ids
        self.direction = direction

        self.resolver_endpoint = self.build_resolver_endpoint()

    def build_resolver_endpoint(self) -> route53resolver.CfnResolverEndpoint:
        ip_addresses = []
        for subnet_id in self.subnet_ids:
            ip_addresses.append(route53resolver.CfnResolverEndpoint.IpAddressRequestProperty(subnet_id=subnet_id))

        resolver_endpoint = route53resolver.CfnResolverEndpoint(
            scope=self.scope,
            id=f'{self.name}-dns-resolver-endpoint',
            direction=self.direction,
            name=self.name,
            ip_addresses=ip_addresses,
            security_group_ids=self.security_group_ids
        )
        self.add_common_tags(resolver_endpoint)

        return resolver_endpoint


class DNSResolverRule(SocaBaseConstruct):

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 domain_name: str,
                 vpc: ec2.IVpc,
                 resolver_endpoint_id: str,
                 ip_addresses: List[str],
                 rule_type: str = 'FORWARD',
                 port: str = None):
        super().__init__(context, name)
        self.scope = scope
        self.domain_name = domain_name
        self.vpc = vpc
        self.resolver_endpoint_id = resolver_endpoint_id

        target_ips = []
        for ip_address in ip_addresses:
            target_ips.append(route53resolver.CfnResolverRule.TargetAddressProperty(
                ip=ip_address,
                port=port
            ))

        self.resolver_rule = route53resolver.CfnResolverRule(
            scope=self.scope,
            id=f'{self.name}-dns-resolver-rule',
            name=f'{self.name}-dns-resolver-rule',
            domain_name=self.domain_name,
            rule_type=rule_type,
            resolver_endpoint_id=self.resolver_endpoint_id,
            target_ips=target_ips
        )
        self.add_common_tags(self.resolver_rule)

        self.resolver_rule_assoc = route53resolver.CfnResolverRuleAssociation(
            scope=self.scope,
            id=f'{self.name}-dns-resolver-rule-association',
            resolver_rule_id=self.resolver_rule.attr_resolver_rule_id,
            vpc_id=self.vpc.vpc_id
        )
        self.add_common_tags(self.resolver_rule_assoc)


class PrivateHostedZone(SocaBaseConstruct, route53.PrivateHostedZone):

    def __init__(self, context: AdministratorContext, scope: constructs.Construct, vpc: ec2.IVpc):
        self.context = context
        zone_name = self.context.config().get_string('cluster.route53.private_hosted_zone_name', required=True)
        super().__init__(context=context,
                         name=f'{self.cluster_name}-private-hosted-zone',
                         scope=scope,
                         vpc=vpc,
                         comment=f'Private Hosted Zone for IDEA Cluster: {self.cluster_name}',
                         zone_name=zone_name)
