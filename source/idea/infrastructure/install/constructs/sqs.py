#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, Optional, Union

import constructs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_sqs as sqs

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class SQSQueue(ResBaseConstruct, sqs.Queue):

    def __init__(
        self,
        id: str,
        scope: constructs.Construct,
        arn_builder: ArnBuilder,
        parameters: Union[RESParameters, BIParameters],
        *,
        content_based_deduplication: Optional[bool] = None,
        fifo_throughput_limit: Optional[sqs.FifoThroughputLimit] = None,
        deduplication_scope: Optional[sqs.DeduplicationScope] = None,
        dead_letter_queue: Optional[Union[sqs.DeadLetterQueue, Dict[str, Any]]] = None,
        encrypt_at_rest: Optional[bool] = True,
        encryption: Optional[sqs.QueueEncryption] = None,
        encryption_master_key: Optional[str] = None,
        fifo: Optional[bool] = None,
    ):
        self.scope = scope
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        if encrypt_at_rest:
            if encryption is None:
                encryption = sqs.QueueEncryption.KMS_MANAGED

            encryption_master_key_ = None
            if encryption_master_key:
                key_arn = arn_builder.kms_sns_key_arn(encryption_master_key)
                encryption_master_key_ = kms.Key.from_key_arn(
                    self.scope, f"{id}-kms-key", key_arn=key_arn
                )
                encryption = sqs.QueueEncryption.KMS
        else:
            encryption = sqs.QueueEncryption.UNENCRYPTED
            encryption_master_key_ = None

        super().__init__(
            self.scope,
            id,
            self.cluster_name,
            parameters,
            deduplication_scope=deduplication_scope,  # type: ignore
            fifo_throughput_limit=fifo_throughput_limit,  # type: ignore
            content_based_deduplication=content_based_deduplication,  # type: ignore
            dead_letter_queue=dead_letter_queue,  # type: ignore
            encryption=encryption,  # type: ignore
            encryption_master_key=encryption_master_key_,  # type: ignore
            fifo=fifo,  # type: ignore
            queue_name=ResBaseConstruct.build_resource_name(id + ".fifo" if fifo else id, self.cluster_name),  # type: ignore
        )

        if encrypt_at_rest:
            self.add_to_resource_policy(
                iam.PolicyStatement(
                    sid="AlwaysEncrypted",
                    effect=iam.Effect.DENY,
                    actions=["sqs:*"],
                    conditions={"Bool": {"aws:SecureTransport": "false"}},
                    resources=[self.queue_arn],
                    principals=[iam.AnyPrincipal()],
                )
            )
