#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import aws_cdk
import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.stack import PUBLIC_REGISTRY_NAME
from idea.pipeline.stack import DeployStage, PipelineStack

TEST_CONTEXT = {"repository_name": "mock_repo", "branch_name": "mock_branch"}


@pytest.fixture
def template() -> assertions.Template:
    app = cdk.App(context=TEST_CONTEXT)
    stack = PipelineStack(app, "idea-pipeline")
    template = assertions.Template.from_stack(stack)
    return template


def test_pipeline_created(template: assertions.Template) -> None:
    template.resource_count_is("AWS::CodePipeline::Pipeline", 1)


def test_registry_name_set_correctly_from_context() -> None:
    # No context should be public registry name
    stage = DeployStage(aws_cdk.App(), "Stage", RESParameters())

    assert stage.install_stack.registry_name == PUBLIC_REGISTRY_NAME

    # context should override
    app = aws_cdk.App()
    app.node.set_context("registry_name", "foo")
    stage = DeployStage(app, "DeployStage", RESParameters())

    assert stage.install_stack.registry_name == "foo"
