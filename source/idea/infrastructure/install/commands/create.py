#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Union

import aws_cdk

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters

EXE = "res-admin"


class Create:
    """
    Using supplied parameters, this generates commands for installing an environment
    automagically
    """

    def __init__(
        self, params: Union[RESParameters, BIParameters], lambda_layer_arn: str
    ):
        self.params = params
        self.lambda_layer_arn = lambda_layer_arn

    def get_commands(self) -> list[str]:
        return [
            f"{EXE} --version",
            *self._bootstrap(),
            *self._deploy(),
        ]

    def _bootstrap(self) -> list[str]:
        """
        Bootstrap the environment

        This creates a bucket and the bootstrap stack
        """
        return [f"{EXE} bootstrap {self._get_suffix()}"]

    def _deploy(self) -> list[str]:
        """
        Deploy the environment

        Using the local configuration (downloaded from dynamo earlier), deploy
        the environment
        """
        return [f"{EXE} deploy all {self._get_suffix()}"]

    def _get_suffix(self) -> str:
        return f"--cluster-name {self.params.get_str(CommonKey.CLUSTER_NAME)} --aws-region {aws_cdk.Aws.REGION}"
