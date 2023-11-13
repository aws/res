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

from ideadatamodel.model_utils import ModelUtils

from typing import Dict, Any, Optional


class EC2SpotFleetRequestConfig:
    """
    Soca wrapper class over EC2 Describe Spot Fleet Requests result entry

    See below link for more information on the response structure:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_spot_fleet_requests
    """

    def __init__(self, entry: Dict[str, Any]):
        self._entry = entry

    @property
    def activity_status(self) -> str:
        return ModelUtils.get_value_as_string('ActivityStatus', self._entry)

    @property
    def fulfilled_capacity(self) -> int:
        config = ModelUtils.get_value_as_dict('SpotFleetRequestConfig', self._entry)
        return ModelUtils.get_value_as_int('FulfilledCapacity', config, default=0)

    @property
    def target_capacity(self) -> int:
        config = ModelUtils.get_value_as_dict('SpotFleetRequestConfig', self._entry)
        return ModelUtils.get_value_as_int('TargetCapacity', config, default=0)

    @property
    def spot_fleet_request_state(self) -> str:
        return ModelUtils.get_value_as_string('SpotFleetRequestState', self._entry)

    @property
    def weighted_capacities(self) -> Optional[Dict[str, int]]:
        config = ModelUtils.get_value_as_dict('SpotFleetRequestConfig', self._entry)

        launch_template_configs = ModelUtils.get_value_as_list('LaunchTemplateConfigs', config)
        if launch_template_configs is None or len(launch_template_configs) == 0:
            return None

        launch_template_config = launch_template_configs[0]
        overrides = ModelUtils.get_value_as_list('Overrides', launch_template_config)

        if overrides is None or len(overrides) == 0:
            return None

        if 'WeightedCapacity' not in overrides[0]:
            return None

        weighted_capacities = {}
        for override in overrides:
            instance_type = ModelUtils.get_value_as_string('InstanceType', override)
            weighted_capacity = ModelUtils.get_value_as_int('WeightedCapacity', override)
            weighted_capacities[instance_type] = weighted_capacity

        return weighted_capacities
