#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Union

import aws_cdk as cdk
import constructs

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class ResBaseStack(ResBaseConstruct):
    def __init__(
        self,
        scope: constructs.Construct,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ):
        self.parameters = parameters
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        super().__init__(
            self.cluster_name,
            cdk.Aws.REGION,
            "res-base",
            scope,
            self.parameters,
        )

        self.nested_stack = cdk.NestedStack(
            scope,
            "res-base",
            description="Nested RES Base Stack",
        )
        self.apply_permission_boundary(self.nested_stack)
