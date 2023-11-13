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

import ideasdk.aws
from ideadatamodel import exceptions, errorcodes, AWSPartition, AWSRegion
from ideasdk.utils import Utils

from typing import Optional, Dict, List

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try back ported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources  # noqa

AWS_ENDPOINTS_FILE = 'aws_endpoints.json'


class AwsEndpoints:

    def __init__(self):
        self._data: Optional[Dict] = None

    # Begin: Private Methods

    @property
    def data(self) -> Dict:
        if self._data is None:
            content = pkg_resources.read_text(package=ideasdk.aws, resource=AWS_ENDPOINTS_FILE)
            self._data = Utils.from_json(content)
        return self._data

    # Begin: Public Methods

    def list_partitions(self) -> List[AWSPartition]:
        partitions = Utils.get_value_as_list('partitions', self.data)
        result = []
        for partition in partitions:
            name = Utils.get_value_as_string('partitionName', partition)
            partition_ = Utils.get_value_as_string('partition', partition)
            dns_suffix = Utils.get_value_as_string('dnsSuffix', partition)
            regions = []
            aws_regions = Utils.get_value_as_dict('regions', partition)
            for region, content in aws_regions.items():
                region_name = Utils.get_value_as_string('description', content)
                regions.append(AWSRegion(
                    name=region_name,
                    region=region
                ))
            result.append(AWSPartition(
                name=name,
                partition=partition_,
                regions=regions,
                dns_suffix=dns_suffix
            ))
        return result

    def get_partition(self, partition: str) -> AWSPartition:

        partitions = self.list_partitions()
        for partition_ in partitions:
            if partition_.partition == partition:
                return partition_

        raise exceptions.soca_exception(
            error_code=errorcodes.AWS_ENDPOINTS_PARTITION_NOT_FOUND,
            message=f'Partition: {partition} not found in {AWS_ENDPOINTS_FILE}.'
        )
