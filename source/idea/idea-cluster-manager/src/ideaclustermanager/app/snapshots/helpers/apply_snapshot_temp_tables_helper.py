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

from typing import List, Optional
import botocore.exceptions


class ApplySnapshotTempTablesHelper:
    def __init__(self, context: SocaContext):
        self.context = context
        self.logger = context.logger('apply-snapshot-temp-table-helper')
        
    def initiate_import_table(self, s3_bucket_name: str, s3_key_prefix: str, table_name: str, partition_key: str, sort_key: Optional[str]):
        """Initiate dynamodb.import_table operation.

        Args:
            s3_bucket_name (str): Bucket name where the snapshot is present
            s3_key_prefix (str): Path at which data for the particular table is present.
            table_name (str): The name of the table that will be created with the data from the snapshot
            partition_key (str): partition_key that will be used for the DynamoDB table created from the snapshot
            sort_key (Optional[str]): sort_key (if applicable) that will be used for the DynamoDb table created from the snapshot

        Returns:
            Dict: Returns response received for the aws().dynamodb().import_table() operation
        """
        import_table_request = {
            'S3BucketSource': {
                # Update with valid S3 bucket name here.
                'S3Bucket': s3_bucket_name,
                'S3KeyPrefix': s3_key_prefix,
            },
            'InputFormat': 'DYNAMODB_JSON',
            'InputCompressionType': 'GZIP',
            'TableCreationParameters': {
                'TableName': table_name,
                'AttributeDefinitions': [{'AttributeName': partition_key, 'AttributeType': 'S'}],
                'KeySchema': [{'AttributeName': partition_key, 'KeyType': 'HASH'}],
                'BillingMode': 'PAY_PER_REQUEST',
            },
        }

        if sort_key:
            import_table_request['TableCreationParameters']['AttributeDefinitions'].append(
                {'AttributeName': sort_key, 'AttributeType': 'S'}
            )
            import_table_request['TableCreationParameters']['KeySchema'].append(
                {'AttributeName': sort_key, 'KeyType': 'RANGE'}
            )

        return self.context.aws_util().dynamodb_import_table(import_table_request)

    def delete_imported_tables(self, table_names: List[str]):
        """ Creates a thread that initates table deletion for all tables in the list

        Args:
            table_names (List[str]): table_names of DynamoDB tables to be deleted
        """
        for table_name in table_names:
            try:
                self.context.aws_util().dynamodb_delete_table(table_name)
            except botocore.exceptions.ClientError as e:
                self.logger.error(f"DynamoDB table {table_name} failed deletion with exception {e}")
