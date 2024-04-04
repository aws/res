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


class SecurityGroup(SocaBaseModel):
    group_id: str
    group_name: str


class Policy(SocaBaseModel):
    policy_arn: str
    policy_name: str


class Script(SocaBaseModel):
    script_location: str
    arguments: Optional[List[str]]


class ScriptEvents(SocaBaseModel):
    on_vdi_start: Optional[List[Script]]
    on_vdi_configured: Optional[List[Script]]


class Scripts(SocaBaseModel):
    windows: Optional[ScriptEvents]
    linux: Optional[ScriptEvents]


class Project(SocaBaseModel):
    project_id: Optional[str]
    name: Optional[str]
    title: Optional[str]
    description: Optional[str]
    enabled: Optional[bool]
    ldap_groups: Optional[List[str]] = []
    users: Optional[List[str]]
    enable_budgets: Optional[bool]
    budget: Optional[AwsProjectBudget]
    tags: Optional[List[SocaKeyValue]]
    created_on: Optional[datetime]
    updated_on: Optional[datetime]

    security_groups: Optional[List[str]] = []
    policy_arns: Optional[List[str]]
    scripts: Optional[Scripts]

    def __eq__(self, other):
        eq = True
        eq = eq and self.name == other.name
        eq = eq and self.title == other.title
        eq = eq and self.description == other.description
        eq = eq and self.enable_budgets == other.enable_budgets
        eq = eq and self.budget == other.budget

        self_ldap_groups = self.ldap_groups if self.ldap_groups else []
        other_ldap_groups = other.ldap_groups if other.ldap_groups else []
        eq = eq and len(self_ldap_groups) == len(other_ldap_groups)
        eq = eq and all(ldap_group in self_ldap_groups for ldap_group in other_ldap_groups)

        self_users = self.users if self.users else []
        other_users = other.users if other.users else []
        eq = eq and len(self_users) == len(other_users)
        eq = eq and all(user in self_users for user in other_users)

        self_tags = self.tags if self.tags else []
        other_tags = other.tags if other.tags else []
        eq = eq and len(self_tags) == len(other_tags)
        eq = eq and all(tag in self_tags for tag in other_tags)

        self_policy_arns = self.policy_arns if self.policy_arns else []
        other_policy_arns = other.policy_arns if other.policy_arns else []
        eq = eq and len(self_policy_arns) == len(other_policy_arns)
        eq = eq and all(policy_arn in self_policy_arns for policy_arn in other_policy_arns)

        self_security_groups = self.security_groups if self.security_groups else []
        other_security_groups = other.security_groups if other.security_groups else []
        eq = eq and len(self_security_groups) == len(other_security_groups)
        eq = eq and all(security_group in self_security_groups for security_group in other_security_groups)

        eq = eq and self.scripts == other.scripts

        return eq

    def is_enabled(self) -> bool:
        return ModelUtils.get_as_bool(self.enabled, False)

    def is_budgets_enabled(self) -> bool:
        if ModelUtils.get_as_bool(self.enable_budgets, False):
            if self.budget is None:
                return False
            return ModelUtils.is_not_empty(self.budget.budget_name)
        return False
