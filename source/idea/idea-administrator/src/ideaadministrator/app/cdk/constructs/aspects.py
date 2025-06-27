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

import constructs
from aws_cdk import (
    Stack,
    aws_iam as iam,
    IAspect
)
import jsii
import secrets
import string

PREFIX_MAX_LENGTH = 12
POLICY_MAX_LENGTH = 128
ROLE_MAX_LENGTH = 64
RANDOM_SUFFIX_LENGTH = 4
ROLE_AVAILABLE_LENGTH = ROLE_MAX_LENGTH - PREFIX_MAX_LENGTH - RANDOM_SUFFIX_LENGTH
POLICY_AVAILABLE_LENGTH = POLICY_MAX_LENGTH - PREFIX_MAX_LENGTH - RANDOM_SUFFIX_LENGTH

@jsii.implements(IAspect)
class IAMResourcePrefixAspect:
    def __init__(self, prefix: str):
        self.prefix = prefix

    @jsii.member(jsii_name="visit")
    def visit(self, node: constructs.IConstruct) -> None:
        random_suffix = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(RANDOM_SUFFIX_LENGTH))
        if isinstance(node, iam.CfnRole):
            if node.role_name and "-" in node.role_name:
                node.role_name = f"{self.prefix}{node.role_name}"
            else:
                node.role_name = f"{self.prefix}{Stack.of(node).resolve(node.logical_id)[:ROLE_AVAILABLE_LENGTH]}{random_suffix}"
                
        elif isinstance(node, iam.CfnPolicy):
            if node.policy_name and "-" in node.policy_name:
                node.policy_name = f"{self.prefix}{node.policy_name}"
            else:
                node.policy_name = f"{self.prefix}{Stack.of(node).resolve(node.logical_id)[:POLICY_AVAILABLE_LENGTH]}{random_suffix}"
                
        elif isinstance(node, iam.CfnManagedPolicy):
            if node.managed_policy_name and "-" in node.managed_policy_name:
                node.managed_policy_name = f"{self.prefix}{node.managed_policy_name}"
            else:
                node.managed_policy_name = f"{self.prefix}{Stack.of(node).resolve(node.logical_id)[:POLICY_AVAILABLE_LENGTH]}{random_suffix}"
        
        elif isinstance(node, iam.CfnInstanceProfile):
            if node.instance_profile_name and "-" in node.instance_profile_name:
                node.instance_profile_name = (
                    f"{self.prefix}{node.instance_profile_name}"
                )
            else:
                node.instance_profile_name = f"{self.prefix}{Stack.of(node).resolve(node.logical_id)[:POLICY_AVAILABLE_LENGTH]}{random_suffix}"


@jsii.implements(IAspect)
class IAMResourcePathAspect:
    def __init__(self, path: str):
        self.path = path

    @jsii.member(jsii_name="visit")
    def visit(self, node: constructs.IConstruct) -> None:
        # For IAM Roles
        if isinstance(node, iam.CfnRole) or isinstance(node, iam.CfnManagedPolicy) or isinstance(node, iam.CfnInstanceProfile):
            node.path = self.path
