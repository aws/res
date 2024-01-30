#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from ideasdk.context import SocaContext
from ideasdk.utils import Utils, scan_db_records
from ideadatamodel import (
    exceptions,
    ApplySnapshot,
    ApplySnapshotStatus,
    ListApplySnapshotRecordsRequest,
    ListApplySnapshotRecordsResult,
    SocaListingPayload,
    SocaPaginator,
)

from typing import Dict, Optional
from boto3.dynamodb.conditions import Attr


class ApplySnapshotDAO:
    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('apply-snapshot-dao')
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.apply-snapshot'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_table_name(),
                'AttributeDefinitions': [{'AttributeName': 'apply_snapshot_identifier', 'AttributeType': 'S'}],
                'KeySchema': [{'AttributeName': 'apply_snapshot_identifier', 'KeyType': 'HASH'}],
                'BillingMode': 'PAY_PER_REQUEST',
            },
            wait=True,
        )
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    @staticmethod
    def convert_from_db(apply_snapshot: Dict) -> ApplySnapshot:
        keys = [
            'apply_snapshot_identifier',
            's3_bucket_name',
            'snapshot_path',
            'status',
            'created_on',
            'failure_reason',
        ]
        return ApplySnapshot(**{k: apply_snapshot.get(k) for k in keys})

    @staticmethod
    def convert_to_db(apply_snapshot: ApplySnapshot) -> Dict:
        keys = [
            'apply_snapshot_identifier',
            's3_bucket_name',
            'snapshot_path',
            'status',
            'created_on',
            'failure_reason',
        ]
        return {k: getattr(apply_snapshot, k) for k in keys}

    def create(self, apply_snapshot: Dict, created_on: int) -> Dict:
        s3_bucket_name = apply_snapshot.get('s3_bucket_name')
        if not s3_bucket_name or len(s3_bucket_name.strip()) == 0:
            raise exceptions.invalid_params('s3_bucket_name is required')
        snapshot_path = apply_snapshot.get('snapshot_path')
        if not snapshot_path or len(snapshot_path.strip()) == 0:
            raise exceptions.invalid_params('snapshot_path is required')

        apply_snapshot_record = {
            **apply_snapshot,
            'apply_snapshot_identifier': f'{s3_bucket_name}-{snapshot_path}-{created_on}',
            'created_on': created_on,
        }

        self.table.put_item(Item=apply_snapshot_record)

        return apply_snapshot_record

    def update_status(self, apply_snapshot: ApplySnapshot, status: ApplySnapshotStatus, failure_message: Optional[str] = None) -> Dict:
        update_expression_tokens = ['#status_key = :status_value']
        expression_attr_names = {"#status_key": "status"}
        expression_attr_values = {':status_value': status}

        if failure_message and status in [ApplySnapshotStatus.FAILED, ApplySnapshotStatus.ROLLBACK_IN_PROGRESS, ApplySnapshotStatus.ROLLBACK_COMPLETE, ApplySnapshotStatus.ROLLBACE_FAILED]:
            update_expression_tokens.append('#failure_reason_key = :failure_reason_value')
            expression_attr_names['#failure_reason_key'] = "failure_reason"
            expression_attr_values[':failure_reason_value'] = failure_message

        result = self.table.update_item(
            Key={'apply_snapshot_identifier': apply_snapshot.apply_snapshot_identifier},
            ConditionExpression=Attr('status').ne(status),
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW',
        )

        updated_apply_snapshot = result['Attributes']
        return updated_apply_snapshot

    def list(self, request: ListApplySnapshotRecordsRequest) -> ListApplySnapshotRecordsResult:
        list_result = scan_db_records(request, self.table)
        entries = list_result.get('Items', [])
        result = [self.convert_from_db(entry) for entry in entries]

        exclusive_start_key = list_result.get("LastEvaluatedKey")
        response_cursor = Utils.base64_encode(Utils.to_json(exclusive_start_key)) if exclusive_start_key else None

        return SocaListingPayload(
            listing=result, paginator=SocaPaginator(page_size=request.page_size, cursor=response_cursor)
        )
