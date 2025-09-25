#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Union

import aws_cdk as cdk
import constructs
from aws_cdk import aws_secretsmanager as secretsmanager

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class OAuthClient(ResBaseConstruct):
    """
    Create ClientId and ClientSecret in Secrets Manager
    """

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        parameters: Union[RESParameters, BIParameters],
        module_name: str,
        kms_key_id: str,
        client_id: str,
        client_secret: str,
    ):
        """
        :param context:
        :param name is used to create the secret name.
            * <name>-client-id
            * <name>-client-secret
        :param module_name is used to tag the secret values.
            access to secrets is restricted by tag name in IAM roles
        :param scope: constructs.Construct
        :param client_id: the client_id
        :param client_secret: the client secret
        """

        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        super().__init__(scope, name, cluster_name, parameters)

        client_id_key = f"{name}-client-id"
        self.client_id = secretsmanager.CfnSecret(
            scope,
            client_id_key,
            description=f"{name} ClientId, Cluster: {cluster_name}",
            kms_key_id=kms_key_id,
            name=self.build_resource_name(client_id_key, cluster_name),
            secret_string=client_id,
        )
        self.client_id.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
        cdk.Tags.of(self.client_id).add(constants.RES_TAG_MODULE_NAME, module_name)
        cdk.Tags.of(self.client_id).add(constants.RES_TAG_MODULE_ID, name)

        self.add_common_tags(self.client_id)

        client_secret_key = f"{name}-client-secret"
        self.client_secret = secretsmanager.CfnSecret(
            scope,
            client_secret_key,
            description=f"{name} ClientSecret, Cluster: {cluster_name}",
            kms_key_id=kms_key_id,
            name=self.build_resource_name(client_secret_key, cluster_name),
            secret_string=client_secret,
        )
        self.client_secret.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
        cdk.Tags.of(self.client_secret).add(constants.RES_TAG_MODULE_NAME, module_name)
        cdk.Tags.of(self.client_secret).add(constants.RES_TAG_MODULE_ID, name)
        self.add_common_tags(self.client_secret)
