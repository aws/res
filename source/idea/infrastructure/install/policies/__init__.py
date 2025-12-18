#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from idea.infrastructure.install.policies.active_directory_policy import (
    ActiveDirectoryPolicy,
)
from idea.infrastructure.install.policies.ad_sync_task_policy import ADSyncTaskPolicy
from idea.infrastructure.install.policies.add_nat_eips_to_alb_security_group_policy import (
    AddNatEipsToAlbSecurityGroupPolicy,
)
from idea.infrastructure.install.policies.add_peer_ingress_rule_policy import (
    AddPeerIngressRulePolicy,
)
from idea.infrastructure.install.policies.add_to_user_pool_client_scopes_policy import (
    AddToUserpoolClientScopesPolicy,
)
from idea.infrastructure.install.policies.amazon_ssm_managed_instance_core_policy import (
    AmazonSsmManagedInstanceCorePolicy,
)
from idea.infrastructure.install.policies.backend_lambda_policy import (
    BackendLambdaPolicy,
)
from idea.infrastructure.install.policies.bastion_host_cleanup_policy import (
    BastionHostCleanupPolicy,
)
from idea.infrastructure.install.policies.bastion_host_policy import BastionHostPolicy
from idea.infrastructure.install.policies.clean_up_resources_policy import (
    CleanupResources,
)
from idea.infrastructure.install.policies.cloud_watch_agent_server_policy import (
    CloudWatchAgentServerPolicy,
)
from idea.infrastructure.install.policies.cluster_endpoints_policy import (
    ClusterEndpointsPolicy,
)
from idea.infrastructure.install.policies.cluster_manager_policy import (
    ClusterManagerPolicy,
)
from idea.infrastructure.install.policies.cognito_sync_policy import CognitoSyncPolicy
from idea.infrastructure.install.policies.cognito_trigger_workflow_create_post_auth_policy import (
    CognitoTriggerWorkflowCreatePostAuthPolicy,
)
from idea.infrastructure.install.policies.cognito_trigger_workflow_create_uid_policy import (
    CognitoTriggerWorkflowCreateUidPolicy,
)
from idea.infrastructure.install.policies.configure_sso_lambda_policy import (
    ConfigureSSOLambdaPolicy,
)
from idea.infrastructure.install.policies.controller_scheduled_event_transformer_lambda_policy import (
    ControllerScheduledEventTransformerLambdaPolicy,
)
from idea.infrastructure.install.policies.controller_ssm_command_pass_role_policy import (
    ControllerSSMCommandPassRolePolicy,
)
from idea.infrastructure.install.policies.custom_credential_broker_policy import (
    CustomCredentialBrokerPolicy,
)
from idea.infrastructure.install.policies.custom_kms_key_policy import (
    CustomKmsKeyPolicy,
)
from idea.infrastructure.install.policies.detach_vpc_from_lambda_policy import (
    DetachVpcFromLambdaPolicy,
)
from idea.infrastructure.install.policies.disable_cognito_protection_policy import (
    DisableCognitoProtectionPolicy,
)
from idea.infrastructure.install.policies.ec2_state_event_transformer_policy import (
    Ec2StateEventTransformerPolicy,
)
from idea.infrastructure.install.policies.get_alb_listener_default_actions_policy import (
    GetAlbListenerDefaultActionsPolicy,
)
from idea.infrastructure.install.policies.get_user_pool_client_secret_policy import (
    GetUserPoolClientSecretPolicy,
)
from idea.infrastructure.install.policies.lambda_basic_execution_policy import (
    LambdaBasicExecutionPolicy,
)
from idea.infrastructure.install.policies.log_retention_policy import LogRetentionPolicy
from idea.infrastructure.install.policies.params_transformer_policy import (
    ParamsTransformerPolicy,
)
from idea.infrastructure.install.policies.populate_custom_tags_policy import (
    PopulateCustomTagsPolicy,
)
from idea.infrastructure.install.policies.proxy_lambda_assume_role_policy import (
    ProxyLambdaAssumeRolePolicy,
)
from idea.infrastructure.install.policies.proxy_lambda_policy import ProxyLambdaPolicy
from idea.infrastructure.install.policies.s3_mount_base_bucket_read_only_policy import (
    S3MountBaseBucketReadOnlyPolicy,
)
from idea.infrastructure.install.policies.s3_mount_base_bucket_read_write_policy import (
    S3MountBaseBucketReadWritePolicy,
)
from idea.infrastructure.install.policies.scheduled_ad_sync_policy import (
    ScheduledADSyncPolicy,
)
from idea.infrastructure.install.policies.self_signed_certificate_policy import (
    SelfSignedCertificatePolicy,
)
from idea.infrastructure.install.policies.shared_efs_file_storage_policy import (
    SharedEfsFileStoragePolicy,
)
from idea.infrastructure.install.policies.tag_resources_policy import TagResourcesPolicy
from idea.infrastructure.install.policies.terminate_ad_sync_task_policy import (
    TerminateADSyncTaskPolicy,
)
from idea.infrastructure.install.policies.update_cluster_prefix_list_policy import (
    UpdateClusterPrefixListPolicy,
)
from idea.infrastructure.install.policies.update_cluster_settings_policy import (
    UpdateClusterSettingsPolicy,
)
from idea.infrastructure.install.policies.vdc_controller_sqs_kms_key_policy import (
    VdcControllerSqsKmsKeyPolicy,
)
from idea.infrastructure.install.policies.vdi_helper_policy import VdiHelperPolicy
from idea.infrastructure.install.policies.virtual_desktop_broker_policy import (
    VirtualDesktopBrokerPolicy,
)
from idea.infrastructure.install.policies.virtual_desktop_connection_gateway_policy import (
    VirtualDesktopConnectionGatewayPolicy,
)
from idea.infrastructure.install.policies.virtual_desktop_controller_policy import (
    VirtualDesktopControllerPolicy,
)
from idea.infrastructure.install.policies.virtual_desktop_dcv_host_policy import (
    VirtualDesktopDcvPolicy,
)
from idea.infrastructure.install.policies.virtual_desktop_dcv_host_scoped_down_policy import (
    VirtualDesktopDcvHostScopedDownPolicy,
)
from idea.infrastructure.install.policies.vpc_lookup_policy import VpcLookupPolicy

__all__ = [
    "ProxyLambdaPolicy",
    "ProxyLambdaAssumeRolePolicy",
    "BackendLambdaPolicy",
    "CognitoTriggerWorkflowCreateUidPolicy",
    "CognitoTriggerWorkflowCreatePostAuthPolicy",
    "AmazonSsmManagedInstanceCorePolicy",
    "ActiveDirectoryPolicy",
    "AddNatEipsToAlbSecurityGroupPolicy",
    "AddPeerIngressRulePolicy",
    "AddToUserpoolClientScopesPolicy",
    "ADSyncTaskPolicy",
    "BastionHostPolicy",
    "BastionHostCleanupPolicy",
    "CleanupResources",
    "ClusterEndpointsPolicy",
    "ClusterManagerPolicy",
    "CloudWatchAgentServerPolicy",
    "CognitoSyncPolicy",
    "ConfigureSSOLambdaPolicy",
    "ControllerScheduledEventTransformerLambdaPolicy",
    "ControllerSSMCommandPassRolePolicy",
    "CustomCredentialBrokerPolicy",
    "CustomKmsKeyPolicy",
    "DetachVpcFromLambdaPolicy",
    "DisableCognitoProtectionPolicy",
    "Ec2StateEventTransformerPolicy",
    "GetAlbListenerDefaultActionsPolicy",
    "GetUserPoolClientSecretPolicy",
    "LambdaBasicExecutionPolicy",
    "LogRetentionPolicy",
    "ScheduledADSyncPolicy",
    "SelfSignedCertificatePolicy",
    "SharedEfsFileStoragePolicy",
    "S3MountBaseBucketReadOnlyPolicy",
    "S3MountBaseBucketReadWritePolicy",
    "TerminateADSyncTaskPolicy",
    "UpdateClusterPrefixListPolicy",
    "UpdateClusterSettingsPolicy",
    "VdcControllerSqsKmsKeyPolicy",
    "VdiHelperPolicy",
    "VirtualDesktopBrokerPolicy",
    "VirtualDesktopConnectionGatewayPolicy",
    "VirtualDesktopControllerPolicy",
    "VirtualDesktopDcvHostScopedDownPolicy",
    "VirtualDesktopDcvPolicy",
    "VpcLookupPolicy",
    "PopulateCustomTagsPolicy",
    "TagResourcesPolicy",
    "ParamsTransformerPolicy",
]
