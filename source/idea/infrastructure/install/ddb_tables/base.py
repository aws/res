#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import aws_cdk as cdk
from aws_cdk import aws_kinesis as kinesis
from aws_cdk.aws_dynamodb import BillingMode, Table
from constructs import Construct
from res import constants  # type: ignore

from idea.infrastructure.install.ddb_tables.list import RESDDBTable


class RESDDBTableBase(Construct):
    def __init__(
        self, scope: Construct, id: str, cluster_name: str, table_data: RESDDBTable
    ):
        super().__init__(scope, id)
        self.id = id
        self.cluster_name = cluster_name
        self.module_id = table_data.module_id
        self.table_props = table_data.table_props
        self.global_secondary_indexes_props = table_data.global_secondary_indexes_props

        kinesis_stream = None
        if table_data.enable_kinesis_stream:
            kinesis_stream = self.get_kinesis_stream_for_table(table_data.id)

        self.ddb_table = Table(
            scope,
            self.get_table_id(),
            billing_mode=BillingMode.PAY_PER_REQUEST,
            table_name=f"{cluster_name}.{self.id}",
            kinesis_stream=kinesis_stream,
            **self.table_props._values,
        )

        self.add_db_tag()
        if self.global_secondary_indexes_props:
            for global_secondary_index_props in self.global_secondary_indexes_props:
                self.ddb_table.add_global_secondary_index(
                    **global_secondary_index_props._values
                )

        self.ddb_table.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

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
            f"KinesisStream",
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
