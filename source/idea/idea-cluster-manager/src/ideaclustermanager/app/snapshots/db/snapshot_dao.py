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

import logging
from ideasdk.utils import Utils
from ideadatamodel import exceptions, Snapshot, SnapshotStatus, ListSnapshotsRequest, ListSnapshotsResult, SocaPaginator
from ideasdk.context import SocaContext

from typing import Dict, Optional
from boto3.dynamodb.conditions import Attr


class SnapshotDAO:

    def __init__(self, context: SocaContext, logger=None):
        self.context = context
        if logger is not None:
            self.logger = logger
        else:
            self.logger = context.logger('snapshot-dao')
        self.table = None

    def get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.snapshots'

    def initialize(self):
        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self.get_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 's3_bucket_name',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'snapshot_path',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 's3_bucket_name',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'snapshot_path',
                        'KeyType': 'RANGE'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True
        )
        self.table = self.context.aws().dynamodb_table().Table(self.get_table_name())

    @staticmethod
    def convert_from_db(snapshot: Dict) -> Snapshot:
        snapshot_entry = Snapshot(
            **{
                's3_bucket_name': Utils.get_value_as_string('s3_bucket_name', snapshot),
                'snapshot_path': Utils.get_value_as_string('snapshot_path', snapshot),
                'status': Utils.get_value_as_string('status', snapshot),
                'created_on': Utils.get_value_as_int('created_on', snapshot),
                'failure_reason': Utils.get_value_as_string('failure_reason', snapshot)
            }
        )
        return snapshot_entry

    @staticmethod
    def convert_to_db(snapshot: Snapshot) -> Dict:
        db_snapshot = {
            's3_bucket_name': snapshot.s3_bucket_name
        }
        if snapshot.snapshot_path is not None:
            db_snapshot['snapshot_path'] = snapshot.snapshot_path
        if snapshot.status is not None:
            db_snapshot['status'] = snapshot.status

        return db_snapshot

    def create_snapshot(self, snapshot: Dict) -> Dict:

        s3_bucket_name = Utils.get_value_as_string('s3_bucket_name', snapshot)
        snapshot_path = Utils.get_value_as_string('snapshot_path', snapshot)
        if Utils.is_empty(s3_bucket_name):
            raise exceptions.invalid_params('s3_bucket_name is required')
        if Utils.is_empty(snapshot_path):
            raise exceptions.invalid_params('snapshot_path is required')

        created_snapshot = {
            **snapshot,
            'created_on': Utils.current_time_ms()
        }

        self.table.put_item(
            Item=created_snapshot
        )

        return created_snapshot

    def update_snapshot_status(self, snapshot: Snapshot, failure_message: Optional[str] = None) -> Dict:
        update_expression_tokens = ['#status_key = :status_value']
        expression_attr_names = {"#status_key": "status"}
        expression_attr_values = {':status_value': snapshot.status}

        if failure_message and snapshot.status == SnapshotStatus.FAILED:
            update_expression_tokens.append(f'#failure_reason_key = :failure_reason_value')
            expression_attr_names['#failure_reason_key'] = "failure_reason"
            expression_attr_values[f':failure_reason_value'] = failure_message

        result = self.table.update_item(
            Key={
                's3_bucket_name': snapshot.s3_bucket_name,
                'snapshot_path': snapshot.snapshot_path
            },
            ConditionExpression=Attr('status').ne(snapshot.status),
            UpdateExpression='SET ' + ', '.join(update_expression_tokens),
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues='ALL_NEW'
        )

        updated_snapshot = result['Attributes']
        return updated_snapshot

    def list_snapshots(self, request: ListSnapshotsRequest) -> ListSnapshotsResult:

        scan_request = {}

        cursor = request.cursor
        last_evaluated_key = None
        if Utils.is_not_empty(cursor):
            last_evaluated_key = Utils.from_json(Utils.base64_decode(cursor))
        if last_evaluated_key is not None:
            scan_request['ExclusiveStartKey'] = last_evaluated_key

        scan_filter = None
        if Utils.is_not_empty(request.filters):
            scan_filter = {}
            for filter_ in request.filters:
                if filter_.eq is not None:
                    scan_filter[filter_.key] = {
                        'AttributeValueList': [filter_.eq],
                        'ComparisonOperator': 'EQ'
                    }
                if filter_.like is not None:
                    scan_filter[filter_.key] = {
                        'AttributeValueList': [filter_.like],
                        'ComparisonOperator': 'CONTAINS'
                    }
        if scan_filter is not None:
            scan_request['ScanFilter'] = scan_filter

        _scan_start = Utils.current_time_ms()
        scan_result = self.table.scan(**scan_request)
        _scan_end = Utils.current_time_ms()

        db_snapshots = Utils.get_value_as_list('Items', scan_result, [])

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"DDB Table scan took {_scan_end - _scan_start}ms for {len(db_snapshots)} snapshots")

        snapshots = []

        _idp_start = Utils.current_time_ms()
        for db_snapshot in db_snapshots:
            snapshot = self.convert_from_db(db_snapshot)
            snapshots.append(snapshot)
        _idp_end = Utils.current_time_ms()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"convert_from_db took {_idp_end - _idp_start}ms for {len(snapshots)} snapshots")

        response_cursor = None
        last_evaluated_key = Utils.get_any_value('LastEvaluatedKey', scan_result)
        if last_evaluated_key is not None:
            response_cursor = Utils.base64_encode(Utils.to_json(last_evaluated_key))

        return ListSnapshotsResult(
            listing=snapshots,
            paginator=SocaPaginator(
                cursor=response_cursor
            )
        )
