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
from datetime import datetime

class ProjectPermissions(SocaBaseModel):
    update_personnel: Optional[bool]
    update_status: Optional[bool]

class VDIPermissions(SocaBaseModel):
    create_sessions: Optional[bool]
    create_terminate_others_sessions: Optional[bool]

class Role(SocaBaseModel):
    role_id: Optional[str]
    name: Optional[str]
    description: Optional[str]
    projects: Optional[ProjectPermissions]
    vdis: Optional[VDIPermissions]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]

    def __eq__(self, other):
        eq = True
        eq = eq and self.role_id == other.role_id
        eq = eq and self.name == other.name
        eq = eq and self.description == other.description
        eq = eq and self.projects == other.projects
        eq = eq and self.vdis == other.vdis
        
        return eq
