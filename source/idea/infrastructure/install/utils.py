#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import inspect
import os
import pathlib
from pathlib import Path
from typing import Any, Callable, Dict, TypedDict, Union

import aws_cdk as cdk
import constructs
from aws_cdk import CfnCondition, Fn
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class LambdaCodeParams(TypedDict):
    handler: str
    code: aws_lambda.Code


class InfraUtils:

    @staticmethod
    def create_permission_boundary_applier(
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ) -> Callable[[constructs.Construct], None]:
        def apply_permission_boundary(scope: constructs.Construct) -> None:
            InfraUtils._attach_permission_boundaries(scope, parameters)

        return apply_permission_boundary

    @staticmethod
    def _attach_permission_boundaries(
        scope: constructs.Construct,
        parameters: Union[RESParameters, BIParameters] = RESParameters(),
    ) -> None:
        # Determine if IAMPermissionBoundary ARN input was provided in CFN.
        permission_boundary_provided = CfnCondition(
            scope,
            "PermissionBoundaryProvided",
            expression=Fn.condition_not(
                Fn.condition_equals(
                    parameters.get(CommonKey.IAM_PERMISSION_BOUNDARY), ""
                )
            ),
        )
        permission_boundary_policy = iam.ManagedPolicy.from_managed_policy_arn(
            scope,
            "PermissionBoundaryPolicy",
            Fn.condition_if(
                permission_boundary_provided.logical_id,
                parameters.get(CommonKey.IAM_PERMISSION_BOUNDARY),
                cdk.Aws.NO_VALUE,
            ).to_string(),
        )
        iam.PermissionsBoundary.of(scope).apply(permission_boundary_policy)

    @staticmethod
    def infra_root_dir() -> str:
        script_dir = Path(os.path.abspath(__file__))
        return str(script_dir.parent.parent)

    @staticmethod
    def resources_dir() -> str:
        return os.path.join(InfraUtils.infra_root_dir(), "resources")

    @staticmethod
    def lambda_functions_dir() -> str:
        return os.path.join(InfraUtils.resources_dir(), "lambda_functions")

    @staticmethod
    def get_handler_and_code_for_function(
        function: Callable[[Dict[str, Any], Any], Any]
    ) -> LambdaCodeParams:
        module = inspect.getmodule(function)
        if module is None or module.__file__ is None:
            raise ValueError("module not found")
        module_name = module.__name__.rsplit(".", 1)[1]
        folder = str(pathlib.Path(module.__file__).parent)

        return LambdaCodeParams(
            handler=f"{module_name}.{function.__name__}",
            code=aws_lambda.Code.from_asset(folder),
        )
