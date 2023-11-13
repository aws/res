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

from ideasdk.context import SocaCliContext, SocaContextOptions
from ideasdk.utils import Utils

from typing import List, Dict


class ClusterPrefixListHelper:

    def __init__(self, cluster_name: str, aws_region: str, aws_profile: str = None):
        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.context = SocaCliContext(options=SocaContextOptions(
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile,
            enable_aws_client_provider=True
        ))

        self.cluster_prefix_list_id = self.context.config().get_string('cluster.network.cluster_prefix_list_id', required=True)

    def _get_current_version(self) -> int:
        describe_result = self.context.aws().ec2().describe_managed_prefix_lists(
            PrefixListIds=[self.cluster_prefix_list_id]
        )
        prefix_list_info = describe_result['PrefixLists'][0]
        version = prefix_list_info['Version']
        return int(version)

    def list_entries(self) -> List[Dict]:
        result = []
        prefix_list_paginator = self.context.aws().ec2().get_paginator('get_managed_prefix_list_entries')
        prefix_list_iterator = prefix_list_paginator.paginate(PrefixListId=self.cluster_prefix_list_id)
        for prefix_list in prefix_list_iterator:
            cidr_entries = prefix_list.get('Entries', [])
            for cidr_entry in cidr_entries:
                result.append({
                    'cidr': cidr_entry['Cidr'],
                    'description': Utils.get_value_as_string('Description', cidr_entry)
                })
        return result

    def add_entry(self, cidr: str, description: str):
        if Utils.is_empty(cidr):
            self.context.error('cidr is required')
            raise SystemExit(1)

        result = self.list_entries()
        for entry in result:
            if entry['cidr'] == cidr:
                self.context.warning(f'CIDR: {cidr} already exists in cluster prefix list: {self.cluster_prefix_list_id}')
                raise SystemExit(1)

        cidr_entry = {
            'Cidr': cidr
        }
        if Utils.is_not_empty(description):
            cidr_entry['Description'] = description

        self.context.aws().ec2().modify_managed_prefix_list(
            AddEntries=[cidr_entry],
            PrefixListId=self.cluster_prefix_list_id,
            CurrentVersion=self._get_current_version()
        )
        self.context.success(f'CIDR: {cidr} added to cluster prefix list: {self.cluster_prefix_list_id}.')

    def remove_entry(self, cidr: str):
        if Utils.is_empty(cidr):
            self.context.error('cidr is required')
            raise SystemExit(1)

        result = self.list_entries()
        found = False
        for entry in result:
            if entry['cidr'] == cidr:
                found = True
                break
        if not found:
            self.context.warning(f'CIDR: {cidr} not found in cluster prefix list: {self.cluster_prefix_list_id}')
            raise SystemExit(1)

        cidr_entry = {
            'Cidr': cidr
        }

        self.context.aws().ec2().modify_managed_prefix_list(
            RemoveEntries=[cidr_entry],
            PrefixListId=self.cluster_prefix_list_id,
            CurrentVersion=self._get_current_version()
        )
        self.context.success(f'CIDR: {cidr} was removed from cluster prefix list: {self.cluster_prefix_list_id}.')
