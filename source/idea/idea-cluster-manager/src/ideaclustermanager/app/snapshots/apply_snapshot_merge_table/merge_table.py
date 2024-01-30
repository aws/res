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
from ideaclustermanager.app.snapshots.helpers.apply_snapshot_observability_helper import ApplySnapshotObservabilityHelper
from ideaclustermanager.app.snapshots.helpers.merged_record_utils import MergedRecordDelta
from ideadatamodel.snapshots.snapshot_model import TableName

from abc import abstractmethod
from typing import Dict, List, Tuple


class MergeTable:
    @abstractmethod
    def merge(self, context: SocaContext, table_data_to_merge: List,
              dedup_id: str, merged_record_deltas: Dict[TableName, List[MergedRecordDelta]],
              logger: ApplySnapshotObservabilityHelper) -> Tuple[List[MergedRecordDelta], bool]:
        """ Merges the records represented by table_data_to_merge List to the env by invoking the corresponding
        Create APIs or the create functions in the Service. If exception arrises during merge operation for a record, the exceotion should be handeled
        and a tuple indicating the elta for merged records with a boolean False indicating merge failure must be returned, Eg. return merge_delata_dict, False.

        Args:
            context (SocaContext):
            table_data_to_merge (List): List of python dicts representing records to be merged.
            dedup_id (str): Dedup ID for resolving conflict records.
            merged_record_deltas (Dict[TableName, List[MergedRecordDelta]]): Deltas for the merged records.
            logger (ApplySnapshotObservabilityHelper): Helper for logging the operations.

        Returns:
            Tuple[Dict, bool]: Dict represents the represents the delta/changes. This will be passed to the rollback function, in case rollback is must be initiated.
            bool represents if the merge was successful for all records. If merging a record fails, the delta will be returned with False indicating the merge was not successful.
            Returned bool indicates if a rollback should be initiated.
        """
        ...

    @abstractmethod
    def rollback(self, context: SocaContext, merge_delta: List[MergedRecordDelta], logger: ApplySnapshotObservabilityHelper):
        """ Rolls back a merge applied on a table.

        Args:
            context (SocaContext):
            merge_delta (Dict): Discribes the delta introduced by the merge operation.
            logger (ApplySnapshotObservabilityHelper): Helper for logging the operations
        """
        ...

    @staticmethod
    def unique_resource_id_generator(key: str, dedup_id: str) -> str:
        return f'{key}_{dedup_id}'