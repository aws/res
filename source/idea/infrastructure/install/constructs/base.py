#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, Optional, Union

import aws_cdk as cdk
import constructs

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.utils import InfraUtils
from ideadatamodel import constants, errorcodes, exceptions  # type: ignore


class ResBaseConstruct(constructs.Construct):
    def __init__(
        self,
        cluster_name: str,
        region: str,
        name: str,
        scope: constructs.Construct,
        parameters: Union[RESParameters, BIParameters],
        **kwargs: Dict[str, Any],
    ) -> None:
        self._cluster_name = cluster_name
        self._region = region
        self._name = name
        self._construct_id: str = self.get_construct_id()
        self._parameters = parameters
        self.kwargs = kwargs

        super().__init__(scope, self.construct_id)

        self.apply_permission_boundary = InfraUtils.create_permission_boundary_applier(
            self._parameters
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
        return self.build_resource_name(self.name)

    @property
    def resource_name_prefix(self) -> str:
        return f"{self._cluster_name}"

    # override if required
    def get_construct_id(self) -> str:
        return f"{self.name}-construct"

    def build_resource_name(self, name: str, region_suffix: bool = False) -> str:
        prefix = self.resource_name_prefix
        resource_name = f"{prefix}-{name}"
        if region_suffix:
            aws_region = self._region
            resource_name = f"{resource_name}-{aws_region}"
        return resource_name

    def add_common_tags(
        self, construct: Optional[constructs.IConstruct] = None
    ) -> None:
        if construct is None:
            construct = self
        cdk.Tags.of(construct).add(constants.IDEA_TAG_NAME, self.resource_name)
        cdk.Tags.of(construct).add(
            constants.IDEA_TAG_ENVIRONMENT_NAME, self._cluster_name
        )
