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

from ideaadministrator.app_context import AdministratorContext
from ideaadministrator.app.cdk.constructs import SocaBaseConstruct
from ideasdk.utils import Utils

from typing import Dict, Optional, List
import constructs
import aws_cdk as cdk
from aws_cdk import (
    aws_iam as iam,
    aws_backup as backup,
    aws_events as events
)


class BackupPlan(SocaBaseConstruct):
    """
    Backup Plan
    """

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.Construct,
                 backup_plan_name: str,
                 backup_plan_config: Dict,
                 backup_vault: backup.IBackupVault,
                 backup_role: iam.IRole):
        self.scope = scope
        self.backup_vault = backup_vault
        self.backup_plan_name = backup_plan_name
        self.backup_plan_config = backup_plan_config
        self.backup_role = backup_role

        super().__init__(context, name)

        self.backup_plan: Optional[backup.BackupPlan] = None
        self.backup_selection: Optional[backup.BackupSelection] = None

        self._build_backup_plan()

    def get_backup_plan_arn(self) -> str:
        return self.backup_plan.backup_plan_arn

    def _build_backup_plan_rules(self) -> List[backup.BackupPlanRule]:

        result = []
        rules = Utils.get_value_as_dict('rules', self.backup_plan_config, default={})

        for rule_name, rule in rules.items():
            delete_after_days = Utils.get_value_as_int('delete_after_days', rule)
            start_window_minutes = Utils.get_value_as_int('start_window_minutes', rule)
            completion_window_minutes = Utils.get_value_as_int('completion_window_minutes', rule)
            schedule_expression = Utils.get_value_as_string('schedule_expression', rule)
            move_to_cold_storage_after_days = Utils.get_value_as_int('move_to_cold_storage_after_days', rule, default=None)

            assert delete_after_days is not None
            assert start_window_minutes is not None
            assert completion_window_minutes is not None
            assert schedule_expression is not None

            move_to_cold_storage_after = None
            if move_to_cold_storage_after_days is not None:
                move_to_cold_storage_after = cdk.Duration.days(move_to_cold_storage_after_days)

            result.append(backup.BackupPlanRule(
                rule_name=rule_name,
                backup_vault=self.backup_vault,
                start_window=cdk.Duration.minutes(start_window_minutes),
                completion_window=cdk.Duration.minutes(completion_window_minutes),
                delete_after=cdk.Duration.days(delete_after_days),
                move_to_cold_storage_after=move_to_cold_storage_after,
                schedule_expression=events.Schedule.expression(schedule_expression)
            ))

        return result

    def _build_backup_plan(self):
        # build rules
        backup_plan_rules = self._build_backup_plan_rules()

        # build backup plan
        backup_plan_enable_windows_vss = Utils.get_value_as_bool('enable_windows_vss', self.backup_plan_config, default=False)
        backup_plan = backup.BackupPlan(
            self.scope, self.backup_plan_name,
            backup_plan_name=self.backup_plan_name,
            backup_plan_rules=backup_plan_rules,
            backup_vault=self.backup_vault,
            windows_vss=backup_plan_enable_windows_vss
        )

        # build backup selection
        selection = Utils.get_value_as_dict('selection', self.backup_plan_config, default={})

        tags = Utils.get_value_as_list('tags', selection, [])
        selection_tags = Utils.convert_custom_tags_to_key_value_pairs(tags)

        resources = []
        for key, value in selection_tags.items():
            resources.append(backup.BackupResource(
                tag_condition=backup.TagCondition(
                    key=key,
                    value=value,
                    operation=backup.TagOperation.STRING_EQUALS
                )
            ))

        backup_selection = backup.BackupSelection(
            self.scope, f'{self.backup_plan_name}-selection',
            backup_plan=backup_plan,
            resources=resources,
            backup_selection_name=f'{self.backup_plan_name}-selection',
            role=self.backup_role
        )

        self.backup_plan = backup_plan
        self.backup_selection = backup_selection
