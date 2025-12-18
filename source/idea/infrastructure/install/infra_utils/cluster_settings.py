#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from functools import lru_cache
from typing import Any, Dict, List

import constructs

from idea.infrastructure.install.infra_utils.utils import InfraUtils

STATIC_SETTINGS: Dict[str, Any] = {
    "cluster": {
        "network": {"cluster_prefix_list_max_entries": 10},
        "secretsmanager": {"kms_key_id": ""},
        "sqs": {"kms_key_id": ""},
        "sns": {"kms_key_id": ""},
        "ebs": {"kms_key_id": ""},
        "backup_vault": {"kms_key_id": ""},
        "dynamodb": {"kms_key_id": ""},
        "kms": {
            "key_type": "aws-managed",
        },
        "iam": {
            # IAM policy ARNs provided below will be attached to all IAM roles for EC2 Instances launched by RES.
            "ec2_managed_policy_arns": [],
        },
        "load_balancers": {
            "external_alb": {
                "access_logs": True,
                "ssl_policy": "ELBSecurityPolicy-TLS13-1-2-2021-06",
            },
            "internal_alb": {
                "access_logs": True,
                "ssl_policy": "ELBSecurityPolicy-TLS13-1-2-2021-06",
            },
        },
        "base_os": "amzn2023",
    },
    "virtual-desktop-controller": {
        "dcv_broker": {
            "client_communication_port": 8444,
            "agent_communication_port": 8445,
            "gateway_communication_port": 8446,
            "ssl_policy": "ELBSecurityPolicy-TLS13-1-2-2021-06",
        },
    },
    "identity-provider": {
        "cognito": {"removal_policy": "DESTROY", "advanced_security_mode": "AUDIT"},
    },
    "shared-storage": {
        "internal": {
            "efs": {
                "encrypted": True,
                "throughput_mode": "bursting",
                "performance_mode": "generalPurpose",
                "kms_key_id": None,
                "removal_policy": "DESTROY",
                "cloudwatch_monitoring": True,
                "transition_to_ia": None,
            }
        }
    },
    "global-settings": {
        "package_config": {
            "host_modules": {
                "nss": ["libnss_cognito"],
                "pam": ["pam_cognito", "ssh_keygen"],
            }
        },
    },
}


class ClusterSettings:
    """
    Util class for retrieving cluster settings
    """

    def __init__(self, cluster_name: str, scope: constructs.Construct):
        self.cluster_name = cluster_name
        self.scope = scope
        self.static_settings = STATIC_SETTINGS

    @property
    def shared_storage_efs_config(self) -> Any:
        return (
            self.static_settings.get("shared-storage", {})
            .get("internal", {})
            .get("efs", {})
        )

    @property
    def kms_secretsmanager_key_id(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("secretsmanager", {})
            .get("kms_key_id", "")
        )

    @property
    def kms_sns_key_id(self) -> Any:
        return (
            self.static_settings.get("cluster", {}).get("sns", {}).get("kms_key_id", "")
        )

    @property
    def kms_sqs_key_id(self) -> Any:
        return (
            self.static_settings.get("cluster", {}).get("sqs", {}).get("kms_key_id", "")
        )

    @property
    def kms_ebs_key_id(self) -> Any:
        return (
            self.static_settings.get("cluster", {}).get("ebs", {}).get("kms_key_id", "")
        )

    @property
    def kms_backup_key_id(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("backup_vault", {})
            .get("kms_key_id", "")
        )

    @property
    def kms_dynamodb_key_id(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("dynamodb", {})
            .get("kms_key_id", "")
        )

    @property
    @lru_cache
    def user_pool_id(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "identity-provider.cognito.user_pool_id",
            self.cluster_name,
        )

    @property
    @lru_cache
    def private_hosted_zone_name(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.route53.private_hosted_zone_name",
            self.cluster_name,
        )

    @property
    def kms_key_type(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("kms", {})
            .get("key_type", "aws-managed")
        )

    @property
    @lru_cache
    def certificate_secret_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.load_balancers.external_alb.certificates.certificate_secret_arn",
            self.cluster_name,
        )

    @property
    @lru_cache
    def private_key_secret_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.load_balancers.external_alb.certificates.private_key_secret_arn",
            self.cluster_name,
        )

    @property
    @lru_cache
    def external_alb_enable_access_log(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("load_balancers", {})
            .get("external_alb", {})
            .get("access_logs", False)
        )

    @property
    @lru_cache
    def internal_alb_enable_access_log(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("load_balancers", {})
            .get("internal_alb", {})
            .get("access_logs", False)
        )

    @property
    @lru_cache
    def external_alb_listener_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.load_balancers.external_alb.https_listener_arn",
            self.cluster_name,
        )

    @property
    @lru_cache
    def external_alb_ssl_policy(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("load_balancers", {})
            .get("external_alb", {})
            .get(
                "ssl_policy",
                "ELBSecurityPolicy-TLS13-1-2-2021-06",
            )
        )

    @property
    @lru_cache
    def dcv_broker_ssl_policy(self) -> Any:
        return (
            self.static_settings.get("virtual-desktop-controller", {})
            .get("dcv_broker", {})
            .get(
                "ssl_policy",
                "ELBSecurityPolicy-TLS13-1-2-2021-06",
            )
        )

    @property
    @lru_cache
    def internal_alb_ssl_policy(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("load_balancers", {})
            .get("internal_alb", {})
            .get(
                "ssl_policy",
                "ELBSecurityPolicy-TLS13-1-2-2021-06",
            )
        )

    @property
    def cluster_prefix_list_max_entries(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("network", {})
            .get("cluster_prefix_list_max_entries", 10)
        )

    @property
    def cognito_removal_policy(self) -> Any:
        return (
            self.static_settings.get("identity-provider", {})
            .get("cognito", {})
            .get("removal_policy", "DESTROY")
        )

    @property
    @lru_cache
    def client_ips(self) -> List[str]:
        return InfraUtils.get_cluster_setting_array(
            self.scope,
            "cluster.network.client_ip",
            self.cluster_name,
        )

    @property
    @lru_cache
    def logging_bucket(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.logging_bucket_name",
            self.cluster_name,
        )

    @property
    @lru_cache
    def staging_bucket(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.staging_bucket_name",
            self.cluster_name,
        )

    @property
    @lru_cache
    def installation_scripts_uri(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.installation_scripts_uri",
            self.cluster_name,
        )

    @property
    @lru_cache
    def external_acm_certificate_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.load_balancers.external_alb.certificates.acm_certificate_arn",
            self.cluster_name,
        )

    @property
    @lru_cache
    def dcv_broker_client_listener_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.load_balancers.internal_alb.dcv_broker_client_listener_arn",
            self.cluster_name,
        )

    @property
    def dcv_broker_client_communication_port(self) -> Any:
        return (
            self.static_settings.get("virtual-desktop-controller", {})
            .get("dcv_broker", {})
            .get("client_communication_port", 8444)
        )

    @property
    @lru_cache
    def dcv_broker_agent_listener_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.load_balancers.internal_alb.dcv_broker_agent_listener_arn",
            self.cluster_name,
        )

    @property
    def dcv_broker_agent_communication_port(self) -> Any:
        return (
            self.static_settings.get("virtual-desktop-controller", {})
            .get("dcv_broker", {})
            .get("agent_communication_port", 8445)
        )

    @property
    @lru_cache
    def dcv_broker_gateway_listener_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.load_balancers.internal_alb.dcv_broker_gateway_listener_arn",
            self.cluster_name,
        )

    @property
    def dcv_broker_gateway_communication_port(self) -> Any:
        return (
            self.static_settings.get("virtual-desktop-controller", {})
            .get("dcv_broker", {})
            .get("gateway_communication_port", 8446)
        )

    @property
    @lru_cache
    def load_balancer_subnets(self) -> List[str]:
        return InfraUtils.get_cluster_setting_array(
            self.scope,
            "cluster.network.load_balancer_subnets",
            self.cluster_name,
        )

    @property
    @lru_cache
    def infrastructure_host_subnets(self) -> List[str]:
        return InfraUtils.get_cluster_setting_array(
            self.scope,
            "cluster.network.infrastructure_host_subnets",
            self.cluster_name,
        )

    @property
    @lru_cache
    def vdi_subnets(self) -> List[str]:
        return InfraUtils.get_cluster_setting_array(
            self.scope,
            "vdc.dcv_session.network.private_subnets",
            self.cluster_name,
        )

    @property
    @lru_cache
    def log_retention_role_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.iam.roles.log-retention",
            self.cluster_name,
        )

    @property
    @lru_cache
    def random_uuid(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "cluster.random-uuid",
            self.cluster_name,
        )

    @property
    def ec2_managed_policy_arns(self) -> Any:
        return (
            self.static_settings.get("cluster", {})
            .get("iam", {})
            .get("ec2_managed_policy_arns", [])
        )

    @property
    @lru_cache
    def host_modules_pam(self) -> Any:
        return (
            self.static_settings.get("global-settings", {})
            .get("package_config", {})
            .get("host_modules", {})
            .get("pam", [])
        )

    @property
    @lru_cache
    def host_modules_nss(self) -> Any:
        return (
            self.static_settings.get("global-settings", {})
            .get("package_config", {})
            .get("host_modules", {})
            .get("nss", [])
        )

    @property
    @lru_cache
    def tls_certificate_secret_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "directoryservice.tls_certificate_secret_arn",
            self.cluster_name,
        )

    @property
    @lru_cache
    def service_account_credentials_secret_arn(self) -> str:
        return InfraUtils.get_cluster_setting_string(
            self.scope,
            "directoryservice.service_account_credentials_secret_arn",
            self.cluster_name,
        )

    @staticmethod
    def base_os() -> Any:
        return STATIC_SETTINGS.get("cluster", {}).get("base_os", "")

    @staticmethod
    def get_ec2_block_device_name() -> str:
        if ClusterSettings.base_os() in ["amazonlinux2", "amzn2023"]:
            return "/dev/xvda"
        else:
            return "/dev/sda1"
