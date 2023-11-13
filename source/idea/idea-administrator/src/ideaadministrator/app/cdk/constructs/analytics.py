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

__all__ = ('OpenSearch')  # noqa

from ideaadministrator.app.cdk.constructs import SocaBaseConstruct, ExistingSocaCluster, IdeaNagSuppression
from ideasdk.context import ArnBuilder
from ideaadministrator.app_context import AdministratorContext
from ideasdk.utils import Utils

from typing import List, Dict, Optional

import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_opensearchservice as opensearch,
    aws_kms as kms
)


class OpenSearch(SocaBaseConstruct, opensearch.Domain):

    def __init__(
        self, context: AdministratorContext, name: str, scope: constructs.Construct,
        cluster: ExistingSocaCluster,
        security_groups: List[ec2.ISecurityGroup],
        data_nodes: int,
        data_node_instance_type: str,
        ebs_volume_size: int,
        removal_policy: cdk.RemovalPolicy,
        version: Optional[opensearch.EngineVersion] = None,
        create_service_linked_role: bool = True,
        access_policies: Optional[List[iam.PolicyStatement]] = None,
        advanced_options: Optional[Dict[str, str]] = None,
        automated_snapshot_start_hour: Optional[int] = None,
        capacity: Optional[opensearch.CapacityConfig] = None,
        cognito_dashboards_auth: Optional[opensearch.CognitoOptions] = None,
        custom_endpoint: Optional[opensearch.CustomEndpointOptions] = None,
        domain_name: Optional[str] = None,
        ebs: Optional[opensearch.EbsOptions] = None,
        enable_version_upgrade: Optional[bool] = None,
        encryption_at_rest: Optional[opensearch.EncryptionAtRestOptions] = None,
        kms_key_arn: Optional[kms.IKey] = None,
        enforce_https: Optional[bool] = None,
        fine_grained_access_control: Optional[opensearch.AdvancedSecurityOptions] = None,
        logging: Optional[opensearch.LoggingOptions] = None,
        node_to_node_encryption: Optional[bool] = None,
        tls_security_policy: Optional[opensearch.TLSSecurityPolicy] = None,
        use_unsigned_basic_auth: Optional[bool] = None,
        vpc_subnets: Optional[List[ec2.SubnetSelection]] = None,
        zone_awareness: Optional[opensearch.ZoneAwarenessConfig] = None
    ):

        self.context = context

        if version is None:
            version = opensearch.EngineVersion.OPENSEARCH_2_3

        if vpc_subnets is None:
            vpc_subnets = [ec2.SubnetSelection(
                subnets=cluster.private_subnets[0:data_nodes]
            )]

        if zone_awareness is None:
            if data_nodes > 1:
                zone_awareness = opensearch.ZoneAwarenessConfig(
                    enabled=True,
                    availability_zone_count=min(3, data_nodes)
                )
            else:
                zone_awareness = opensearch.ZoneAwarenessConfig(
                    enabled=False
                )

        if domain_name is None:
            domain_name = self.build_resource_name(name).lower()

        if enforce_https is None:
            enforce_https = True

        if encryption_at_rest is None:
            encryption_at_rest = opensearch.EncryptionAtRestOptions(
                enabled=True,
                kms_key=kms_key_arn
            )

        if ebs is None:
            ebs = opensearch.EbsOptions(
                volume_size=ebs_volume_size,
                volume_type=ec2.EbsDeviceVolumeType.GP3
            )

        if capacity is None:
            capacity = opensearch.CapacityConfig(
                data_node_instance_type=data_node_instance_type,
                data_nodes=data_nodes
            )

        if automated_snapshot_start_hour is None:
            automated_snapshot_start_hour = 0

        if removal_policy is None:
            removal_policy = cdk.RemovalPolicy.DESTROY

        if access_policies is None:
            arn_builder = ArnBuilder(self.context.config())
            access_policies = [
                iam.PolicyStatement(
                    principals=[iam.AnyPrincipal()],
                    actions=['es:ESHttp*'],
                    resources=[
                        arn_builder.get_arn(
                            'es',
                            f'domain/{domain_name}/*'
                        )
                    ]
                )
            ]

        if advanced_options is None:
            advanced_options = {
                'rest.action.multi.allow_explicit_index': 'true'
            }

        super().__init__(
            context, name, scope,
            version=version,
            access_policies=access_policies,
            advanced_options=advanced_options,
            automated_snapshot_start_hour=automated_snapshot_start_hour,
            capacity=capacity,
            cognito_dashboards_auth=cognito_dashboards_auth,
            custom_endpoint=custom_endpoint,
            domain_name=domain_name,
            ebs=ebs,
            enable_version_upgrade=enable_version_upgrade,
            encryption_at_rest=encryption_at_rest,
            enforce_https=enforce_https,
            fine_grained_access_control=fine_grained_access_control,
            logging=logging,
            node_to_node_encryption=node_to_node_encryption,
            removal_policy=removal_policy,
            security_groups=security_groups,
            tls_security_policy=tls_security_policy,
            use_unsigned_basic_auth=use_unsigned_basic_auth,
            vpc=cluster.vpc,
            vpc_subnets=vpc_subnets,
            zone_awareness=zone_awareness)

        if create_service_linked_role:

            aws_service_name = self.context.config().get_string('global-settings.opensearch.aws_service_name')
            if Utils.is_empty(aws_service_name):
                dns_suffix = self.context.config().get_string('cluster.aws.dns_suffix', required=True)
                aws_service_name = f'es.{dns_suffix}'

            # DO NOT CHANGE THE DESCRIPTION OF THE ROLE.
            service_linked_role = iam.CfnServiceLinkedRole(
                self,
                self.build_resource_name('es-service-linked-role'),
                aws_service_name=aws_service_name,
                description='Role for ES to access resources in the VPC'
            )
            self.node.add_dependency(service_linked_role)

        self.add_nag_suppression(suppressions=[
            IdeaNagSuppression(rule_id='AwsSolutions-OS3', reason='Access to OpenSearch cluster is restricted within a VPC'),
            IdeaNagSuppression(rule_id='AwsSolutions-OS4', reason='Use existing resources flow to provision an even more scalable OpenSearch cluster with dedicated master nodes'),
            IdeaNagSuppression(rule_id='AwsSolutions-OS5', reason='Access to OpenSearch cluster is restricted within a VPC')
        ])
