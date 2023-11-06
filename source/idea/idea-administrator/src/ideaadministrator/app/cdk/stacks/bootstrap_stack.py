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

import aws_cdk as cdk
import constructs


class SocaBootstrapStack(cdk.Stack):
    """
    IDEA Bootstrap Stack
    Empty stack as CDK bootstrap needs a stack to bootstrap.

    CloudFormation Stack will not be created.
    """

    def __init__(self, scope: constructs.Construct, env: cdk.Environment, stack_name: str):
        super().__init__(scope, env=env, stack_name=stack_name)
