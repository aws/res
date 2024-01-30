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

from ideadatamodel.snapshots.snapshot_model import RESVersion, TableName, TableKeys
from ideaclustermanager.app.snapshots.helpers.apply_snapshots_config import RES_VERSION_IN_TOPOLOGICAL_ORDER, TABLE_TO_TABLE_KEYS_BY_VERSION

from typing import Dict, List


def get_table_keys_by_res_version(table_names: List[TableName], res_version: RESVersion) -> Dict[TableName, TableKeys]:
    """Returns the partition_key and optional sort_key for all tables represented by the table_names list.
    
    It returns the partition_key and sort_key of a table based on the res version of the snapshot (as these keys can be updated for tables between versions).

    The TABLE_TO_TABLE_KEYS_BY_VERSION constant keeps track of these keys for each table by version. If it does not have an entry for a table 
    for a particular version, it uses a fallback mechanism to get the keys corresponding to the most recent res_version that was released before 
    the res_version of the snapshot
    
    Args:
        table_names (List[TableName]): List of table_names for which the partition_key and optional sort_key should be returned
        res_version (ResVersion): The res version of the Snapshot being applied

    Returns:
        Dict[TableName, TableKeys]: returns a dict that includes the partition_key and optional sort_key for the requested tables
    """
    snapshot_res_version_index = RES_VERSION_IN_TOPOLOGICAL_ORDER.index(res_version)
    
    response: Dict[TableName, TableKeys] = {}
    
    for table_name in table_names:
        res_version_index = snapshot_res_version_index
        table_key_details = TABLE_TO_TABLE_KEYS_BY_VERSION[table_name]
        
        while table_key_details.get(RES_VERSION_IN_TOPOLOGICAL_ORDER[res_version_index]) is None and res_version_index >= 0:
            res_version_index -= 1
            
        if res_version_index < 0:
            error_message = f"Could not fetch partition_key and sort_key for {table_name} in RES_VERSION_IN_TOPOLOGICAL_ORDER dict"
            raise RuntimeError(error_message)
        response[table_name] = table_key_details.get(RES_VERSION_IN_TOPOLOGICAL_ORDER[res_version_index])
                
    return response
