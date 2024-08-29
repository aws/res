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
from ideasdk.launch_configurations import LaunchRoleHelper
from ideasdk.config.cluster_config import ClusterConfig
from ideadatamodel import constants

from typing import Optional, List


class ArnBuilder:

    def __init__(self, config: ClusterConfig):
        self.config = config

    @staticmethod
    def build_arn(partition: Optional[str],
                  service: Optional[str],
                  region: Optional[str],
                  account_id: Optional[str],
                  resource: Optional[str] = None,
                  resource_type: Optional[str] = None,
                  resource_id: Optional[str] = None,
                  resource_delimiter='/') -> str:
        arn = f'arn:{partition}:{service}:{region}:{account_id}'
        if resource is not None:
            arn += f':{resource}'
        else:
            if resource_type is None:
                arn += f':{resource_id}'
            else:
                arn += f':{resource_type}{resource_delimiter}{resource_id}'
        return arn

    def get_arn(self, service: str, resource: str,
                aws_account_id=None, aws_region=None) -> str:
        if aws_account_id is None:
            aws_account_id = self.config.get_string('cluster.aws.account_id')
        if aws_region is None:
            aws_region = self.config.get_string('cluster.aws.region')
        return self.build_arn(
            partition=self.config.get_string('cluster.aws.partition'),
            service=service,
            region=aws_region,
            account_id=aws_account_id,
            resource=resource
        )

    @property
    def vpc_arn(self) -> str:
        return self.get_arn(
            service='ec2',
            resource=f'vpc/{self.config.get_string("cluster.network.vpc_id")}'
        )

    def get_log_group_arn(self, suffix: str = None) -> str:
        if suffix is None:
            suffix = '*'
        return self.get_arn(
            service='logs',
            resource=f'log-group:/{self.config.get_string("cluster.cluster_name")}{suffix}'
        )

    def get_log_stream_arn(self) -> str:
        return self.get_arn(
            service='logs',
            resource=f'log-group:/{self.config.get_string("cluster.cluster_name")}*:log-stream:*'
        )

    def get_lambda_log_group_arn(self, suffix: str = None) -> str:
        if suffix is None:
            suffix = '*'
        return self.get_arn(
            service='logs',
            resource=f'log-group:/aws/lambda/{self.config.get_string("cluster.cluster_name")}{suffix}'
        )

    @property
    def lambda_log_stream_arn(self) -> str:
        return self.get_arn(
            service='logs',
            resource=f'log-group:/aws/lambda/{self.config.get_string("cluster.cluster_name")}*:log-stream:*'
        )

    @property
    def get_security_group_arn(self) -> str:
        return self.get_arn(
            service='ec2',
            resource='security-group/*')

    @property
    def get_security_group_rule_arn(self) -> str:
        return self.get_arn(
            service='ec2',
            resource='security-group-rule/*')

    @property
    def ec2_common_arns(self) -> List[str]:
        return [
            self.get_arn('ec2', 'subnet/*', aws_account_id='*', aws_region='*'),
            self.get_arn('ec2', 'key-pair/*', aws_region='*'),
            self.get_arn('ec2', 'instance/*', aws_region='*'),
            self.get_arn('ec2', 'snapshot/*', aws_account_id='*', aws_region='*'),
            self.get_arn('ec2', 'launch-template/*', aws_region='*'),
            self.get_arn('ec2', 'volume/*', aws_region='*'),
            self.get_arn('ec2', 'security-group/*', aws_region='*'),
            self.get_arn('ec2', 'placement-group/*', aws_region='*'),
            self.get_arn('ec2', 'network-interface/*', aws_region='*'),
            self.get_arn('ec2', 'spot-instances-request/*', aws_account_id='*', aws_region='*'),
            self.get_arn('ec2', 'image/*', aws_account_id='*', aws_region='*')
        ]

    @property
    def s3_global_arns(self) -> List[str]:
        return [
            self.get_arn('s3', f'dcv-license.{self.config.get_string("cluster.aws.region")}/*', aws_account_id='', aws_region=''),
            self.get_arn('s3', 'ec2-linux-nvidia-drivers/*', aws_account_id='', aws_region=''),
            self.get_arn('s3', 'ec2-linux-nvidia-drivers', aws_account_id='', aws_region=''),
            self.get_arn('s3', 'nvidia-gaming/*', aws_account_id='', aws_region=''),
            self.get_arn('s3', 'nvidia-gaming-drivers', aws_account_id='', aws_region=''),
            self.get_arn('s3', 'nvidia-gaming-drivers/*', aws_account_id='', aws_region=''),
            self.get_arn('s3', 'ec2-amd-linux-drivers/*', aws_account_id='', aws_region=''),
            self.get_arn('s3', 'ec2-amd-linux-drivers', aws_account_id='', aws_region='')
        ]

    @property
    def alb_listener_rule_arn(self) -> str:
        return self.get_arn(
            service='elasticloadbalancing',
            resource=f'listener-rule/app/{self.config.get_string("cluster.cluster_name")}*/*/*'
        )

    @property
    def alb_listener_arn(self) -> str:
        return self.get_arn(
            service='elasticloadbalancing',
            resource=f'listener/app/{self.config.get_string("cluster.cluster_name")}*/*/*'
        )

    @property
    def nlb_listener_arn(self) -> str:
        return self.get_arn(
            service='elasticloadbalancing',
            resource=f'listener/net/{self.config.get_string("cluster.cluster_name")}*/*/*'
        )

    @property
    def get_target_group_arn(self) -> str:
        return self.get_arn(service='elasticloadbalancing',
                            resource=f'targetgroup/{self.config.cluster_name}*/*')

    @property
    def get_loadbalancer_arn(self) -> str:
        return self.get_arn(service='elasticloadbalancing',
                            resource=f'loadbalancer/net/{self.config.cluster_name}*/*')

    @property
    def target_group_arn(self) -> str:
        return self.get_arn(
            service='elasticloadbalancing',
            resource=f'targetgroup/soca*/*'
        )

    def get_lambda_arn(self, suffix: str = '*') -> str:
        return self.get_arn(
            service='lambda',
            resource=f'function:{self.config.get_string("cluster.cluster_name")}-{suffix}'
        )

    @property
    def service_role_arns(self) -> List[str]:
        def role_arn(service) -> str:
            return str(f'arn:{self.config.get_string("cluster.aws.partition")}:iam::{self.config.get_string("cluster.aws.account_id")}:'
                       f'role/{self.config.get_string("cluster.aws.partition")}-service-role/{service}')

        return [
            role_arn(f's3.data-source.lustre.fsx.{self.config.get_string("cluster.aws.dns_suffix")}/*'),
            role_arn(f'autoscaling.{self.config.get_string("cluster.aws.dns_suffix")}/*'),
            role_arn(f'spotfleet.{self.config.get_string("cluster.aws.dns_suffix")}/*'),
            role_arn(f'fsx.{self.config.get_string("cluster.aws.dns_suffix")}/*')
        ]

    @property
    def ses_arn(self) -> str:
        return self.get_arn(
            service='ses',
            resource='identity/*',
            aws_region='*'
        )

    @property
    def dcv_license_s3_bucket_arns(self) -> List[str]:
        return [
            self.get_arn(service='s3', aws_region='', aws_account_id='', resource='dcv-license.*/*'),
            self.get_arn(service='s3', aws_region='', aws_account_id='', resource='dcv-license.*')
        ]

    @property
    def dcv_host_required_policy_arns(self) -> List[str]:
        required_policies = [
            'amazon_ssm_managed_instance_core_arn',
            'cloud_watch_agent_server_arn',
            'dcv_host_role_managed_policy_arn'
        ]
        required_policy_arns = [self.config.get_string(f'cluster.iam.policies.{policy}') for policy in required_policies]

        return required_policy_arns

    @property
    def s3_bucket_arns(self) -> List[str]:
        return [
            self.get_arn(service='s3', aws_region='', aws_account_id='',
                         resource=f'{self.config.get_string("cluster.cluster_s3_bucket")}/*'),
            self.get_arn(service='s3', aws_region='', aws_account_id='', resource=f'{self.config.get_string("cluster.cluster_s3_bucket")}')
        ]

    def get_s3_bucket_arns(self, bucket_name: str) -> List[str]:
        return [
            self.get_arn(service='s3', aws_region='', aws_account_id='', resource=f'{bucket_name}/*'),
            self.get_arn(service='s3', aws_region='', aws_account_id='', resource=bucket_name)
        ]


    def get_ssm_arn(self, resource_id: str) -> str:
        return self.build_arn(
            partition=self.config.get_string("cluster.aws.partition"),
            service='ssm',
            region='',
            account_id='',
            resource_type='',
            resource_id=resource_id,
            resource_delimiter=':'
        )

    @property
    def cluster_config_ddb_arn(self) -> List[str]:
        return [
            self.get_arn(service='dynamodb',
                         resource=f'table/{self.config.get_string("cluster.cluster_name")}.cluster-settings',
                         aws_region=self.config.get_string("cluster.aws.region")),
            self.get_arn(service='dynamodb',
                         resource=f'table/{self.config.get_string("cluster.cluster_name")}.cluster-settings/stream/*',
                         aws_region=self.config.get_string("cluster.aws.region")),
            self.get_arn(service='dynamodb',
                         resource=f'table/{self.config.get_string("cluster.cluster_name")}.modules',
                         aws_region=self.config.get_string("cluster.aws.region"))
        ]

    def get_ddb_table_arn(self, table_name_suffix: str) -> str:
        return self.get_arn(service='dynamodb',
                            resource=f'table/{self.config.get_string("cluster.cluster_name")}.{table_name_suffix}',
                            aws_region=self.config.get_string("cluster.aws.region"))

    def get_ddb_table_export_arn(self) -> str:
        return self.get_arn(service='dynamodb',
                            resource=f'table/{self.config.get_string("cluster.cluster_name")}.*/export/*',
                            aws_region=self.config.get_string("cluster.aws.region"))

    def get_ddb_table_stream_arn(self, table_name_suffix: str) -> str:
        return self.get_arn(service='kinesis',
                            resource=f'stream/{self.config.get_string("cluster.cluster_name")}.{table_name_suffix}-kinesis-stream',
                            aws_region=self.config.get_string("cluster.aws.region"))

    def get_ad_automation_ddb_table_arn(self) -> str:
        return self.get_ddb_table_arn('ad-automation')

    def get_ad_automation_sqs_queue_arn(self) -> str:
        module_id = self.config.get_module_id(constants.MODULE_DIRECTORYSERVICE)
        return self.get_sqs_arn(f'{module_id}-ad-automation.fifo')

    def get_kinesis_arn(self) -> str:
        return self.get_arn(service='kinesis',
                            resource=f'stream/{self.config.get_string("cluster.cluster_name")}-*',
                            aws_region=self.config.get_string("cluster.aws.region"))

    def get_sns_arn(self, topic_name_suffix: str) -> str:
        return self.get_arn(service='sns',
                            resource=f'{self.config.get_string("cluster.cluster_name")}-{topic_name_suffix}',
                            aws_region=self.config.get_string("cluster.aws.region"))

    def get_sqs_arn(self, queue_name_suffix: str) -> str:
        return self.get_arn(service='sqs',
                            resource=f'{self.config.get_string("cluster.cluster_name")}-{queue_name_suffix}',
                            aws_region=self.config.get_string("cluster.aws.region"))

    def get_route53_hostedzone_arn(self) -> str:
        return f'arn:{self.config.get_string("cluster.aws.partition", required=True)}:route53:::hostedzone/*'

    def get_iam_arn(self, role_name_suffix: str) -> str:
        return self.get_arn(service='iam',
                            resource=f'role/{self.config.get_string("cluster.cluster_name")}-{role_name_suffix}-{self.config.get_string("cluster.aws.region")}',
                            aws_region='')

    def get_vdi_iam_role_arn(self, project_name:str) -> str:
        return self.get_arn(service = 'iam',
                            aws_region='',
                            resource= f'role/{LaunchRoleHelper.get_vdi_role_path( cluster_name=self.config.get_string("cluster.cluster_name"), region=self.config.get_string("cluster.aws.region"))}/{LaunchRoleHelper.get_vdi_role_name(self.config.get_string("cluster.cluster_name"),project_name)}'
                            )

    def get_vdi_iam_instance_profile_arn(self, project_name:str) -> str:
        return self.get_arn(service = 'iam',
                            aws_region='',
                            resource= f'instance-profile/{LaunchRoleHelper.get_vdi_instance_profile_path( cluster_name=self.config.get_string("cluster.cluster_name"), region=self.config.get_string("cluster.aws.region"))}/{LaunchRoleHelper.get_vdi_instance_profile_name(self.config.get_string("cluster.cluster_name"),project_name)}'
                            )
    @property
    def kms_secretsmanager_key_arn(self) -> str:
        return(self.get_arn(service='kms',
                        resource=f'key/{self.config.get_string("cluster.secretsmanager.kms_key_id")}',
                        aws_region=self.config.get_string("cluster.aws.region")))

    @property
    def kms_sqs_key_arn(self) -> str:
        return(self.get_arn(service='kms',
                        resource=f'key/{self.config.get_string("cluster.sqs.kms_key_id")}',
                        aws_region=self.config.get_string("cluster.aws.region")))

    @property
    def kms_sns_key_arn(self) -> str:
        return(self.get_arn(service='kms',
                        resource=f'key/{self.config.get_string("cluster.sns.kms_key_id")}',
                        aws_region=self.config.get_string("cluster.aws.region")))

    @property
    def kms_dynamodb_key_arn(self) -> str:
        return(self.get_arn(service='kms',
                        resource=f'key/{self.config.get_string("cluster.dynamodb.kms_key_id")}',
                        aws_region=self.config.get_string("cluster.aws.region")))
    @property
    def kms_ebs_key_arn(self) -> str:
        return(self.get_arn(service='kms',
                        resource=f'key/{self.config.get_string("cluster.ebs.kms_key_id")}',
                        aws_region=self.config.get_string("cluster.aws.region")))

    @property
    def kms_backup_key_arn(self) -> str:
        return(self.get_arn(service='kms',
                        resource=f'key/{self.config.get_string("cluster.backups.backup_vault.kms_key_id")}',
                        aws_region=self.config.get_string("cluster.aws.region")))

    @property
    def kms_key_arn(self) -> List[str]:
        kms_key_arns = []
        service_kms_key_ids = {
                'secretsmanager': 'cluster.secretsmanager.kms_key_id',
                'sqs': 'cluster.sqs.kms_key_id',
                'sns': 'cluster.sns.kms_key_id',
                'dynamodb': 'cluster.dynamodb.kms_key_id',
                'ebs': 'cluster.ebs.kms_key_id',
                'backup': 'cluster.backups.backup_vault.kms_key_id',
                }
        service_kms_key_arns = {
                'secretsmanager': self.kms_secretsmanager_key_arn,
                'sqs': self.kms_sqs_key_arn,
                'sns': self.kms_sns_key_arn,
                'dynamodb': self.kms_dynamodb_key_arn,
                'ebs': self.kms_ebs_key_arn,
                'backup': self.kms_backup_key_arn,
                }
        for service in service_kms_key_arns.keys():
            if self.config.get_string(service_kms_key_ids[service]) is not None:
                kms_key_arns.append(service_kms_key_arns[service])

        return kms_key_arns

    @property
    def user_pool_arn(self) -> str:
        return self.get_arn(service='cognito-idp',
                            resource=f'userpool/{self.config.get_string("identity-provider.cognito.user_pool_id")}',
                            aws_region=self.config.get_string("cluster.aws.region"))

    def get_directory_service_arn(self) -> str:
        return self.get_arn(service='ds',
                            resource=f'directory/{self.config.get_string("directoryservice.directory_id", required=True)}',
                            aws_region=self.config.get_string("cluster.aws.region"))

    def get_ddb_application_autoscaling_service_role_arn(self) -> str:
        return self.get_arn(service='iam', aws_region='', resource='role/aws-service-role/dynamodb.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_DynamoDBTable')

    def api_gateway_execute_api_arn(self, api_id: str, stage: str, http_verb: str, resource: str):
        return self.get_arn(service="execute-api", aws_region=self.config.get_string("cluster.aws.region"), resource=f'{api_id}/{stage}/{http_verb}/{resource}')

    def custom_credential_broker_api_gateway_execute_api_arn(self, api_id: str):
        return self.api_gateway_execute_api_arn(api_id, constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_STAGE, "GET", constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE)

