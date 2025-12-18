#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from abc import abstractmethod
from typing import Any, List, Optional, Union

import constructs
from aws_cdk import aws_iam as iam

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.infra_utils.arn_builder import ArnBuilder
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class ManagedPolicy(ResBaseConstruct, iam.ManagedPolicy):
    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        description: str,
        arn_builder: ArnBuilder,
        parameters: Union[RESParameters, BIParameters],
    ):
        self.scope = scope
        self.arn_builder = arn_builder
        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        super().__init__(
            scope,
            name,
            cluster_name=cluster_name,
            managed_policy_name=ResBaseConstruct.build_resource_name(  # type: ignore
                name, cluster_name
            ),
            statements=self.create_policy_statements(arn_builder),  # type: ignore
            description=description,  # type: ignore
            path=parameters.iam_resource_path_string,  # type: ignore
        )

    @staticmethod
    @abstractmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        pass


class Policy(ResBaseConstruct, iam.Policy):
    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        arn_builder: ArnBuilder,
        parameters: Union[RESParameters, BIParameters],
    ):
        self.scope = scope
        self.arn_builder = arn_builder
        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        super().__init__(
            scope,
            name,
            cluster_name=cluster_name,
            policy_name=ResBaseConstruct.build_resource_name(name, cluster_name),  # type: ignore
            statements=self.create_policy_statements(self.arn_builder),  # type: ignore
        )

    @staticmethod
    @abstractmethod
    def create_policy_statements(arn_builder: ArnBuilder) -> List[iam.PolicyStatement]:
        pass


class Role(ResBaseConstruct, iam.Role):
    MAX_NAME_LENGTH = 64

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        arn_builder: ArnBuilder,
        parameters: Union[RESParameters, BIParameters],
        description: str,
        assumed_by: List[Any],
        inline_policies: Optional[List[Policy]] = None,
        managed_policies: Optional[List[Any]] = None,
    ):
        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        role_path = parameters.iam_resource_path_string
        role_name = ResBaseConstruct.build_resource_name(name, cluster_name)
        if isinstance(role_name, tuple):
            role_name = " ".join(role_name)

        if len(role_name) > self.MAX_NAME_LENGTH:
            role_name = ResBaseConstruct.build_trimmed_resource_name(
                name,
                cluster_name,
                region_suffix=False,
                trim_length=self.MAX_NAME_LENGTH,
            )

        super().__init__(
            scope,
            name,
            cluster_name=cluster_name,
            role_name=role_name,  # type: ignore
            description=description,  # type: ignore
            assumed_by=self.build_assumed_by(assumed_by),  # type: ignore
            path=role_path,  # type: ignore
        )
        if inline_policies:
            for policy in inline_policies:
                self.attach_inline_policy(policy)
        if managed_policies:
            for managed_policy in managed_policies:
                if isinstance(managed_policy, str) and managed_policy.startswith(
                    "arn:"
                ):
                    name = managed_policy.split("/", maxsplit=1)[1]
                    self.add_managed_policy(
                        iam.ManagedPolicy.from_managed_policy_arn(
                            self, name, managed_policy
                        )
                    )
                else:
                    self.add_managed_policy(managed_policy)

    def build_assumed_by(self, assumed_by: List[Any]) -> iam.IPrincipal:
        principals = []
        for principal in assumed_by:
            if isinstance(principal, iam.PrincipalBase):
                principals.append(principal)
                continue
            principals.append(self.build_service_principal(principal))
        return iam.CompositePrincipal(*principals)


class InstanceProfile(ResBaseConstruct, iam.CfnInstanceProfile):
    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        parameters: Union[RESParameters, BIParameters],
        roles: List[iam.Role],
    ):
        cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)
        instance_profile_name = ResBaseConstruct.build_resource_name(name, cluster_name)

        role_names = []
        for role in roles:
            role_names.append(role.role_name)

        super().__init__(
            scope,
            name,
            cluster_name=cluster_name,
            instance_profile_name=instance_profile_name,  # type: ignore
            roles=role_names,  # type: ignore
        )
