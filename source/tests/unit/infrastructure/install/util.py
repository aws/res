#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, List

import aws_cdk
from aws_cdk import Stack, assertions
from constructs import IConstruct

from idea.infrastructure.install.stacks.install_stack import InstallStack


def assert_resource_name_has_correct_type_and_props(
    stack: Stack,
    template: assertions.Template,
    resources: List[str],
    cfn_type: str,
    props: Any,
) -> None:
    template.has_resource(type=cfn_type, props=props)
    existing = template.find_resources(type=cfn_type, props=props)
    assert len(existing) >= 1
    assert get_logical_id(stack, resources) in existing


def get_logical_id(stack: Stack, resources: List[str]) -> str:
    node = stack.node
    child: IConstruct = stack
    for resource in resources:
        child = node.find_child(resource)
        node = child.node

    cfn_element = node.default_child
    if cfn_element is None:
        cfn_element = child
    assert isinstance(cfn_element, aws_cdk.CfnElement)
    return stack.get_logical_id(cfn_element)
