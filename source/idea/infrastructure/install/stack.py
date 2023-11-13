#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import importlib.metadata
from typing import Any, Optional, TypedDict, Union

from aws_cdk import Environment, IStackSynthesizer, SecretValue, Stack, Tags
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_kms as kms
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct, DependencyGroup

import idea
from idea.infrastructure.install import installer
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.directoryservice import DirectoryServiceKey
from idea.infrastructure.install.parameters.parameters import (
    AllParameterGroups,
    Parameters,
)
from ideadatamodel import constants  # type: ignore

PUBLIC_REGISTRY_NAME = (
    "public.ecr.aws/i4h1n0f0/idea-administrator:v3.0.0-pre-alpha-feature"
)


class DynamoEncryptionParams(TypedDict):
    encryption: dynamodb.TableEncryption
    encryption_key: kms.IKey


class EmptyDynamoEncryptionParams(TypedDict):
    pass


class InstallStack(Stack):
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        parameters: Parameters = Parameters(),
        registry_name: Optional[str] = None,
        dynamodb_kms_key_alias: Optional[str] = None,
        env: Union[Environment, dict[str, Any], None] = None,
        synthesizer: Optional[IStackSynthesizer] = None,
    ):
        super().__init__(
            scope,
            stack_id,
            env=env,
            synthesizer=synthesizer,
            description=f"RES_{importlib.metadata.version(idea.__package__)}",
        )

        self.parameters = parameters
        self.parameters.generate(self)
        self.template_options.metadata = AllParameterGroups.template_metadata()
        self.registry_name = (
            registry_name if registry_name is not None else PUBLIC_REGISTRY_NAME
        )
        self.dynamodb_kms_key: Optional[kms.IKey] = self.get_dynamodb_kms_key(
            dynamodb_kms_key_alias
        )

        settings_table = self.get_settings_table()
        modules_table = self.get_modules_table()

        root_username_secret = self.get_directory_service_secret(
            DirectoryServiceKey.ROOT_USERNAME
        )
        root_password_secret = self.get_directory_service_secret(
            DirectoryServiceKey.ROOT_PASSWORD
        )

        self.parameters.root_username_secret_arn = root_username_secret.secret_arn
        self.parameters.root_password_secret_arn = root_password_secret.secret_arn

        dependency_group = DependencyGroup()
        dependency_group.add(settings_table)
        dependency_group.add(modules_table)

        self.installer = installer.Installer(
            self,
            "Installer",
            registry_name=self.registry_name,
            params=self.parameters,
            dependency_group=dependency_group,
        )

    def get_dynamodb_kms_key(self, alias: Optional[str]) -> Optional[kms.IKey]:
        if alias is None:
            return None
        return kms.Key.from_lookup(self, id="dynamodb_kms_key", alias_name=alias)

    def get_directory_service_secret(
        self, key: DirectoryServiceKey
    ) -> secretsmanager.Secret:
        secret = secretsmanager.Secret(
            self,
            id=f"DirectoryServiceSecret{key}",
            secret_name=f"{self.parameters.get_str(CommonKey.CLUSTER_NAME)}-{constants.MODULE_DIRECTORYSERVICE}-{key}",
            secret_string_value=SecretValue.cfn_parameter(self.parameters.get(key)),
        )

        Tags.of(secret).add(
            key=constants.IDEA_TAG_ENVIRONMENT_NAME,
            value=self.parameters.get_str(CommonKey.CLUSTER_NAME),
        )
        Tags.of(secret).add(
            key=constants.IDEA_TAG_MODULE_NAME,
            value=constants.MODULE_DIRECTORYSERVICE,
        )
        Tags.of(secret).add(
            key=constants.IDEA_TAG_MODULE_ID,
            value=constants.MODULE_DIRECTORYSERVICE,
        )

        return secret

    def get_settings_table(self) -> dynamodb.Table:
        table = dynamodb.Table(
            self,
            "Settings",
            table_name=f"{self.parameters.get_str(CommonKey.CLUSTER_NAME)}.cluster-settings",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            partition_key=dynamodb.Attribute(
                name="key", type=dynamodb.AttributeType.STRING
            ),
            **self.get_dynamodb_encryption_params(),
        )

        Tags.of(table).add(
            key=constants.IDEA_TAG_ENVIRONMENT_NAME,
            value=self.parameters.get_str(CommonKey.CLUSTER_NAME),
        )

        return table

    def get_modules_table(self) -> dynamodb.Table:
        table = dynamodb.Table(
            self,
            "Modules",
            table_name=f"{self.parameters.get_str(CommonKey.CLUSTER_NAME)}.modules",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            partition_key=dynamodb.Attribute(
                name="module_id", type=dynamodb.AttributeType.STRING
            ),
            **self.get_dynamodb_encryption_params(),
        )

        Tags.of(table).add(
            key=constants.IDEA_TAG_ENVIRONMENT_NAME,
            value=self.parameters.get_str(CommonKey.CLUSTER_NAME),
        )
        Tags.of(table).add(
            key=constants.IDEA_TAG_BACKUP_PLAN,
            value=f"{self.parameters.get_str(CommonKey.CLUSTER_NAME)}-{constants.MODULE_CLUSTER}",
        )

        return table

    def get_dynamodb_encryption_params(
        self,
    ) -> Union[DynamoEncryptionParams, EmptyDynamoEncryptionParams]:
        if self.dynamodb_kms_key is None:
            return EmptyDynamoEncryptionParams()
        return DynamoEncryptionParams(
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.dynamodb_kms_key,
        )
