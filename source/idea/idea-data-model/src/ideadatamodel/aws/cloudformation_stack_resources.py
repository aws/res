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


class CloudFormationStackResources:
    """
    Soca wrapper class over Describe Cloud Formation Stack Resources result entry
    """

    def __init__(self, entry: Dict[str, Any]):
        self._entry = entry

    def get_spot_fleet_request_id(self) -> Optional[str]:
        resources = ModelUtils.get_value_as_list('StackResources', self._entry)
        if resources is None:
            return None
        for resource in resources:
            resource_type = ModelUtils.get_value_as_string('ResourceType', resource)
            if resource_type is None:
                continue
            if resource_type == 'AWS::EC2::SpotFleet':
                return ModelUtils.get_value_as_string('PhysicalResourceId', resource)
        return None

    def get_auto_scaling_group_name(self) -> Optional[str]:
        resources = ModelUtils.get_value_as_list('StackResources', self._entry)
        if resources is None:
            return None
        for resource in resources:
            resource_type = ModelUtils.get_value_as_string('ResourceType', resource)
            if resource_type is None:
                continue
            if resource_type == 'AWS::AutoScaling::AutoScalingGroup':
                return ModelUtils.get_value_as_string('PhysicalResourceId', resource)
        return None
