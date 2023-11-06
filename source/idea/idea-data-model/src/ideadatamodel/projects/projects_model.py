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
    SocaBaseModel,
    SocaKeyValue,
    AwsProjectBudget
)
from ideadatamodel.model_utils import ModelUtils

from typing import Optional, List
from datetime import datetime


class Project(SocaBaseModel):
    project_id: Optional[str]
    name: Optional[str]
    title: Optional[str]
    description: Optional[str]
    enabled: Optional[bool]
    ldap_groups: Optional[List[str]]
    enable_budgets: Optional[bool]
    budget: Optional[AwsProjectBudget]
    tags: Optional[List[SocaKeyValue]]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]

    def is_enabled(self) -> bool:
        return ModelUtils.get_as_bool(self.enabled, False)

    def is_budgets_enabled(self) -> bool:
        if ModelUtils.get_as_bool(self.enable_budgets, False):
            if self.budget is None:
                return False
            return ModelUtils.is_not_empty(self.budget.budget_name)
        return False
