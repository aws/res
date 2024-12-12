#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

ENVIRONMENT_NAME_TAG_KEY = "res:EnvironmentName"

ADMIN_ROLE = "admin"
USER_ROLE = "user"
ENVIRONMENT_NAME_KEY = "environment_name"
DEFAULT_REGION_KEY = "AWS_DEFAULT_REGION"

PROJECT_ROLE_ASSIGNMENT_TYPE = "project"
VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES = [PROJECT_ROLE_ASSIGNMENT_TYPE]
ROLE_ASSIGNMENT_ACTOR_USER_TYPE = "user"
ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE = "group"
VALID_ROLE_ASSIGNMENT_ACTOR_TYPES = [
    ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
    ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
]
PROJECT_MEMBER_ROLE_ID = "project_member"
INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE = "Resource type value is not recognized"

# This regex is defined based on the POSIX username schema (https://systemd.io/USER_NAMES/) and
# SAM-Account-Name schema (https://learn.microsoft.com/en-us/windows/win32/adschema/a-samaccountname).
AD_SAM_ACCOUNT_NAME_MAX_LENGTH = 20
AD_SAM_ACCOUNT_NAME_REGEX = (
    rf"[a-zA-Z0-9_.][a-zA-Z0-9_.-]{{1,{AD_SAM_ACCOUNT_NAME_MAX_LENGTH}}}"
)

CLUSTER_ADMIN_USERNAME = "clusteradmin"
USERNAME_REGEX = rf"^{AD_SAM_ACCOUNT_NAME_REGEX}$"
USERNAME_ERROR_MESSAGE = (
    f"Username (SAM-Account-Name of the AD user) doesn't match the regex pattern {USERNAME_REGEX}. "
    f"Username may only contain lower and upper case ASCII letters, "
    f"digits, period, underscore, and hyphen, with the restriction that "
    f"hyphen is not allowed as first character of the username. "
    f"The maximum length of username is 20."
)

# The total allowable number of characters for group name is 65.
GROUP_NAME_REGEX = "^([a-zA-Z0-9_. -]){1,65}$"

CLUSTER_NETWORK_PRIVATE_SUBNETS = "cluster.network.private_subnets"
COGNITO_USER_POOL_PROVIDER_URL = "identity-provider.cognito.provider_url"
COGNITO_SSO_IDP_PROVIDER_NAME = "identity-provider.cognito.sso_idp_provider_name"

#
# Constants for AD Sync
#
AD_SYNC_LOCK_KEY = "ad-sync-lock"
AD_SYNC_TASK_DEFINITION = "ad-sync.task_definition"
AD_SYNC_TASK_CLUSTER = "ad-sync.task_cluster"
AD_SYNC_SECURITY_GROUP_ID = "ad-sync.security_group_id"
VPC_ID_KEY = "cluster.network.vpc_id"

AD_CONFIGURATION_REQUIRED_KEYS = [
    "directoryservice.ad_short_name",
    "directoryservice.computers.ou",
    "directoryservice.groups.ou",
    "directoryservice.ldap_base",
    "directoryservice.ldap_connection_uri",
    "directoryservice.name",
    "directoryservice.root_user_dn_secret_arn",
    "directoryservice.service_account_credentials_secret_arn",
    "directoryservice.users.ou",
    "directoryservice.sudoers.group_name",
]
SERVICE_ACCOUNT_USER_DN_KEY = "root_user_dn"
SERVICE_ACCOUNT_USER_DN_SECRET_ARN_KEY = "root_user_dn_secret_arn"
SERVICE_ACCOUNT_USER_DN_INPUT_PARAMETER_NAME = "ServiceAccountUserDN"

#
# Constants for RES resource tags
#
RES_TAG_PREFIX = "res:"
RES_TAG_MODULE_ID = RES_TAG_PREFIX + "ModuleId"
RES_TAG_ENVIRONMENT_NAME = RES_TAG_PREFIX + "EnvironmentName"
RES_TAG_MODULE_NAME = RES_TAG_PREFIX + "ModuleName"
RES_TAG_BACKUP_PLAN = RES_TAG_PREFIX + "BackupPlan"

BASTION_HOST_INSTANCE_AMI = "bastion-host.instance_ami"
BASTION_HOST_INSTANCE_TYPE = "bastion-host.instance_type"
CLUSTER_KEYPAIR_NAME = "cluster.network.ssh_key_pair"
BASTION_HOST_SECURITY_GROUP_ID = "cluster.network.security_groups.bastion-host"
PUBLIC_SUBNETS = "cluster.network.public_subnets"
BASTION_HOST_INSTANCE_ID = "bastion-host.instance_id"
BASTION_HOST_PRIVATE_IP = "bastion-host.private_ip"
BASTION_HOST_PUBLIC_IP = "bastion-host.public_ip"
BASTION_HOST_PRIVATE_DNS_NAME = "bastion-host.private_dns_name"
BASTION_HOST_PUBLIC = "bastion-host.public"
BASTION_HOST_BASE_OS = "bastion-host.base_os"
BASTION_HOST_VOLUME_SIZE = "bastion-host.volume_size"
BASTION_HOST_METADATA_HTTP_TOKENS = "bastion-host.metadata_http_tokens"
BASTION_HOST_HOSTNAME = "bastion-host.hostname"
CLUSTER_NETWORK_HTTPS_PROXY = "cluster.network.https_proxy"
CLUSTER_NETWORK_NO_PROXY = "cluster.network.no_proxy"
CLUSTER_ROUTE53_PRIVATE_HOSTED_ZONE_ID = "cluster.route53.private_hosted_zone_id"
CLUSTER_ROUTE53_PRIVATE_HOSTED_ZONE_NAME = "cluster.route53.private_hosted_zone_name"

BASTION_HOST_VOLUME_SIZE = "bastion-host.volume_size"
BASTION_HOST_KMS_KEY_ID = "bastion-host.kms_key_id"
BASTION_HOST_REQUIRE_IMDSV2 = "bastion-host.ec2.metadata_http_tokens"
BASTION_HOST_ENABLE_DETAILED_MONITORING = "bastion-host.ec2.enable_detailed_monitoring"
BASTION_HOST_ENABLE_TERMINATION_PROTECTION = (
    "bastion-host.ec2.enable_termination_protection"
)
BASTION_HOST_INSTANCE_PROFILE_NAME = "bastion-host.instance_profile_arn"
BASTION_HOST_USER_DATA = "bastion-host.user_data"
BASTION_HOST_IS_PUBLIC = "bastion-host.public"
CLUSTER_ADMINISTRATOR_EMAIL = "cluster.administrator_email"

SSO_USER_IDP_TYPE = "SSO"
COGNITO_USER_IDP_TYPE = "Native user"

AD_SYNC_LOCK_TABLE = "ad-sync.distributed-lock"
AD_AUTOMATION_TABLE_NAME = "ad-automation"
AD_AUTOMATION_DB_HASH_KEY = "instance_id"
AD_AUTOMATION_DB_RANGE_KEY = "nonce"
SNAPSHOT_TABLE_NAME = "snapshots"
SNAPSHOT_DB_HASH_KEY = "s3_bucket_name"
SNAPSHOT_DB_RANGE_KEY = "snapshot_path"
APPLY_SNAPSHOT_TABLE_NAME = "apply-snapshot"
APPLY_SNAPSHOT_DB_HASH_KEY = "apply_snapshot_identifier"
CLUSTER_MANAGER_LOCK_TABLE_NAME = "cluster-manager.distributed-lock"
EMAIL_TEMPLATE_TABLE_NAME = "email-templates"
EMAIL_TEMPLATE_DB_HASH_KEY = "name"
PERMISSION_PROFILE_TABLE_NAME = "vdc.controller.permission-profiles"
SSM_COMMAND_TABLE_NAME = "vdc.controller.ssm-commands"
SSM_COMMAND_DB_HASH_KEY = "command_id"
SOFTWARE_STACK_TABLE_NAME = "vdc.controller.software-stacks"
SOFTWARE_STACK_DB_HASH_KEY = "base_os"
SOFTWARE_STACK_DB_RANGE_KEY = "stack_id"
VDC_LOCK_TABLE_NAME = "vdc.distributed-lock"
LOCK_DB_HASH_KEY = "lock_key"
LOCK_DB_RANGE_KEY = "sort_key"

NODE_TYPE_APP = "app"

# Module IDs
MODULE_ID_VDC = "vdc"
MODULE_ID_CLUSTER_MANAGER = "cluster-manager"
MODULE_ID_DIRECTORY_SERVICE = "directoryservice"

# Module Names
MODULE_NAME_VDC = "virtual-desktop-controller"
MODULE_NAME_CLUSTER_MANAGER = "cluster-manager"
MODULE_NAME_DIRECTORY_SERVICE = "directoryservice"

# Module Mapping
MODULE_ID_NAME_MAPPING = {
    MODULE_ID_VDC: MODULE_NAME_VDC,
    MODULE_ID_CLUSTER_MANAGER: MODULE_NAME_CLUSTER_MANAGER,
    MODULE_ID_DIRECTORY_SERVICE: MODULE_NAME_DIRECTORY_SERVICE,
}

# Constants for Custom Domain
CUSTOM_DOMAIN_NAME_FOR_WEBAPP_KEY = (
    "cluster.load_balancers.external_alb.certificates.custom_dns_name"
)
CUSTOM_DOMAIN_NAME_FOR_VDI_KEY = (
    "vdc.dcv_connection_gateway.certificate.custom_dns_name"
)
