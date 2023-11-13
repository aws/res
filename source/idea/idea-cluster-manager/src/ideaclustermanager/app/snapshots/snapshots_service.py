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
from ideadatamodel.snapshots import (
    Snapshot, SnapshotStatus, ListSnapshotsRequest, ListSnapshotsResult
)
from ideadatamodel import exceptions
from ideasdk.context import ArnBuilder
from ideasdk.utils import Utils
from ideaclustermanager.app.snapshots import snapshot_constants
from ideaclustermanager.app.snapshots.snapshot_dao import SnapshotDAO

import botocore.exceptions
import re
import json

DYNAMODB_TABLES_TO_EXPORT = [
    'accounts.group-members',
    'accounts.groups',
    'accounts.sso-state',
    'accounts.users',
    'ad-automation',
    'cluster-settings',
    'email-templates',
    'modules',
    'projects',
    'projects.project-groups',
    'projects.user-projects',
    'snapshots',
    'vdc.controller.permission-profiles',
    'vdc.controller.schedules',
    'vdc.controller.servers',
    'vdc.controller.session-permissions',
    'vdc.controller.software-stacks',
    'vdc.controller.ssm-commands',
    'vdc.controller.user-sessions',
    'vdc.controller.user-sessions-counter',
    'vdc.dcv-broker.AgentKeyPair',
    'vdc.dcv-broker.AgentOAuth2Clients',
    'vdc.dcv-broker.AuthServerPubKeys',
    'vdc.dcv-broker.BrokerAuthServerPrivateKey',
    'vdc.dcv-broker.ConnectSessionKeyPair',
    'vdc.dcv-broker.createSessionCustomerRequest',
    'vdc.dcv-broker.dcvServer',
    'vdc.dcv-broker.deleteSessionCustomerRequest',
    'vdc.dcv-broker.DescribeNextTokenKeyPair',
    'vdc.dcv-broker.HealthTest',
    'vdc.dcv-broker.JwksUrls',
    'vdc.dcv-broker.PortalOAuth2Clients',
    'vdc.dcv-broker.ServerDnsMapping',
    'vdc.dcv-broker.SoftwareStatement',
    'vdc.dcv-broker.UpdateSessionPermissionsSessionCustomerRequest'
]


class SnapshotsService:
    """
    Snapshot Management Service

    Exposes functionality around:
    1. Creating Snapshots
    2. Listing Snapshots
    3. Deleting Snapshots

    The service is primarily invoked via AuthAPI and SnapshotsAPI
    """

    def __init__(self, context: SocaContext):

        self.context = context
        self.arn_builder = ArnBuilder(self.context.config())
        self.logger = context.logger('snapshots-service')
        self.snapshot_dao = SnapshotDAO(context)
        self.snapshot_dao.initialize()

    def create_snapshot(self, snapshot: Snapshot):
        """
        create a new snapshot
        """

        if Utils.is_empty(snapshot.s3_bucket_name):
            raise exceptions.invalid_params('s3_bucket_name is required')
        if not re.match(snapshot_constants.SNAPSHOT_S3_BUCKET_NAME_REGEX, snapshot.s3_bucket_name):
            raise exceptions.invalid_params(f's3_bucket_name must match regex: {snapshot_constants.SNAPSHOT_S3_BUCKET_NAME_REGEX}')

        if Utils.is_empty(snapshot.snapshot_path):
            raise exceptions.invalid_params('snapshot_path is required')
        if not re.match(snapshot_constants.SNAPSHOT_PATH_REGEX, snapshot.snapshot_path):
            raise exceptions.invalid_params(f'snapshot_path must match regex: {snapshot_constants.SNAPSHOT_PATH_REGEX}')

        self.logger.info(f'creating snapshot in S3 Bucket: {snapshot.s3_bucket_name} at path {snapshot.snapshot_path}')

        try:
            table_export_descriptions = {}
            for table_name in DYNAMODB_TABLES_TO_EXPORT:
                self.context.aws().dynamodb().update_continuous_backups(
                    TableName=f'{self.context.config().get_string("cluster.cluster_name")}.{table_name}',
                    PointInTimeRecoverySpecification={
                        'PointInTimeRecoveryEnabled': True
                    }
                )

                export_response = self.context.aws().dynamodb().export_table_to_point_in_time(
                    TableArn=self.arn_builder.get_ddb_table_arn(table_name),
                    S3Bucket=snapshot.s3_bucket_name,
                    S3Prefix=snapshot.snapshot_path,
                    ExportFormat='DYNAMODB_JSON'
                )

                table_export_descriptions[table_name] = export_response['ExportDescription']

            metadata = {
                'table_export_descriptions': table_export_descriptions,
                'version': self.context.module_version()
            }

            self.context.aws().s3().put_object(
                Bucket=snapshot.s3_bucket_name,
                Key=f'{snapshot.snapshot_path}/metadata.json',
                Body=json.dumps(metadata, default=str)
            )
            self.snapshot_dao.create_snapshot({
                's3_bucket_name': snapshot.s3_bucket_name,
                'snapshot_path': snapshot.snapshot_path,
                'status': SnapshotStatus.IN_PROGRESS
            })
        except botocore.exceptions.ClientError as e:
            self.logger.error(f"An error occurred while creating the snapshot: {e}")
            error_message = e.response["Error"]["Message"]
            self.snapshot_dao.create_snapshot({
                's3_bucket_name': snapshot.s3_bucket_name,
                'snapshot_path': snapshot.snapshot_path,
                'status': SnapshotStatus.FAILED,
                'failure_reason': error_message
            })
            raise e

    def __update_snapshot_status(self, snapshot: Snapshot):
        try:
            metadata_s3_object = self.context.aws().s3().get_object(Bucket=snapshot.s3_bucket_name, Key=f'{snapshot.snapshot_path}/metadata.json')
            metadata_file_content = metadata_s3_object['Body'].read().decode('utf-8')
            metadata = json.loads(metadata_file_content)
            table_export_descriptions = metadata['table_export_descriptions']
            is_export_status_updated = False
            export_completed_tables_count = 0
            is_export_failed = False
            failure_message = ''
            for table_name in DYNAMODB_TABLES_TO_EXPORT:
                table_export_description = table_export_descriptions[table_name]
                if table_export_description['ExportStatus'] == SnapshotStatus.IN_PROGRESS:
                    describe_export_response = self.context.aws().dynamodb().describe_export(ExportArn=table_export_description['ExportArn'])
                    latest_table_export_description = describe_export_response['ExportDescription']
                    if latest_table_export_description['ExportStatus'] == SnapshotStatus.COMPLETED:
                        export_completed_tables_count += 1
                        is_export_status_updated = True
                        table_export_descriptions[table_name] = latest_table_export_description
                    elif latest_table_export_description['ExportStatus'] == SnapshotStatus.FAILED:
                        is_export_failed = True
                        is_export_status_updated = True
                        failure_message = latest_table_export_description['FailureMessage']
                        table_export_descriptions[table_name] = latest_table_export_description
                elif table_export_description['ExportStatus'] == SnapshotStatus.COMPLETED:
                    export_completed_tables_count += 1
                else:
                    self.logger.error(f"An error occurred while trying to update the snapshot status. Table export status for table {table_name} is {table_export_description['ExportStatus']}")
                    is_export_failed = True
                    is_export_status_updated = True
                    failure_message = f"Invalid export status: {table_export_description['ExportStatus']} for table {table_name}"
                    break

            if is_export_status_updated:
                metadata['table_export_descriptions'] = table_export_descriptions
                self.context.aws().s3().put_object(
                    Bucket=snapshot.s3_bucket_name,
                    Key=f'{snapshot.snapshot_path}/metadata.json',
                    Body=json.dumps(metadata, default=str)
                )
                if is_export_failed:
                    snapshot.status = SnapshotStatus.FAILED
                    self.snapshot_dao.update_snapshot_status(snapshot, failure_message)
                elif export_completed_tables_count == len(DYNAMODB_TABLES_TO_EXPORT):
                    snapshot.status = SnapshotStatus.COMPLETED
                    self.snapshot_dao.update_snapshot_status(snapshot)
        except botocore.exceptions.ClientError as e:
            self.logger.error(f"An error occurred while trying to update the snapshot status: {e}")
            error_message = e.response["Error"]["Message"]
            snapshot.status = SnapshotStatus.FAILED
            self.snapshot_dao.update_snapshot_status(snapshot, error_message)

    def list_snapshots(self, request: ListSnapshotsRequest) -> ListSnapshotsResult:
        list_snapshots_response = self.snapshot_dao.list_snapshots(request)
        for snapshot in list_snapshots_response.listing:
            if snapshot.status == SnapshotStatus.IN_PROGRESS:
                self.__update_snapshot_status(snapshot)

        return list_snapshots_response
