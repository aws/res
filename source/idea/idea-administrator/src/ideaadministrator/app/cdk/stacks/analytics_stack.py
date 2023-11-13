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
from ideaadministrator.app.cdk.idea_code_asset import IdeaCodeAsset, SupportedLambdaPlatforms
from ideadatamodel import (
    constants
)

import ideaadministrator
from ideaadministrator.app.cdk.stacks import IdeaBaseStack

from ideaadministrator.app.cdk.constructs import (
    ExistingSocaCluster,
    KinesisStream,
    IdeaNagSuppression,
    Role,
    Policy,
    LambdaFunction,
    OpenSearchSecurityGroup,
    OpenSearch,
    CustomResource
)
from ideadatamodel import exceptions

from ideasdk.utils import Utils

from typing import Optional
import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_opensearchservice as opensearch,
    aws_elasticloadbalancingv2 as elbv2,
    aws_kinesis as kinesis,
    aws_lambda as lambda_,
    aws_kms as kms,
    aws_lambda_event_sources as lambda_event_sources,
    aws_logs as logs
)


class AnalyticsStack(IdeaBaseStack):

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
                constants.IDEA_TAG_MODULE_NAME: constants.MODULE_ANALYTICS,
                constants.IDEA_TAG_MODULE_VERSION: ideaadministrator.props.current_release_version
            },
            env=env
        )

        self.cluster = ExistingSocaCluster(self.context, self.stack)

        self.security_group: Optional[ec2.ISecurityGroup] = None
        self.opensearch: Optional[opensearch.Domain] = None
        self.kinesis_stream: Optional[KinesisStream] = None

        self.build_security_group()
        is_existing = self.context.config().get_bool('analytics.opensearch.use_existing', default=False)
        if is_existing:
            domain_vpc_endpoint_url = self.context.config().get_string('analytics.opensearch.domain_vpc_endpoint_url', required=True)
            self.opensearch = opensearch.Domain.from_domain_endpoint(
                scope=self.stack,
                id='existing-opensearch',
                domain_endpoint=f'https://{domain_vpc_endpoint_url}'
            )
            self.build_dashboard_endpoints()
        else:
            self.build_opensearch()
            self.build_dashboard_endpoints()

            self.add_nag_suppression(
                construct=self.stack,
                suppressions=[
                    IdeaNagSuppression(rule_id='AwsSolutions-IAM5', reason='CDK L2 construct does not support custom LogGroup permissions'),
                    IdeaNagSuppression(rule_id='AwsSolutions-IAM4', reason='Usage is required for Service Linked Role'),
                    IdeaNagSuppression(rule_id='AwsSolutions-L1', reason='CDK L2 construct does not offer options to customize the Lambda runtime'),
                    IdeaNagSuppression(rule_id='AwsSolutions-KDS3', reason='Kinesis Data Stream is encrypted with customer-managed KMS key')
                ]
            )
            data_nodes = self.context.config().get_int('analytics.opensearch.data_nodes', required=True)
            if data_nodes == 1:
                self.add_nag_suppression(
                    construct=self.stack,
                    suppressions=[
                        IdeaNagSuppression(rule_id='AwsSolutions-OS7', reason='OpenSearch domain has 1 data node disabling Zone Awareness')
                    ]
                )

        self.build_analytics_input_stream()
        self.build_cluster_settings()

    def build_analytics_input_stream(self):

        stream_config = self.context.config().get_string('analytics.kinesis.stream_mode', required=True)
        if stream_config not in {'PROVISIONED', 'ON_DEMAND'}:
            raise exceptions.invalid_params('analytics.kinesis.stream_mode needs to be one of PROVISIONED or ON_DEMAND only')

        if stream_config == 'PROVISIONED':
            stream_mode = kinesis.StreamMode.PROVISIONED
            shard_count = self.context.config().get_int('analytics.kinesis.shard_count', required=True)
        else:
            stream_mode = kinesis.StreamMode.ON_DEMAND
            shard_count = None

        self.kinesis_stream = KinesisStream(
            context=self.context,
            name=f'{self.module_id}-kinesis-stream',
            scope=self.stack,
            stream_name=f'{self.module_id}-kinesis-stream',
            stream_mode=stream_mode,
            shard_count=shard_count
        )
        if self.aws_region in Utils.get_value_as_list('KINESIS_STREAMS_CLOUDFORMATION_UNSUPPORTED_STREAMMODEDETAILS_REGION_LIST', constants.CAVEATS, []):
            self.kinesis_stream.node.default_child.add_property_deletion_override('StreamModeDetails')

        lambda_name = f'{self.module_id}-sink-lambda'
        stream_processing_lambda_role = Role(
            context=self.context,
            name=f'{lambda_name}-role',
            scope=self.stack,
            description=f'Role for {lambda_name} function for Cluster: {self.cluster_name}',
            assumed_by=['lambda'])

        stream_processing_lambda_role.attach_inline_policy(Policy(
            context=self.context,
            name=f'{lambda_name}-policy',
            scope=self.stack,
            policy_template_name='analytics-sink-lambda.yml'
        ))

        stream_processing_lambda = LambdaFunction(
            self.context,
            lambda_name,
            self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_analytics_sink',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            description='Lambda to process analytics-kinesis-stream data',
            timeout_seconds=900,
            security_groups=[self.security_group],
            role=stream_processing_lambda_role,
            environment={
                'opensearch_endpoint': self.opensearch.domain_endpoint
            },
            vpc=self.cluster.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnets=self.cluster.private_subnets
            )
        )

        stream_processing_lambda.add_event_source(lambda_event_sources.KinesisEventSource(
            self.kinesis_stream,
            batch_size=100,
            starting_position=lambda_.StartingPosition.LATEST
        ))

    def build_security_group(self):
        self.security_group = OpenSearchSecurityGroup(
            context=self.context,
            name=f'{self.module_id}-opensearch-security-group',
            scope=self.stack,
            vpc=self.cluster.vpc
        )

    def check_service_linked_role_exists(self) -> bool:
        try:
            aws_dns_suffix = self.context.config().get_string('cluster.aws.dns_suffix', required=True)
            list_roles_result = self.context.aws().iam().list_roles(
                PathPrefix=f'/aws-service-role/es.{aws_dns_suffix}')
            roles = Utils.get_value_as_list('Roles', list_roles_result, default=[])

            list_roles_result = self.context.aws().iam().list_roles(
                PathPrefix=f'/aws-service-role/opensearchservice.{aws_dns_suffix}')
            roles.extend(Utils.get_value_as_list('Roles', list_roles_result, default=[]))

            return Utils.is_not_empty(roles)
        except Exception as e:
            self.context.aws_util().handle_aws_exception(e)

    def build_opensearch(self):
        create_service_linked_role = not self.check_service_linked_role_exists()

        data_nodes = self.context.config().get_int('analytics.opensearch.data_nodes', required=True)
        data_node_instance_type = self.context.config().get_string('analytics.opensearch.data_node_instance_type', required=True)
        ebs_volume_size = self.context.config().get_int('analytics.opensearch.ebs_volume_size', required=True)
        node_to_node_encryption = self.context.config().get_bool('analytics.opensearch.node_to_node_encryption', required=True)
        removal_policy = self.context.config().get_string('analytics.opensearch.removal_policy', required=True)
        app_log_removal_policy = self.context.config().get_string('analytics.opensearch.logging.app_log_removal_policy', default='DESTROY')
        search_log_removal_policy = self.context.config().get_string('analytics.opensearch.logging.search_log_removal_policy', default='DESTROY')
        slow_index_log_removal_policy = self.context.config().get_string('analytics.opensearch.logging.slow_index_log_removal_policy', default='DESTROY')
        kms_key_id = self.context.config().get_string('analytics.opensearch.kms_key_id')
        kms_key_arn = None
        if kms_key_id is not None:
            kms_key_arn = kms.Key.from_key_arn(self.stack, 'opensearch-kms-key', self.get_kms_key_arn(key_id=kms_key_id))

        self.opensearch = OpenSearch(
            context=self.context,
            name='analytics',
            scope=self.stack,
            cluster=self.cluster,
            security_groups=[self.security_group],
            data_nodes=data_nodes,
            data_node_instance_type=data_node_instance_type,
            ebs_volume_size=ebs_volume_size,
            removal_policy=cdk.RemovalPolicy(removal_policy),
            node_to_node_encryption=node_to_node_encryption,
            kms_key_arn=kms_key_arn,
            create_service_linked_role=create_service_linked_role,
            logging=opensearch.LoggingOptions(
                slow_search_log_enabled=self.context.config().get_bool('analytics.opensearch.logging.slow_search_log_enabled', required=True),
                slow_search_log_group=logs.LogGroup(
                    scope=self.stack,
                    id='analytics-search-log-group',
                    log_group_name=f'/{self.cluster_name}/{self.module_id}/search-log',
                    removal_policy=cdk.RemovalPolicy(search_log_removal_policy)
                ),
                app_log_enabled=self.context.config().get_bool('analytics.opensearch.logging.app_log_enabled', required=True),
                app_log_group=logs.LogGroup(
                    scope=self.stack,
                    id='analytics-app-log-group',
                    log_group_name=f'/{self.cluster_name}/{self.module_id}/app-log',
                    removal_policy=cdk.RemovalPolicy(app_log_removal_policy)
                ),
                slow_index_log_enabled=self.context.config().get_bool('analytics.opensearch.logging.slow_index_log_enabled', required=True),
                slow_index_log_group=logs.LogGroup(
                    scope=self.stack,
                    id='analytics-slow-index-log-group',
                    log_group_name=f'/{self.cluster_name}/{self.module_id}/slow-index-log',
                    removal_policy=cdk.RemovalPolicy(slow_index_log_removal_policy)
                ),
                # Audit logs are not enabled by default and not supported as this setting require fine-grained access permissions.
                # Manually provision OpenSearch cluster to enable audit logs and use existing resources flow to use the OpenSearch cluster
                audit_log_enabled=False
            ))

    def build_dashboard_endpoints(self):

        cluster_endpoints_lambda_arn = self.context.config().get_string('cluster.cluster_endpoints_lambda_arn', required=True)
        external_https_listener_arn = self.context.config().get_string('cluster.load_balancers.external_alb.https_listener_arn', required=True)
        dashboard_endpoint_path_patterns = self.context.config().get_list('analytics.opensearch.endpoints.external.path_patterns', required=True)
        dashboard_endpoint_priority = self.context.config().get_int('analytics.opensearch.endpoints.external.priority', required=True)

        is_existing = self.context.config().get_bool('analytics.opensearch.use_existing', default=False)
        if is_existing:
            domain_name = self.opensearch.domain_name
            if domain_name.startswith('vpc-'):
                # existing lookup returns the domain name as vpc-idea-dev1-analytics
                # when used in describe_domain, service returns error - Domain not found: vpc-idea-dev1-analytics
                # hack - fix to replace vpc- and then perform look up
                domain_name = domain_name.replace('vpc-', '', 1)
            describe_domain_result = self.context.aws().opensearch().describe_domain(DomainName=domain_name)
            domain_status = describe_domain_result['DomainStatus']
            domain_cluster_config = domain_status['ClusterConfig']
            data_nodes = domain_cluster_config['InstanceCount']
        else:
            domain_name = self.opensearch.domain_name
            data_nodes = self.context.config().get_int('analytics.opensearch.data_nodes', required=True)

        opensearch_private_ips = CustomResource(
            context=self.context,
            name='opensearch-private-ips',
            scope=self.stack,
            idea_code_asset=IdeaCodeAsset(
                lambda_package_name='idea_custom_resource_opensearch_private_ips',
                lambda_platform=SupportedLambdaPlatforms.PYTHON
            ),
            lambda_timeout_seconds=180,
            policy_template_name='custom-resource-opensearch-private-ips.yml',
            resource_type='OpenSearchPrivateIPAddresses'
        ).invoke(
            name='opensearch-private-ips',
            properties={
                'DomainName': domain_name
            }
        )

        targets = []
        for i in range(data_nodes * 3):
            targets.append(elbv2.CfnTargetGroup.TargetDescriptionProperty(
                id=cdk.Fn.select(
                    index=i,
                    array=cdk.Fn.split(
                        delimiter=',',
                        source=opensearch_private_ips.get_att_string('IpAddresses')
                    )
                )
            ))

        dashboard_target_group = elbv2.CfnTargetGroup(
            self.stack,
            f'{self.cluster_name}-dashboard-target-group',
            port=443,
            protocol='HTTPS',
            target_type='ip',
            vpc_id=self.cluster.vpc.vpc_id,
            name=self.get_target_group_name('dashboard'),
            targets=targets,
            health_check_path='/'
        )

        cdk.CustomResource(
            self.stack,
            'dashboard-endpoint',
            service_token=cluster_endpoints_lambda_arn,
            properties={
                'endpoint_name': f'{self.module_id}-dashboard-endpoint',
                'listener_arn': external_https_listener_arn,
                'priority': dashboard_endpoint_priority,
                'target_group_arn': dashboard_target_group.ref,
                'conditions': [
                    {
                        'Field': 'path-pattern',
                        'Values': dashboard_endpoint_path_patterns
                    }
                ],
                'actions': [
                    {
                        'Type': 'forward',
                        'TargetGroupArn': dashboard_target_group.ref
                    }
                ],
                'tags': {
                    constants.IDEA_TAG_ENVIRONMENT_NAME: self.cluster_name,
                    constants.IDEA_TAG_MODULE_ID: self.module_id,
                    constants.IDEA_TAG_MODULE_NAME: constants.MODULE_ANALYTICS
                }
            },
            resource_type='Custom::DashboardEndpointExternal'
        )

    def build_cluster_settings(self):

        cluster_settings = {
            'deployment_id': self.deployment_id,
            'opensearch.domain_name': self.opensearch.domain_name,
            'opensearch.domain_arn': self.opensearch.domain_arn,
            'opensearch.domain_endpoint': self.opensearch.domain_endpoint,
            'opensearch.dashboard_endpoint': f'{self.opensearch.domain_endpoint}/_dashboards',
            'kinesis.stream_name': self.kinesis_stream.stream_name,
            'kinesis.stream_arn': self.kinesis_stream.stream_arn
        }

        if self.security_group is not None:
            cluster_settings['opensearch.security_group_id'] = self.security_group.security_group_id

        self.update_cluster_settings(cluster_settings)
