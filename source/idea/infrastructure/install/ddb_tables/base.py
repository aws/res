#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Optional

import aws_cdk as cdk
import res.constants as constants  # type: ignore
from aws_cdk import Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kinesis as kinesis
from aws_cdk import aws_lambda as lambda_
from aws_cdk.aws_dynamodb import BillingMode, Table
from constructs import Construct

from idea.infrastructure.install.constants import RES_COMMON_LAMBDA_RUNTIME
from idea.infrastructure.install.ddb_tables.list import RESDDBTable
from idea.infrastructure.install.utils import InfraUtils
from idea.infrastructure.resources.lambda_functions.table_stream_subscription_lambda import (
    table_stream_subscription_handler,
)


class RESDDBTableBase(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        cluster_name: str,
        table_data: RESDDBTable,
        shared_library_lambda_layer: Optional[lambda_.LayerVersion] = None,
        stream_event_handler_role: Optional[iam.Role] = None,
    ):
        super().__init__(scope, id)
        self.id = id
        self.cluster_name = cluster_name
        self.module_id = table_data.module_id
        self.table_props = table_data.table_props
        self.global_secondary_indexes_props = table_data.global_secondary_indexes_props

        self.kinesis_stream = None
        if table_data.enable_kinesis_stream:
            self.kinesis_stream = self.get_kinesis_stream_for_table(table_data.id)

        self.ddb_table = Table(
            scope,
            self.get_table_id(),
            billing_mode=BillingMode.PAY_PER_REQUEST,
            table_name=f"{cluster_name}.{self.id}",
            kinesis_stream=self.kinesis_stream,
            **self.table_props._values,
        )

        self.add_db_tag()
        if self.global_secondary_indexes_props:
            for global_secondary_index_props in self.global_secondary_indexes_props:
                self.ddb_table.add_global_secondary_index(
                    **global_secondary_index_props._values
                )

        self.ddb_table.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        if table_data.enable_table_event_handler_lambda:
            self.create_table_event_handler_lambda(
                shared_library_lambda_layer,
                stream_event_handler_role,
            )

    def get_table_id(self) -> str:
        return f"{self.id.replace('.', '-')}-table"

    def add_db_tag(self) -> None:
        module_name = constants.MODULE_ID_NAME_MAPPING[self.module_id]

        cdk.Tags.of(self.ddb_table).add(
            key=constants.ENVIRONMENT_NAME_TAG_KEY, value=self.cluster_name
        )
        cdk.Tags.of(self.ddb_table).add(
            key=constants.RES_TAG_BACKUP_PLAN, value=f"{self.cluster_name}-cluster"
        )
        cdk.Tags.of(self.ddb_table).add(
            key=constants.RES_TAG_MODULE_NAME, value=module_name
        )
        cdk.Tags.of(self.ddb_table).add(
            key=constants.RES_TAG_MODULE_ID, value=self.module_id
        )

    def get_kinesis_stream_for_table(self, table_id: str) -> kinesis.IStream:
        kinesis_stream = kinesis.Stream(
            self,
            "KinesisStream",
            encryption=kinesis.StreamEncryption.MANAGED,
            stream_mode=kinesis.StreamMode.ON_DEMAND,
            stream_name=f"{self.cluster_name}.{table_id}-kinesis-stream",
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        cdk.Tags.of(kinesis_stream).add(
            key=constants.ENVIRONMENT_NAME_TAG_KEY,
            value=self.cluster_name,
        )
        return kinesis_stream

    def create_table_event_handler_lambda(
        self,
        shared_library_lambda_layer: Optional[lambda_.LayerVersion],
        stream_event_handler_role: Optional[iam.Role],
    ) -> None:
        stream_event_handler_lambda = lambda_.Function(
            self,
            id="TableEventHandler",
            function_name=f"{self.cluster_name}-{self.id}-table-event-handler",
            timeout=Duration.seconds(300),
            role=stream_event_handler_role,
            runtime=RES_COMMON_LAMBDA_RUNTIME,
            **InfraUtils.get_handler_and_code_for_function(
                table_stream_subscription_handler.handle
            ),
            layers=(
                [shared_library_lambda_layer] if shared_library_lambda_layer else None
            ),
            environment={
                "TABLE_NAME": self.id,
                "environment_name": self.cluster_name,
            },
        )
        cdk.Tags.of(stream_event_handler_lambda).add(
            key=constants.ENVIRONMENT_NAME_TAG_KEY,
            value=self.cluster_name,
        )

        self.ddb_table.grant_read_data(stream_event_handler_lambda)

        if self.kinesis_stream:
            self.kinesis_stream.grant_read(stream_event_handler_lambda)
            lambda_.CfnEventSourceMapping(
                self,
                id="TableEventSourceMapping",
                function_name=stream_event_handler_lambda.function_name,
                event_source_arn=self.kinesis_stream.stream_arn,
                maximum_batching_window_in_seconds=1,
                starting_position="LATEST",
                batch_size=10,
            )
