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

from ideasdk.protocols import SocaContextProtocol, IamPermissionUtilProtocol
from typing import List, Dict


class IamPermissionUtil(IamPermissionUtilProtocol):

    def __init__(self, context: SocaContextProtocol):
        self._context = context
        self._logger = context.logger()

    def has_permission(self, action_names: List[str],
                       resource_arns: List[str] = None,
                       context_entries: List[Dict] = None):
        """
        Checks if the current scheduler instance has given permissions
        This method assumes Scheduler is run using InstanceProfile credentials

        request syntax:
        response = client.simulate_principal_policy(
            PolicySourceArn='string',
            PolicyInputList=[
                'string',
            ],
            PermissionsBoundaryPolicyInputList=[
                'string',
            ],
            ActionNames=[
                'string',
            ],
            ResourceArns=[
                'string',
            ],
            ResourcePolicy='string',
            ResourceOwner='string',
            CallerArn='string',
            ContextEntries=[
                {
                    'ContextKeyName': 'string',
                    'ContextKeyValues': [
                        'string',
                    ],
                    'ContextKeyType': 'string'|'stringList'|'numeric'|'numericList'|'boolean'|'booleanList'|'ip'|'ipList'|'binary'|'binaryList'|'date'|'dateList'
                },
            ],
            ResourceHandlingOption='string',
            MaxItems=123,
            Marker='string'
        )

        :param action_names:
        :param resource_arns:
        :param context_entries:
        :return:
        """

        document = self._context.ec2_metadata_util().get_instance_identity_document()
        security_credentials = self._context.ec2_metadata_util().get_iam_security_credentials()
        instance_profile_role_arn = f'arn:aws:iam::{document.accountId}:role/{security_credentials}'

        if resource_arns is None:
            resource_arns = []

        if context_entries is None:
            context_entries = []

        simulate_result = self._context.aws().iam().simulate_principal_policy(
            PolicySourceArn=instance_profile_role_arn,
            ActionNames=action_names,
            ResourceArns=resource_arns,
            ContextEntries=context_entries
        )

        if 'EvaluationResults' not in simulate_result:
            return False

        allow = True
        for eval_result in simulate_result['EvaluationResults']:
            if 'EvalDecision' not in eval_result:
                allow = False
                break
            if eval_result['EvalDecision'] != 'allowed':
                allow = False
                break
        return allow
