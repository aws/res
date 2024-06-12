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

from ideadatamodel import (
    SocaBaseModel
)

from typing import Optional

class RoleAssignment(SocaBaseModel):
    resource_key: Optional[str]
    actor_key: Optional[str]
    resource_id: Optional[str]
    actor_id: Optional[str]
    resource_type: Optional[str]
    actor_type: Optional[str]
    role_id: Optional[str]

    def __eq__(self, other):
        eq = True
        eq = eq and self.resource_key == other.resource_key
        eq = eq and self.actor_key == other.actor_key
        eq = eq and self.resource_id == other.resource_id
        eq = eq and self.actor_id == other.actor_id
        eq = eq and self.resource_type == other.resource_type
        eq = eq and self.actor_type == other.actor_type
        eq = eq and self.role_id == other.role_id
        
        return eq
