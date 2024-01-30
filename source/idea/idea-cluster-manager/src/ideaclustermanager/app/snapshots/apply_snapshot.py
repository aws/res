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
from ideadatamodel.snapshots import Snapshot, ApplySnapshotStatus, TableName
from ideadatamodel import exceptions, SocaListingPayload
from ideasdk.utils import Utils, scan_db_records
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_version_control_helper import get_table_keys_by_res_version
from ideaclustermanager.app.snapshots import snapshot_constants
from ideaclustermanager.app.snapshots.db.apply_snapshot_dao import ApplySnapshotDAO
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_temp_tables_helper import ApplySnapshotTempTablesHelper
from ideaclustermanager.app.snapshots.helpers.apply_snapshots_config import RES_VERSION_IN_TOPOLOGICAL_ORDER, RES_VERSION_TO_DATA_TRANSFORMATION_CLASS, TABLES_IN_MERGE_DEPENDENCY_ORDER, TABLE_TO_MERGE_LOGIC_CLASS
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import ApplySnapshotObservabilityHelper
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import MergedRecordDelta

import botocore.exceptions
import concurrent.futures
import json
import os
import re
import threading
import time
from typing import List, Dict, Optional


class ApplySnapshot:
    def __init__(self, snapshot: Snapshot, apply_snapshot_dao: ApplySnapshotDAO, context: SocaContext):
        self.snapshot = snapshot
        self.context = context
        self.logger = context.logger('apply-snapshot')
        self.apply_snapshot_observability_helper = ApplySnapshotObservabilityHelper(self.logger)

        self.apply_snapshot_dao = apply_snapshot_dao
        self.apply_snapshot_temp_tables_helper = ApplySnapshotTempTablesHelper(context)
        self._ddb_client = self.context.aws().dynamodb_table()

        self.created_on = Utils.current_time_ms()

        self.validate_input()

    def initialize(self):
        self.logger.info(
            f"Snapshot Apply request received for s3_bucket_name: {self.snapshot.s3_bucket_name}, snapshot_path: {self.snapshot.snapshot_path}"
        )

        try:
            self.metadata = self.fetch_snapshot_metadata()
        except botocore.exceptions.ClientError as e:
            error_message = e.response["Error"]["Message"]
            self.apply_snapshot_dao.create(
                {
                    's3_bucket_name': self.snapshot.s3_bucket_name,
                    'snapshot_path': self.snapshot.snapshot_path,
                    'status': ApplySnapshotStatus.FAILED,
                    'failure_reason': error_message,
                },
                created_on=self.created_on
            )
            raise e

        try:
            # Extract the RES Version of the snapshot
            self.snapshot_res_version = self.metadata[snapshot_constants.VERSION_KEY]

            # Extract the table_export_description object from metadata that stores details off all the tables present in the snapshot
            self.table_export_descriptions = self.metadata[snapshot_constants.TABLE_EXPORT_DESCRIPTION_KEY]

            self.tables_to_be_imported = self.get_list_of_tables_to_be_imported()
            self.logger.info(f"Tables that will be imported are: {(',').join(self.tables_to_be_imported)}")
            self.tables_to_be_imported_with_table_key_info = get_table_keys_by_res_version(
                self.tables_to_be_imported, self.snapshot_res_version
            )

            self.apply_snapshot_record = self.apply_snapshot_dao.convert_from_db(
                self.apply_snapshot_dao.create(
                    {
                        's3_bucket_name': self.snapshot.s3_bucket_name,
                        'snapshot_path': self.snapshot.snapshot_path,
                        'status': ApplySnapshotStatus.IN_PROGRESS,
                    },
                    created_on=self.created_on
                )
            )

            self.logger.info("Starting thread to perform ApplySnapshot main process")
            threading.Thread(target=self.apply_snapshot_main).start()
        except Exception as e:
            self.logger.error(f"Applying Snapshot {self.snapshot} failed with error {repr(e)}")
            self.apply_snapshot_dao.create(
                {
                    's3_bucket_name': self.snapshot.s3_bucket_name,
                    'snapshot_path': self.snapshot.snapshot_path,
                    'status': ApplySnapshotStatus.FAILED,
                    'failure_reason': f'{repr(e)}',
                },
                created_on=self.created_on
            )
            raise e

    def get_temp_table_name(self, table_name) -> str:
        return f'{self.context.cluster_name()}.temp-{table_name}-{self.created_on}'

    def validate_input(self):
        """Validates snapshot input object to check if the requred parameters are present.
        Required parameters
        - s3_bucket_name
        - snapshot_path

        Raises:
            exceptions.invalid_params: if required parameters `s3_bucket_name` or `snapshot_path` are not passed.
        """
        if not self.snapshot.s3_bucket_name or not self.snapshot.s3_bucket_name.strip():
            raise exceptions.invalid_params('s3_bucket_name is required')
        if not re.match(snapshot_constants.SNAPSHOT_S3_BUCKET_NAME_REGEX, self.snapshot.s3_bucket_name):
            raise exceptions.invalid_params(
                f's3_bucket_name must match regex: {snapshot_constants.SNAPSHOT_S3_BUCKET_NAME_REGEX}'
            )

        if not self.snapshot.snapshot_path or not self.snapshot.snapshot_path.strip():
            raise exceptions.invalid_params('snapshot_path is required')
        if not re.match(snapshot_constants.SNAPSHOT_PATH_REGEX, self.snapshot.snapshot_path):
            raise exceptions.invalid_params(f'snapshot_path must match regex: {snapshot_constants.SNAPSHOT_PATH_REGEX}')

    def fetch_snapshot_metadata(self):
        """Fetches the metadata.json file from the S3 bucket passed as input. Loads the data into python dict and returns it.

        Raises:
            botocore.exceptions.ClientError: ClientError could occure in the following cases
                - The S3 bucket does not have proper permissions set that allow RES application to get an aboject from the bucket
                - The S3 bucket or the path do not exist

        Returns:
            Dict: returns the metadata.json file contents in python Dict format
        """
        try:
            metadata = json.loads(
                self.context.aws()
                .s3()
                .get_object(
                    Bucket=self.snapshot.s3_bucket_name,
                    Key=f"{self.snapshot.snapshot_path}/{snapshot_constants.METADATA_FILE_NAME_AND_EXTENSION}",
                )['Body']
                .read()
            )
            self.logger.debug(f"Metadata file contents: {metadata}")

            return metadata
        except botocore.exceptions.ClientError as e:
            self.logger.error(
                f"An error occured while trying to fetch {snapshot_constants.METADATA_FILE_NAME_AND_EXTENSION} file from S3 bucket {self.snapshot.s3_bucket_name} at path {self.snapshot.snapshot_path} during the apply snapshot process: {e}"
            )
            raise e

    def get_list_of_tables_to_be_imported(self) -> List[TableName]:
        """Returns a list of table names that should be imported from the snapshot.

        Returns:
            List: List of table names that represents the intersection of the tables present in the snapshot
            and list of tables the ApplySnapshot process supports applying.
        """
        return [e.value for e in TableName if e.value in self.table_export_descriptions]

    def apply_snapshot_main(self):

        try:
            # Step 1.1: Import all applicable tables from snapshot
            self.import_all_tables()
            self.logger.info(f"All tables imported successfully")

            # Step 1.2: Scans all table data and stores it in a python dict
            data_by_table = self.scan_ddb_tables()
            self.logger.debug(f"All table data fetched from snapshot {data_by_table}")

            # Step 2: Apply applicable data transformation logic on table data
            transformed_data = self.apply_data_transformations(data_by_table)
            self.logger.debug(f"Data transformations applied {transformed_data}")

            # Step 3: Merge data to env's actual DDB tables
            self.merge_transformed_data_for_all_tables(transformed_data)

            self.logger.info(f"Apply snapshot operation completed")
            
        except botocore.exceptions.ClientError as e:
            error_message = e.response["Error"]["Message"]
            self.apply_snapshot_dao.update_status(self.apply_snapshot_record, ApplySnapshotStatus.FAILED, error_message)
        except exceptions.SocaException as e:
            error_message = e.message
            self.apply_snapshot_dao.update_status(self.apply_snapshot_record, ApplySnapshotStatus.FAILED, error_message)
        except Exception as e:
            error_message = repr(e)
            self.logger.error(f"Applying Snapshot {self.apply_snapshot_record.apply_snapshot_identifier} failed with error {error_message}")
            self.apply_snapshot_dao.update_status(self.apply_snapshot_record, ApplySnapshotStatus.FAILED, error_message)
        finally:
            imported_tables = [self.get_temp_table_name(table_name) for table_name in self.tables_to_be_imported]
            self.apply_snapshot_temp_tables_helper.delete_imported_tables(table_names=imported_tables)

    def import_all_tables(self) -> None:
        """ Creates one thread per table to import all tables in the self.tables_to_be_imported_with_table_key_info list.

        Raises:
            exceptions.table_import_failed: Raises the exception when some of the tables fail to be imported
        """
        start_time = time.time()
        tables_failed_import: List[str] = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            tasks = {
                executor.submit(
                    self.import_table,
                    table_name,
                    self.tables_to_be_imported_with_table_key_info[table_name].partition_key,
                    self.tables_to_be_imported_with_table_key_info[table_name].sort_key,
                ): table_name for table_name in self.tables_to_be_imported_with_table_key_info.keys()
            }
            for future in concurrent.futures.as_completed(tasks):
                table_name = tasks[future]
                exception = future.exception()
                if exception:
                    tables_failed_import.append(table_name)

        self.logger.debug(f"Table import completed for all tables in {time.time()-start_time} seconds")

        if tables_failed_import:
            error_message = f"Tables ({(',').join(tables_failed_import)}) failed to import. For more details see CloudWatch logs or DynamoDB > Imports from S3 in AWS Console for imports suffixed with '{self.created_on}'"
            self.logger.error(error_message)
            raise exceptions.table_import_failed(error_message)

    def import_table(
        self, table_name: str, partition_key: str, sort_key: Optional[str]
    ):
        """Initiates an import_table operation for a table from the snapshot. Waits for the import operation to complete (either sucesfully or fail).

        Args:
            table_name (str): Name of the table that needs to be imported
            partition_key (str): partition_key that should be used for the temp table craeated
            sort_key (_type_): sort_key (if any) that should be used for the temp DyanmoDB table created
            """
        table_export_details = self.table_export_descriptions.get(table_name)

        table_export_manifest_file = table_export_details['ExportManifest']
        table_export_directory = os.path.dirname(table_export_manifest_file)

        temp_table_name = self.get_temp_table_name(table_name)

        try:
            res = self.apply_snapshot_temp_tables_helper.initiate_import_table(
                s3_bucket_name=self.snapshot.s3_bucket_name,
                s3_key_prefix=f'{table_export_directory}/data/',
                table_name=temp_table_name,
                partition_key=partition_key,
                sort_key=sort_key,
            )

            import_arn = res['ImportTableDescription']['ImportArn']

            imported = self.context.aws_util().dynamodb_check_import_completed_successfully(import_arn)

            if not imported:
                self.logger.error(f'Table "{table_name}" failed import')
                raise RuntimeError(f'Table "{table_name}" failed import')
        except botocore.exceptions.ClientError as e:
            self.logger.error(f'Table "{table_name}" failed import with error: {e}')
            raise e

    def scan_ddb_tables(self) -> Dict[TableName, List]:
        data_by_table = {}
        for table_name in self.tables_to_be_imported:
            data_by_table[table_name] = {}

            temp_table_name = self.get_temp_table_name(table_name)

            table_obj = self._ddb_client.Table(temp_table_name)

            result = scan_db_records(SocaListingPayload(), table_obj)

            data_by_table[table_name] = result["Items"]
        return data_by_table

    def apply_data_transformations(self, data: Dict[TableName, List]) -> Dict:
        res_index = RES_VERSION_IN_TOPOLOGICAL_ORDER.index(self.snapshot_res_version)

        for i in range(res_index, len(RES_VERSION_IN_TOPOLOGICAL_ORDER)):
            version = RES_VERSION_IN_TOPOLOGICAL_ORDER[i]

            if version in RES_VERSION_TO_DATA_TRANSFORMATION_CLASS and RES_VERSION_TO_DATA_TRANSFORMATION_CLASS[version]:
                data_transformer_obj = RES_VERSION_TO_DATA_TRANSFORMATION_CLASS[version]()

                self.logger.info(f"Initiating {type(data_transformer_obj).__name__}'s transform_data()")
                data = data_transformer_obj.transform_data(data, self.logger)
                self.logger.info(f"Completed executing {type(data_transformer_obj).__name__}'s transform_data()")

        return data

    def merge_transformed_data_for_all_tables(self, transformed_data: Dict[TableName, List]) -> None:
        merged_table_to_delta_mappings: Dict[TableName, List[MergedRecordDelta]] = {}

        def _rollback_merged_tables():
            try:
                for table_name in list(reversed(TABLES_IN_MERGE_DEPENDENCY_ORDER)):
                    if table_name in merged_table_to_delta_mappings and table_name in TABLE_TO_MERGE_LOGIC_CLASS and TABLE_TO_MERGE_LOGIC_CLASS[table_name]:
                        merger = TABLE_TO_MERGE_LOGIC_CLASS[table_name]()

                        self.logger.info(f"Initiating {type(merger).__name__}'s rollback()")
                        merger.rollback(self.context, merged_table_to_delta_mappings[table_name], self.apply_snapshot_observability_helper)
                        del merged_table_to_delta_mappings[table_name]
                        self.logger.info(f"Completed executing {type(merger).__name__}'s rollback()")
            except botocore.exceptions.ClientError as e:
                error_message = e.response["Error"]["Message"]
                self.logger.error(f"Apply Snapshot {self.apply_snapshot_record.apply_snapshot_identifier} failed to rollback with error {error_message}. Tables {list(merged_table_to_delta_mappings.keys())} failed to rollback.")
                raise exceptions.table_rollback_failed(error_message)
            except exceptions.SocaException as e:
                error_message = e.message
                self.logger.error(f"Apply Snapshot {self.apply_snapshot_record.apply_snapshot_identifier} failed to rollback with error {error_message}. Tables {list(merged_table_to_delta_mappings.keys())} failed to rollback.")
                raise exceptions.table_rollback_failed(error_message)
            except Exception as e:
                error_message = repr(e)
                self.logger.error(f"Apply Snapshot {self.apply_snapshot_record.apply_snapshot_identifier} failed to rollback with error {error_message}. Tables {list(merged_table_to_delta_mappings.keys())} failed to rollback.")
                raise exceptions.table_rollback_failed(error_message)

        try:
            for table_name in TABLES_IN_MERGE_DEPENDENCY_ORDER:
                if table_name in TABLE_TO_MERGE_LOGIC_CLASS and TABLE_TO_MERGE_LOGIC_CLASS[table_name]:
                    merger = TABLE_TO_MERGE_LOGIC_CLASS[table_name]()

                    self.logger.info(f"Initiating {type(merger).__name__}'s merge()")
                    merge_delta, success = merger.merge(
                        self.context, transformed_data.get(table_name, []),
                        self._get_snapshot_record_dedup_id(),
                        merged_table_to_delta_mappings,
                        self.apply_snapshot_observability_helper
                    )

                    merged_table_to_delta_mappings[table_name] = merge_delta

                    if success:
                        self.logger.info(f"Completed executing {type(merger).__name__}'s merge()")
                    else:
                        error_message = f"Apply Snapshot {self.apply_snapshot_record.apply_snapshot_identifier} failed to apply {table_name}. Initiating rollback."
                        raise exceptions.table_merge_failed(error_message)
                    
            self.apply_snapshot_dao.update_status(self.apply_snapshot_record, ApplySnapshotStatus.COMPLETED)

        except exceptions.SocaException as e:
            error_message = e.message
            self.logger.error(error_message)
            
            self.apply_snapshot_dao.update_status(self.apply_snapshot_record, ApplySnapshotStatus.ROLLBACK_IN_PROGRESS, error_message)
            
            try:
                _rollback_merged_tables()
                self.apply_snapshot_dao.update_status(self.apply_snapshot_record, ApplySnapshotStatus.ROLLBACK_COMPLETE, error_message)
            except exceptions.SocaException as e:
                self.apply_snapshot_dao.update_status(self.apply_snapshot_record, ApplySnapshotStatus.ROLLBACE_FAILED, e.message)

    def _get_snapshot_record_dedup_id(self) -> str:
        return f"{self.snapshot_res_version}_{self.created_on}"
