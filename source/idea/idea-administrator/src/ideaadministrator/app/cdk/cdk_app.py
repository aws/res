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

from ideadatamodel import constants
from ideasdk.utils import Utils, EnvironmentUtils
from ideaadministrator.app.cdk.stacks import (
    SchedulerStack,
)

import aws_cdk as cdk
from aws_cdk import Aspects
from cdk_nag import AwsSolutionsChecks


class CdkApp:
    """
    IDEA CDK App
    """

    def __init__(self, cluster_name: str,
                 module_name: str,
                 module_id: str,
                 aws_region: str,
                 deployment_id: str,
                 termination_protection: bool,
                 aws_profile: str = None):

        self.cluster_name = cluster_name
        self.module_name = module_name
        self.module_id = module_id
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.deployment_id = deployment_id
        self.termination_protection = termination_protection

        session = Utils.create_boto_session(aws_region=aws_region, aws_profile=aws_profile)

        sts = session.client('sts')
        result = sts.get_caller_identity()
        account_id = Utils.get_value_as_string('Account', result)

        self.cdk_app = cdk.App()

        # add cdk nag scan
        enable_nag_scan = Utils.get_as_bool(EnvironmentUtils.get_environment_variable('IDEA_ADMIN_ENABLE_CDK_NAG_SCAN'), True)
        if enable_nag_scan:
            Aspects.of(self.cdk_app).add(AwsSolutionsChecks())

        self.cdk_env = cdk.Environment(
            account=account_id,
            region=aws_region
        )

    def scheduler_stack(self):
        SchedulerStack(
            scope=self.cdk_app,
            cluster_name=self.cluster_name,
            aws_region=self.aws_region,
            aws_profile=self.aws_profile,
            module_id=self.module_id,
            deployment_id=self.deployment_id,
            termination_protection=self.termination_protection,
            env=self.cdk_env
        )

    def build_stack(self):
        if self.module_name == constants.MODULE_SCHEDULER:
            self.scheduler_stack()

    def invoke(self):
        self.build_stack()
        self.cdk_app.synth()
