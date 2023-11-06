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
from ideadatamodel import constants

from typing import Dict, Any, Optional, List
import arrow


class CloudFormationStack:
    """
    Soca wrapper class over Describe Cloud Formation Stacks result entry
    """

    def __init__(self, entry: Dict[str, Any]):
        self._entry = entry

    def get_tag(self, key: str) -> Optional[str]:
        tags = ModelUtils.get_value_as_list('Tags', self._entry)
        if tags is None:
            return None
        for tag in tags:
            tag_key = ModelUtils.get_value_as_string('Key', tag)
            if tag_key == key:
                return ModelUtils.get_value_as_string('Value', tag)
        return None

    @property
    def stack_id(self) -> str:
        return ModelUtils.get_value_as_string('StackId', self._entry)

    @property
    def stack_status(self) -> str:
        return ModelUtils.get_value_as_string('StackStatus', self._entry)

    @property
    def creation_time(self) -> Optional[arrow.Arrow]:
        if 'CreationTime' in self._entry:
            return arrow.get(self._entry.get('CreationTime'))
        return None

    @property
    def soca_keep_forever(self) -> bool:
        value = self.get_tag(constants.IDEA_TAG_KEEP_FOREVER)
        return ModelUtils.get_as_bool(value, default=False)

    @property
    def soca_terminate_when_idle(self) -> int:
        value = self.get_tag(constants.IDEA_TAG_TERMINATE_WHEN_IDLE)
        return ModelUtils.get_as_int(value, default=0)

    @property
    def soca_job_group(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_JOB_GROUP)

    @property
    def soca_job_queue(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_JOB_QUEUE)

    @property
    def soca_queue_type(self) -> Optional[str]:
        return self.get_tag(constants.IDEA_TAG_QUEUE_TYPE)

    @property
    def outputs(self) -> Optional[List[Dict]]:
        return ModelUtils.get_value_as_list('Outputs', self._entry)

    def get_output(self, key: str) -> Optional[Dict]:
        outputs = self.outputs
        if ModelUtils.is_empty(outputs):
            return None
        for output in outputs:
            output_key = ModelUtils.get_value_as_string('OutputKey', output)
            if output_key == key:
                return output
        return None
