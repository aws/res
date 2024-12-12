#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Any, Dict, Union

import aws_cdk as cdk
import constructs
from aws_cdk import CfnJson, Fn, RemovalPolicy, SecretValue, Tags
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import custom_resources as cr
from res.constants import (  # type: ignore
    ENVIRONMENT_NAME_KEY,
    ENVIRONMENT_NAME_TAG_KEY,
    MODULE_ID_DIRECTORY_SERVICE,
    MODULE_NAME_DIRECTORY_SERVICE,
    RES_TAG_BACKUP_PLAN,
    RES_TAG_ENVIRONMENT_NAME,
    RES_TAG_MODULE_ID,
    RES_TAG_MODULE_NAME,
)
from res.resources import (  # type: ignore
    cluster_settings,
    email_templates,
    modules,
    permission_profiles,
    software_stacks,
)

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import utils
from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.ddb_tables.base import RESDDBTableBase
from idea.infrastructure.install.ddb_tables.list import ddb_tables_list
from idea.infrastructure.install.handlers import installer_handlers
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.customdomain import CustomDomainKey
from idea.infrastructure.install.parameters.directoryservice import DirectoryServiceKey
from idea.infrastructure.install.parameters.internet_proxy import InternetProxyKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.parameters.shared_storage import SharedStorageKey
from idea.infrastructure.install.utils import InfraUtils


class ResBaseStack(ResBaseConstruct):
    def __init__(
        self,
        scope: constructs.Construct,
        shared_library_lambda_layer: lambda_.LayerVersion,
        params_transformer: cdk.CustomResource,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):
        self.parameters = parameters
        self.params_transformer = params_transformer
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        self.shared_library_lambda_layer = shared_library_lambda_layer
        self.shared_library_arn = shared_library_lambda_layer.layer_version_arn
        super().__init__(
            self.cluster_name,
            cdk.Aws.REGION,
            "res-base",
            scope,
            self.parameters,
        )

        baseStack = self.nested_stack = cdk.NestedStack(
            scope,
            "res-base",
            description="Nested RES Base Stack",
        )

        for table in ddb_tables_list:
            RESDDBTableBase(
                self.nested_stack,
                table.id,
                self.cluster_name,
                table,
            )

        dcvBrokerTableDeltionPolicy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["dynamodb:DeleteTable"],
                    resources=[
                        f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/{self.cluster_name}.vdc.dcv-broker*"
                    ],
                ),
                iam.PolicyStatement(
                    actions=["dynamodb:ListTables"],
                    resources=[
                        f"arn:{cdk.Aws.PARTITION}:dynamodb:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:table/*"
                    ],
                ),
            ]
        )
        dcvBrokerTableDeltionRole = iam.Role(
            self,
            "DcvBrokerTableDeltionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
            inline_policies={"DDBPolicy": dcvBrokerTableDeltionPolicy},
        )

        dcvBrokerTableDeletionLambda = lambda_.Function(
            baseStack,
            "dcvBrokerTableDeletionLambda",
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            description="Lambda to handle deletion of the NICE DCV Broker tables",
            role=dcvBrokerTableDeltionRole,
            **utils.InfraUtils.get_handler_and_code_for_function(
                installer_handlers.delete_dcv_broker_tables
            ),
        )
        provider = cr.Provider(
            self,
            "dcvBrokerTableDeletionProvider",
            on_event_handler=dcvBrokerTableDeletionLambda,
        )
        cdk.CustomResource(
            self,
            "dcvBrokerTableDeletionCustomResource",
            service_token=provider.service_token,
            properties={"environment_name": self.cluster_name},
        )

        self.parameters.root_user_dn_secret_arn = self.get_directory_service_secret_arn(
            DirectoryServiceKey.ROOT_USER_DN
        )
        self.populator_custom_resource = self.populate_default_values()
        self.create_bucket()
        self.apply_permission_boundary(self.nested_stack)

    def get_directory_service_secret_arn(self, key: DirectoryServiceKey) -> str:
        scope = self.nested_stack
        service_account_dn_provided = cdk.CfnCondition(
            scope,
            "ServiceAccountDNProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(self.parameters.get(key), ""),
            ),
        )

        secret = secretsmanager.Secret(
            scope,
            id=f"DirectoryServiceSecret{key}",
            secret_name=f"{self.cluster_name}-{MODULE_NAME_DIRECTORY_SERVICE}-{key}",
            secret_string_value=SecretValue.cfn_parameter(self.parameters.get(key)),
        )

        Tags.of(secret).add(
            key=ENVIRONMENT_NAME_TAG_KEY,
            value=self.cluster_name,
        )
        Tags.of(secret).add(
            key=RES_TAG_MODULE_NAME,
            value=MODULE_NAME_DIRECTORY_SERVICE,
        )
        Tags.of(secret).add(
            key=RES_TAG_MODULE_ID,
            value=MODULE_ID_DIRECTORY_SERVICE,
        )
        raw_secret = secret.node.default_child
        raw_secret.cfn_options.condition = service_account_dn_provided  # type: ignore

        return Fn.condition_if(
            service_account_dn_provided.logical_id,
            secret.secret_arn,
            cdk.Aws.NO_VALUE,
        ).to_string()

    def populate_default_values(self) -> cdk.CustomResource:
        lambda_name = f"{self.cluster_name}-DDBDefaultValuesPopulator"
        scope = self.nested_stack
        ddb_default_values_populator_role = iam.Role(
            scope,
            id="DDBDefaultValuesPopulatorRole",
            role_name=f"{lambda_name}Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        ddb_default_values_populator_role_policy = iam.Policy(
            scope,
            id="DDBDefaultValuesPopulatorRolePolicy",
            policy_name=f"{lambda_name}Policy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DeleteLogStream",
                    ],
                    sid="CloudWatchLogStreamPermissions",
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["dynamodb:Scan", "dynamodb:GetItem", "dynamodb:PutItem"],
                    resources=[
                        InfraUtils.get_ddb_table_arn(
                            self.cluster_name,
                            cluster_settings.CLUSTER_SETTINGS_TABLE_NAME,
                        ),
                        InfraUtils.get_ddb_table_arn(
                            self.cluster_name,
                            modules.MODULES_TABLE_NAME,
                        ),
                        InfraUtils.get_ddb_table_arn(
                            self.cluster_name,
                            permission_profiles.PERMISSION_PROFILE_TABLE_NAME,
                        ),
                        InfraUtils.get_ddb_table_arn(
                            self.cluster_name,
                            software_stacks.SOFTWARE_STACK_TABLE_NAME,
                        ),
                        InfraUtils.get_ddb_table_arn(
                            self.cluster_name,
                            email_templates.EMAIL_TEMPLATE_TABLE_NAME,
                        ),
                    ],
                ),
            ],
        )
        ddb_default_values_populator_role.attach_inline_policy(
            ddb_default_values_populator_role_policy
        )
        self.add_common_tags(ddb_default_values_populator_role)

        default_values_populator_handler = lambda_.Function(
            scope,
            "DDBDefaultValuesPopulator",
            function_name=lambda_name,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            timeout=cdk.Duration.seconds(300),
            environment={
                **self.generate_ddb_populator_environment_variables(),
            },
            role=ddb_default_values_populator_role,
            description="Lambda to populate default values in ddb",
            layers=[self.shared_library_lambda_layer],
            handler="lambda_functions.custom_resource.ddb_default_values_populator_lambda.handler.handler",
            code=lambda_.Code.from_asset(InfraUtils.resources_dir()),
        )
        self.add_common_tags(default_values_populator_handler)

        return cdk.CustomResource(
            scope,
            "CustomResourceDDBDefaultValuesPopulator",
            service_token=default_values_populator_handler.function_arn,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            resource_type="Custom::RESDdbPopulator",
            properties={
                ENVIRONMENT_NAME_KEY: self.cluster_name,
                "shared_library_arn": self.shared_library_arn,
            },
        )

    def generate_ddb_populator_environment_variables(self) -> Dict[str, Any]:
        # create environment variables dict
        environment_variables = {
            # Essential environment variables
            "aws_partition": cdk.Aws.PARTITION,
            "aws_region": cdk.Aws.REGION,
            "aws_account_id": cdk.Aws.ACCOUNT_ID,
            "aws_dns_suffix": cdk.Aws.URL_SUFFIX,
            ###### Stack Input parameters ######
            # Environment and installer details
            ENVIRONMENT_NAME_KEY: self.cluster_name,
            "administrator_email": self.parameters.get_str(CommonKey.ADMIN_EMAIL),
            "instance_ami": self.parameters.get_str(CommonKey.INFRASTRUCTURE_HOST_AMI),
            "ssh_key_pair_name": self.parameters.get_str(CommonKey.SSH_KEY_PAIR),
            "client_ip": self.parameters.get_str(CommonKey.CLIENT_IP),
            "prefix_list": self.parameters.get_str(CommonKey.CLIENT_PREFIX_LIST),
            "permission_boundary_arn": self.parameters.get_str(
                CommonKey.IAM_PERMISSION_BOUNDARY
            ),
            # Network configuration for the RES environment
            "vpc_id": self.parameters.get_str(CommonKey.VPC_ID),
            "alb_public": self.parameters.get_str(
                CommonKey.IS_LOAD_BALANCER_INTERNET_FACING
            ),
            "load_balancer_subnet_ids": self.params_transformer.get_att_string(
                "LOAD_BALANCER_SUBNETS"
            ),
            "infrastructure_host_subnet_ids": self.params_transformer.get_att_string(
                "INFRA_SUBNETS"
            ),
            "vdi_subnet_ids": self.params_transformer.get_att_string("VDI_SUBNETS"),
            # Active Directory details
            "ad_name": self.parameters.get_str(DirectoryServiceKey.NAME),
            "ad_short_name": self.parameters.get_str(DirectoryServiceKey.AD_SHORT_NAME),
            "ldap_base": self.parameters.get_str(DirectoryServiceKey.LDAP_BASE),
            "ldap_connection_uri": self.parameters.get_str(
                DirectoryServiceKey.LDAP_CONNECTION_URI
            ),
            "service_account_credentials_secret_arn": self.parameters.get_str(
                DirectoryServiceKey.SERVICE_ACCOUNT_CREDENTIALS_SECRET_ARN
            ),
            "users_ou": self.parameters.get_str(DirectoryServiceKey.USERS_OU),
            "groups_ou": self.parameters.get_str(DirectoryServiceKey.GROUPS_OU),
            "sudoers_group_name": self.parameters.get_str(
                DirectoryServiceKey.SUDOERS_GROUP_NAME
            ),
            "computers_ou": self.parameters.get_str(DirectoryServiceKey.COMPUTERS_OU),
            "domain_tls_certificate_secret_arn": self.parameters.get_str(
                DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN
            ),
            "enable_ldap_id_mapping": self.parameters.get_str(
                DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING
            ),
            "disable_ad_join": self.parameters.get_str(
                DirectoryServiceKey.DISABLE_AD_JOIN
            ),
            "root_user_dn_secret_arn": self.parameters.root_user_dn_secret_arn,
            # Shared Storage details
            "existing_home_fs_id": self.parameters.get_str(
                SharedStorageKey.SHARED_HOME_FILESYSTEM_ID
            ),
            # Custom domain details
            "webapp_custom_dns_name": self.parameters.get_str(
                CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_WEB_APP
            ),
            "acm_certificate_arn": self.parameters.get_str(
                CustomDomainKey.ACM_CERTIFICATE_ARN_FOR_WEB_APP
            ),
            "vdi_custom_dns_name": self.parameters.get_str(
                CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_VDI
            ),
            "certificate_secret_arn": self.parameters.get_str(
                CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI
            ),
            "private_key_secret_arn": self.parameters.get_str(
                CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI
            ),
            "shared_library_arn": self.shared_library_arn,
            #  Internet Proxy details
            "http_proxy_value": self.parameters.get_str(InternetProxyKey.HTTP_PROXY),
            "https_proxy_value": self.parameters.get_str(InternetProxyKey.HTTPS_PROXY),
            "no_proxy_value": self.parameters.get_str(InternetProxyKey.NO_PROXY),
        }
        return environment_variables

    def create_bucket(self) -> None:
        scope = self.nested_stack
        stack_id = cdk.Stack.of(scope).stack_id
        stack_id_suffix = cdk.Fn.select(
            0, cdk.Fn.split("-", cdk.Fn.select(2, cdk.Fn.split("/", stack_id)))
        )
        logging_bucket_name = f"log-{self.cluster_name}-cluster-{cdk.Aws.REGION}-{cdk.Aws.ACCOUNT_ID}-{stack_id_suffix}"
        logging_bucket = s3.Bucket(
            scope,
            "ClusterLoggingBucket",
            bucket_name=logging_bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
        )

        logging_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:PutObject"],
                sid="AllowS3LogRequests",
                resources=[f"{logging_bucket.bucket_arn}/*"],
                principals=[iam.ServicePrincipal("logging.s3.amazonaws.com")],
            ),
        )

        staging_bucket_name = (
            f"{self.cluster_name}-cluster-{cdk.Aws.REGION}-{cdk.Aws.ACCOUNT_ID}"
        )
        staging_bucket = s3.Bucket(
            scope,
            "ClusterStagingBucket",
            bucket_name=staging_bucket_name,
            access_control=s3.BucketAccessControl.PRIVATE,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            server_access_logs_bucket=logging_bucket,
            server_access_logs_prefix="cluster-s3-bucket-logs/",
        )
        elb_principal_type = self.populator_custom_resource.get_att_string(
            "elb_principal_type"
        )
        elb_principal_value = self.populator_custom_resource.get_att_string(
            "elb_principal_value"
        )

        alb_access_logs_principal_json = CfnJson(
            self.nested_stack,
            "alb_access_logs_principal_json",
            value={elb_principal_type: elb_principal_value},
        )

        existing_staging_bucket_statement = []
        if staging_bucket.policy is not None:
            existing_staging_bucket_statement = (
                staging_bucket.policy.document.to_json().get("Statement", [])
            )
        staging_bucket_policy_document = {
            "Version": "2012-10-17",
            "Statement": existing_staging_bucket_statement
            + [
                {
                    "Sid": "IdeaAlbAccessLogs",
                    "Effect": "Allow",
                    "Principal": alb_access_logs_principal_json,
                    "Action": "s3:PutObject",
                    "Resource": f"{staging_bucket.bucket_arn}/logs/*",
                },
                {
                    "Sid": "AllowSSLRequestsOnly",
                    "Effect": "Deny",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:*",
                    "Resource": [
                        f"{staging_bucket.bucket_arn}/*",
                        f"{staging_bucket.bucket_arn}",
                    ],
                    "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                },
                {
                    "Sid": "IdeaNlbAccessLogs-AWSLogDeliveryWrite",
                    "Effect": "Allow",
                    "Principal": {"Service": f"delivery.logs.{cdk.Aws.URL_SUFFIX}"},
                    "Action": "s3:PutObject",
                    "Resource": f"{staging_bucket.bucket_arn}/logs/*",
                    "Condition": {
                        "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}
                    },
                },
                {
                    "Sid": "IdeaNlbAccessLogs-AWSLogDeliveryAclCheck",
                    "Effect": "Allow",
                    "Principal": {"Service": f"delivery.logs.{cdk.Aws.URL_SUFFIX}"},
                    "Action": "s3:GetBucketAcl",
                    "Resource": f"{staging_bucket.bucket_arn}",
                },
            ],
        }

        staging_bucket_policy = s3.CfnBucketPolicy(
            self.nested_stack,
            "ClusterStagingBucketPolicy",
            bucket=staging_bucket_name,
            policy_document=staging_bucket_policy_document,
        )
        staging_bucket_policy.apply_removal_policy(RemovalPolicy.RETAIN)

        staging_bucket.node.add_dependency(self.populator_custom_resource)
        staging_bucket_policy.node.add_dependency(self.populator_custom_resource)
        staging_bucket_policy.node.add_dependency(staging_bucket)
        cdk.Tags.of(staging_bucket).add(RES_TAG_BACKUP_PLAN, "cluster")
        cdk.Tags.of(staging_bucket).add(RES_TAG_ENVIRONMENT_NAME, self.cluster_name)
        cdk.Tags.of(logging_bucket).add(RES_TAG_ENVIRONMENT_NAME, self.cluster_name)
