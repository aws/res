#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import List, Optional, Union

import aws_cdk as cdk

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.infra_utils.cluster_settings import ClusterSettings
from idea.infrastructure.install.parameters.parameters import RESParameters


class ArnBuilder:
    """
    Util class for building RES resource ARNs
    """

    def __init__(
        self,
        cluster_name: str,
        cluster_settings: ClusterSettings,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):
        self.cluster_name = cluster_name
        self.cluster_settings = cluster_settings
        self.parameters = parameters
        self.iam_resource_path = self.parameters.iam_resource_path_string
        self.iam_resource_prefix = self.parameters.iam_resource_prefix_string

    @staticmethod
    def build_arn(
        partition: Optional[str],
        service: Optional[str],
        region: Optional[str],
        account_id: Optional[str],
        resource: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_delimiter: str = "/",
    ) -> str:
        arn = f"arn:{partition}:{service}:{region}:{account_id}"
        if resource is not None:
            arn += f":{resource}"
        else:
            if resource_type is None:
                arn += f":{resource_id}"
            else:
                arn += f":{resource_type}{resource_delimiter}{resource_id}"
        return arn

    @staticmethod
    def get_arn(
        service: str,
        resource: str,
        account_id: str = cdk.Aws.ACCOUNT_ID,
        region: str = cdk.Aws.REGION,
    ) -> str:
        return ArnBuilder.build_arn(
            partition=cdk.Aws.PARTITION,
            service=service,
            region=region,
            account_id=account_id,
            resource=resource,
        )

    def get_elastic_load_balancer_arn(self, name: str) -> str:
        return self.get_arn(service="elasticloadbalancing", resource=f"{name}")

    def get_iam_role_arn(self, role_name: str) -> str:
        return self.get_arn(
            service="iam",
            resource=f"role{self.parameters.iam_resource_path_string}{self.parameters.iam_resource_prefix_string}{role_name}",
            region="",
        )

    @property
    @lru_cache
    def get_ddb_table_export_arn(self) -> str:
        return self.get_arn(
            service="dynamodb",
            resource=f"table/{self.cluster_name}.*/export/*",
        )

    def get_ddb_table_arn(self, table_name_suffix: str) -> str:
        return self.get_arn(
            service="dynamodb",
            resource=f"table/{self.cluster_name}.{table_name_suffix}",
        )

    def get_lambda_log_group_arn(self, suffix: str) -> str:
        return self.get_arn(
            service="logs",
            resource=f"log-group:/aws/lambda/{self.cluster_name}{suffix}",
        )

    def get_log_group_arn(self, suffix: str) -> str:
        return self.get_arn(
            service="logs", resource=f"log-group:/{self.cluster_name}{suffix}"
        )

    def get_lambda_function_arn(self, name: str) -> str:
        return self.get_arn(service="lambda", resource=f"function:{name}")

    @property
    @lru_cache
    def lambda_log_stream_arn(self) -> str:
        return self.get_arn(
            service="logs",
            resource=f"log-group:/aws/lambda/{self.cluster_name}*:log-stream:*",
        )

    @property
    @lru_cache
    def s3_global_arns(self) -> List[str]:
        return [
            ArnBuilder.get_arn("s3", f"dcv-license.{cdk.Aws.REGION}/*", "", ""),
            ArnBuilder.get_arn("s3", "ec2-linux-nvidia-drivers/*", "", ""),
            ArnBuilder.get_arn("s3", "ec2-linux-nvidia-drivers", "", ""),
            ArnBuilder.get_arn("s3", "nvidia-gaming/*", "", ""),
            ArnBuilder.get_arn("s3", "nvidia-gaming-drivers", "", ""),
            ArnBuilder.get_arn("s3", "nvidia-gaming-drivers/*", "", ""),
            ArnBuilder.get_arn("s3", "ec2-amd-linux-drivers/*", "", ""),
            ArnBuilder.get_arn("s3", "ec2-amd-linux-drivers", "", ""),
            ArnBuilder.get_arn("s3", "ec2-windows-nvidia-drivers", "", ""),
            ArnBuilder.get_arn("s3", "ec2-windows-nvidia-drivers/*", "", ""),
            ArnBuilder.get_arn("s3", "ec2-amd-windows-drivers", "", ""),
            ArnBuilder.get_arn("s3", "ec2-amd-windows-drivers/*", "", ""),
        ]

    def get_s3_bucket_arns(self, bucket_name: str) -> List[str]:
        return [
            ArnBuilder.get_arn("s3", f"{bucket_name}/*", "", ""),
            ArnBuilder.get_arn("s3", bucket_name, "", ""),
        ]

    @property
    @lru_cache
    def s3_public_host_modules(self) -> List[str]:
        return [
            ArnBuilder.get_arn(
                "s3",
                f"{constants.ARTIFACTS_BUCKET_PREFIX_NAME}-{cdk.Aws.REGION}/host_modules/*",
                "",
                "",
            )
        ]

    @property
    @lru_cache
    def dcv_license_s3_bucket_arns(self) -> List[str]:
        return [
            ArnBuilder.get_arn(
                service="s3", resource="dcv-license.*/*", region="", account_id=""
            ),
            ArnBuilder.get_arn(
                service="s3", resource="dcv-license.*", region="", account_id=""
            ),
        ]

    @property
    @lru_cache
    def s3_bucket_arns(self) -> List[str]:
        return [
            self.get_arn(
                service="s3",
                region="",
                account_id="",
                resource=f"{self.cluster_settings.staging_bucket}/*",
            ),
            self.get_arn(
                service="s3",
                region="",
                account_id="",
                resource=self.cluster_settings.staging_bucket,  # type: ignore
            ),
        ]

    @property
    @lru_cache
    def cluster_config_ddb_arn(self) -> List[str]:
        return [
            self.get_arn(
                service="dynamodb",
                resource=f"table/{self.cluster_name}.cluster-settings",
            ),
            self.get_arn(
                service="dynamodb",
                resource=f"table/{self.cluster_name}.cluster-settings/stream/*",
            ),
            self.get_arn(
                service="dynamodb", resource=f"table/{self.cluster_name}.modules"
            ),
        ]

    def get_ddb_table_stream_arn(self, table_name_suffix: str) -> str:
        return self.get_arn(
            service="kinesis",
            resource=f"stream/{self.cluster_name}.{table_name_suffix}-kinesis-stream",
        )

    def get_sns_arn(self, topic_name_suffix: str) -> str:
        return self.get_arn(
            service="sns", resource=f"{self.cluster_name}-{topic_name_suffix}"
        )

    def get_ecs_cluster_arn(self, name: str) -> str:
        return self.get_arn(service="ecs", resource=f"cluster/{name}")

    def get_sqs_arn(self, queue_name_suffix: str) -> str:
        return self.get_arn(
            service="sqs", resource=f"{self.cluster_name}-{queue_name_suffix}"
        )

    def get_iam_arn(
        self,
        role_name_suffix: str,
    ) -> str:

        return self.get_arn(
            service="iam",
            resource=f"role{self.iam_resource_path}{self.iam_resource_prefix}{self.cluster_settings.cluster_name}-{role_name_suffix}",
            region="",
        )

    def get_instance_profile_arn(
        self,
        profile_name_suffix: str,
    ) -> str:
        return self.get_arn(
            service="iam",
            resource=f"instance-profile{self.iam_resource_path}{self.iam_resource_prefix}{self.cluster_settings.cluster_name}-{profile_name_suffix}",
            region="",
        )

    def get_instance_profile_arn_from_ref(
        self,
        instance_profile_ref: str,
    ) -> str:
        return self.get_arn(
            service="iam",
            resource=f"instance-profile{self.iam_resource_path}{instance_profile_ref}",
            region="",
        )

    def get_policy_arn(
        self,
        name: str,
    ) -> str:
        return self.get_arn(
            service="iam",
            resource=f"policy{self.iam_resource_path}{self.iam_resource_prefix}{name}",
            region="",
        )

    def get_eventbridge_rule_arn(self, name: str = "*") -> str:
        return self.get_arn(service="events", resource=f"rule/{name}")

    @property
    @lru_cache
    def kms_secretsmanager_key_arn(self) -> str:
        return self.get_arn(
            service="kms",
            resource=f"key/{self.cluster_settings.kms_secretsmanager_key_id}",
        )

    @property
    def get_security_group_arn(self) -> str:
        return self.get_arn(service="ec2", resource="security-group/*")

    @property
    def get_security_group_rule_arn(self) -> str:
        return self.get_arn(service="ec2", resource="security-group-rule/*")

    @property
    @lru_cache
    def kms_sqs_key_arn(self) -> str:
        return self.get_arn(
            service="kms", resource=f"key/{self.cluster_settings.kms_sqs_key_id}"
        )

    @lru_cache
    def kms_sns_key_arn(self, key_id: str = "") -> str:
        if not key_id:
            key_id = self.cluster_settings.kms_sns_key_id
        return self.get_arn(service="kms", resource=f"key/{key_id}")

    @property
    @lru_cache
    def kms_dynamodb_key_arn(self) -> str:
        return self.get_arn(
            service="kms", resource=f"key/{self.cluster_settings.kms_dynamodb_key_id}"
        )

    @property
    @lru_cache
    def kms_ebs_key_arn(self) -> str:
        return self.get_arn(
            service="kms", resource=f"key/{self.cluster_settings.kms_ebs_key_id}"
        )

    @property
    @lru_cache
    def kms_backup_key_arn(self) -> str:
        return self.get_arn(
            service="kms", resource=f"key/{self.cluster_settings.kms_backup_key_id}"
        )

    @property
    @lru_cache
    def kms_key_arns(self) -> List[str]:
        kms_key_arns = []
        service_kms_key_arns = {
            "secretsmanager": self.kms_secretsmanager_key_arn,
            "sqs": self.kms_sqs_key_arn,
            "sns": self.kms_sns_key_arn,
            "dynamodb": self.kms_dynamodb_key_arn,
            "ebs": self.kms_ebs_key_arn,
            "backup": self.kms_backup_key_arn,
        }
        for service_arn in service_kms_key_arns.values():
            if service_arn:
                kms_key_arns.append(service_arn)

        return kms_key_arns  # type: ignore

    @property
    @lru_cache
    def user_pool_arn(self) -> str:
        return ArnBuilder.get_arn(
            service="cognito-idp",
            resource=f"userpool/{self.cluster_settings.user_pool_id}",
        )

    @staticmethod
    def api_gateway_execute_api_arn(
        api_id: str, stage: str, http_verb: str, resource: str
    ) -> str:
        return ArnBuilder.get_arn(
            service="execute-api", resource=f"{api_id}/{stage}/{http_verb}/{resource}"
        )

    @staticmethod
    def get_secretmanager_secret_arn(name: str) -> str:
        return ArnBuilder.get_arn(service="secretsmanager", resource=f"secret:{name}*")

    def get_vdi_iam_role_arn(self, project_name: str) -> str:
        return ArnBuilder.get_arn(
            service="iam",
            resource=f"role{self.iam_resource_path}{self.cluster_name}-{cdk.Aws.REGION}/vdi/{self.iam_resource_prefix}{self.cluster_name}-vdi-{project_name}",
            region="",
        )

    def get_vdi_iam_instance_profile_arn(self, project_name: str) -> str:
        return self.get_arn(
            service="iam",
            region="",
            resource=f"instance-profile{self.iam_resource_path}{self.cluster_name}-{cdk.Aws.REGION}/vdi/{self.iam_resource_prefix}{self.cluster_name}-vdi-{project_name}",
        )

    @property
    @lru_cache
    def get_route53_hostedzone_arn(self) -> str:
        return ArnBuilder.get_arn("route53", "hostedzone/*", "", "")

    @property
    @lru_cache
    def custom_credential_broker_api_gateway_execute_get_api_arn(self) -> str:
        return ArnBuilder.api_gateway_execute_api_arn(
            "*",
            constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_STAGE,
            "GET",
            constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE,
        )

    @property
    @lru_cache
    def custom_credential_broker_api_gateway_execute_post_api_arn(self) -> str:
        return ArnBuilder.api_gateway_execute_api_arn(
            "*",
            constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_STAGE,
            "POST",
            constants.API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE,
        )

    @property
    @lru_cache
    def get_kinesis_arn(self) -> str:
        return self.get_arn(service="kinesis", resource=f"stream/{self.cluster_name}-*")

    @property
    @lru_cache
    def get_ddb_application_autoscaling_service_role_arn(self) -> str:
        return ArnBuilder.get_arn(
            service="iam",
            resource="role/aws-service-role/dynamodb.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_DynamoDBTable",
            region="",
        )

    @property
    @lru_cache
    def vdi_helper_api_gateway_execute_api_arn(self) -> str:
        return ArnBuilder.api_gateway_execute_api_arn(
            "*",
            constants.API_GATEWAY_VDI_HELPER_STAGE,
            "POST",
            constants.API_GATEWAY_VDI_HELPER_RESOURCE,
        )
