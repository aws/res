#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List, Optional, Union

import constructs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_sns as sns

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class SNSTopic(ResBaseConstruct, sns.Topic):

    def __init__(
        self,
        scope: constructs.Construct,
        id_: str,
        parameters: Union[RESParameters, BIParameters],
        *,
        fifo: Optional[bool] = None,
        master_key: Optional[str] = None,
        display_name: Optional[str] = None,
        topic_name: Optional[str] = None,
        policy_statements: Optional[List[iam.PolicyStatement]] = None,
    ):

        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        if not topic_name:
            topic_name = self.build_resource_name(id_, self.cluster_name)

        if not display_name:
            display_name = topic_name

        if master_key:
            kms_key_arn = ArnBuilder.get_arn(
                service="kms", resource=f"key/{master_key}"
            )
            master_key_ = kms.Key.from_key_arn(
                scope=scope, id=f"{id_}-kms-key", key_arn=kms_key_arn
            )
        else:
            master_key_ = kms.Alias.from_alias_name(
                scope=scope, id=f"{id_}-kms-key-default", alias_name="alias/aws/sns"
            )

        super().__init__(
            scope,
            id_,
            cluster_name=self.cluster_name,
            display_name=display_name,  # type: ignore
            fifo=fifo,  # type: ignore
            topic_name=ResBaseConstruct.build_resource_name(topic_name, self.cluster_name),  # type: ignore
            master_key=master_key_,  # type: ignore
        )

        if policy_statements is not None:
            for statement in policy_statements:
                self.add_to_resource_policy(statement)

        self.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AlwaysEncrypted",
                effect=iam.Effect.DENY,
                actions=["SNS:Publish"],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
                resources=[self.topic_arn],
                principals=[iam.AnyPrincipal()],
            )
        )
