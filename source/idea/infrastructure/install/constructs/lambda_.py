#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Callable, Dict, Optional, Union

import constructs
from aws_cdk import aws_lambda as lambda_

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils import utils
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class Function(ResBaseConstruct, lambda_.Function):

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        handler: Union[Callable[[Dict[str, Any], Any], Any], str],
        parameters: Union[RESParameters, BIParameters],
        code_directory_string: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ):
        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        if callable(handler):
            handler_code_kwargs = utils.InfraUtils.get_handler_and_code_for_function(
                handler
            )
        else:
            if not code_directory_string:
                raise Exception(
                    "Invalid lambda construct. code_directory_string is required if hanlder not callable."
                )
            handler_code_kwargs = {
                "handler": handler,
                "code": lambda_.Code.from_asset(code_directory_string),
            }

        super().__init__(
            scope,
            name,
            cluster_name=cluster_name,
            **handler_code_kwargs,  # type: ignore
            function_name=ResBaseConstruct.build_resource_name(name, cluster_name),  # type: ignore
            **kwargs,  # type: ignore
        )
