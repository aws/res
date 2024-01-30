#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import dataclasses

import aws_cdk
from aws_cdk.assertions import Template

from idea.infrastructure.install.parameters.base import Attributes, Base
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.directoryservice import DirectoryServiceKey
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.stack import InstallStack


def test_parameters_are_generated(cluster_name: str) -> None:
    parameters = RESParameters(cluster_name=cluster_name)
    env = aws_cdk.Environment(account="111111111111", region="us-east-1")
    app = aws_cdk.App()
    InstallStack(
        app,
        "IDEAInstallStack",
        parameters=parameters,
        env=env,
    )

    assert parameters._generated
    assert parameters.cluster_name == cluster_name
    assert parameters.get(CommonKey.CLUSTER_NAME).default == cluster_name
    assert parameters.get(CommonKey.INFRASTRUCTURE_HOST_SUBNETS).default is None


def test_parameters_can_be_passed_via_context() -> None:
    parameters = RESParameters(
        cluster_name="foo", infrastructure_host_subnets=["a", "b"]
    )

    stack = aws_cdk.Stack()
    for key, value in parameters.to_context().items():
        stack.node.set_context(key, value)

    context_params = RESParameters.from_context(stack)

    assert context_params.cluster_name == parameters.cluster_name
    assert (
        context_params.infrastructure_host_subnets
        == parameters.infrastructure_host_subnets
    )


def test_parameter_list_default_set_correctly() -> None:
    parameters = RESParameters(infrastructure_host_subnets=["a", "b"])
    parameters.generate(aws_cdk.Stack())
    assert parameters.get(CommonKey.INFRASTRUCTURE_HOST_SUBNETS).default == "a,b"


def test_fields_only_includes_base_parameters() -> None:
    @dataclasses.dataclass
    class TestParameters(Base):
        name: str = Base.parameter(Attributes(id=CommonKey.CLUSTER_NAME))
        other: str = "not defined as a base parameter"

    fields = list(TestParameters._fields())
    assert len(fields) == 1
    field, attributes = fields[0]
    assert field.name == "name"
    assert attributes.id == CommonKey.CLUSTER_NAME


def test_parameters_only_generates_cfn_parameters_for_base_parameter_attributes(
    stack: InstallStack,
    template: Template,
) -> None:
    parameters = template.find_parameters(logical_id="*")

    cfn_keys = set(parameters.keys())
    defined_keys = set(attributes.id.value for _, attributes in RESParameters._fields())

    assert cfn_keys == defined_keys


def test_secrets_use_no_echo(
    stack: InstallStack,
    template: Template,
) -> None:
    for parameter in (
        DirectoryServiceKey.ROOT_USERNAME,
        DirectoryServiceKey.ROOT_PASSWORD,
    ):
        template.has_parameter(parameter, props={"NoEcho": True})
