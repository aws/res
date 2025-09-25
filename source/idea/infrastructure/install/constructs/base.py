#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aws_cdk as cdk
import constructs
import jsii
from aws_cdk import Aspects, CfnCondition, IAspect
from aws_cdk import aws_iam as iam
from cdk_nag import NagSuppressions

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.infra_utils.utils import InfraUtils
from idea.infrastructure.install.parameters.parameters import RESParameters
from ideadatamodel import constants, errorcodes, exceptions  # type: ignore


@jsii.implements(IAspect)
class ConditionAspect:
    """
    Aspect to apply a condition on all the resources within the construct
    """

    condition: CfnCondition

    def __init__(self, condition: CfnCondition):
        self.condition = condition

    @jsii.member(jsii_name="visit")
    def visit(self, node: constructs.IConstruct) -> None:
        if hasattr(node, "cfn_options"):
            node.cfn_options.condition = self.condition


class ResBaseConstruct(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        cluster_name: str,
        parameters: Optional[Union[RESParameters, BIParameters]] = None,
        **kwargs: Dict[str, Any],
    ) -> None:
        self._cluster_name = cluster_name
        self._region = cdk.Aws.REGION
        self._name = name
        self._construct_id: str = self.get_construct_id()
        self._parameters = parameters
        self.kwargs = kwargs

        super().__init__(scope, self._construct_id, **kwargs)

        self.apply_permission_boundary = InfraUtils.create_permission_boundary_applier(
            self._parameters  # type: ignore
        )

        self.add_common_tags()

    @property
    def name(self) -> str:
        if not self._name:
            raise exceptions.SocaException(
                error_code=errorcodes.GENERAL_ERROR,
                message='Invalid CDK Construct. "name" is required.',
            )
        return self._name

    @property
    def construct_id(self) -> str:
        return self._construct_id

    @property
    def resource_name(self) -> str:
        return self.build_resource_name(
            self.name, self.resource_name_prefix, self._region
        )

    @property
    def resource_name_prefix(self) -> str:
        return self._cluster_name

    # override if required
    def get_construct_id(self) -> str:
        return f"{self.name}-construct"

    @staticmethod
    def build_resource_name(
        name: str,
        resource_name_prefix: str,
        region: str = cdk.Aws.REGION,
        region_suffix: bool = False,
    ) -> str:
        prefix = resource_name_prefix
        resource_name = f"{prefix}-{name}"
        if region_suffix:
            resource_name = f"{resource_name}-{region}"
        return resource_name

    def add_common_tags(
        self, construct: Optional[constructs.IConstruct] = None
    ) -> None:
        if construct is None:
            construct = self
        cdk.Tags.of(construct).add(
            constants.IDEA_TAG_NAME,
            self.resource_name,
            exclude_resource_types=["AWS::Events::Rule"],
        )
        cdk.Tags.of(construct).add(
            constants.IDEA_TAG_ENVIRONMENT_NAME,
            self._cluster_name,
            exclude_resource_types=["AWS::Events::Rule"],
        )

    # trimmed format - {prefix}-{region}-{name[:10]}-{hash}
    @staticmethod
    def build_trimmed_resource_name(
        name: str,
        prefix: str,
        region: str = cdk.Aws.REGION,
        region_suffix: bool = False,
        trim_length: int = 64,
    ) -> str:
        suffix = ""
        if region_suffix:
            suffix = f"-{region}"

        resource_name = f"{prefix}-{name}{suffix}"
        trimmed_resource_name = f"{prefix}{suffix}-{name[:10]}-{ResBaseConstruct.shake_256(data=resource_name, num_bytes=int((trim_length - 12 - len(prefix) - len(suffix)) / 2))}"
        return trimmed_resource_name

    @staticmethod
    def build_service_principal(service_name: str) -> iam.ServicePrincipal:
        service_fqdn = f"{service_name}.{cdk.Aws.URL_SUFFIX}"
        return iam.ServicePrincipal(service_fqdn)

    @staticmethod
    def shake_256(data: str, num_bytes: int = 5) -> str:
        return hashlib.shake_256(data.encode("utf-8")).hexdigest(num_bytes)

    @staticmethod
    def get_res_release_version() -> str:
        # Cannot retrieve version number from importlib.metadata.version directly since setuptools
        # strips leading zeros in date based releases: https://github.com/pypa/setuptools/issues/302
        project_dir = Path(__file__).parent.parent.parent.parent.parent.parent.resolve()
        with project_dir.joinpath("RES_VERSION.txt").open("r") as f:
            return f.read().strip()

    def apply_condition_aspect(self, condition: CfnCondition) -> None:
        Aspects.of(self).add(ConditionAspect(condition))

    def add_retain_on_delete(
        self, construct: Optional[constructs.IConstruct] = None
    ) -> None:
        if not construct:
            construct = self
        construct.node.find_child("Resource").cfn_options.deletion_policy = (  # type: ignore
            cdk.CfnDeletionPolicy.RETAIN
        )
