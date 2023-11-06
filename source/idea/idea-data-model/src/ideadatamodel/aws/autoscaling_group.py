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

from ideadatamodel.aws import AutoScalingGroupInstance
from ideadatamodel.model_utils import ModelUtils

from typing import Dict, Any, Optional, List


class AutoScalingGroup:
    """
    Soca wrapper class over Describe AutoScaling Groups result entry
    """

    def __init__(self, entry: Dict[str, Any]):
        self._entry = entry

    @property
    def desired_capacity(self) -> int:
        return ModelUtils.get_value_as_int('DesiredCapacity', self._entry, default=0)

    @property
    def weighted_capacities(self) -> Optional[Dict[str, int]]:

        policy = ModelUtils.get_value_as_dict('MixedInstancesPolicy', self._entry)
        if policy is None:
            return None

        launch_template = ModelUtils.get_value_as_dict('LaunchTemplate', policy)
        if launch_template is None:
            return None

        overrides = ModelUtils.get_value_as_list('Overrides', launch_template)
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

    def instance_count(self, lifecycle_state='InService') -> int:
        instances = ModelUtils.get_value_as_list('Instances', self._entry)
        if instances is None:
            return 0
        count = 0
        for instance in instances:
            state = ModelUtils.get_value_as_string('LifecycleState', instance)
            if state != lifecycle_state:
                continue
            count += 1
        return count

    @property
    def instances(self) -> List[AutoScalingGroupInstance]:
        instances = ModelUtils.get_value_as_list('Instances', self._entry)
        if instances is None:
            return []
        result = []
        for instance in instances:
            result.append(AutoScalingGroupInstance(**instance))
        return result
