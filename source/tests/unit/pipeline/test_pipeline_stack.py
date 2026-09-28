#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import os
from typing import Any

import aws_cdk
import aws_cdk as cdk
import pytest
from aws_cdk import assertions, pipelines

from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.stacks.install_stack import (
    PUBLIC_REGISTRY_NAME,
    InstallStack,
)
from idea.pipeline.stack import DeployStage, PipelineStack

TEST_CONTEXT = {"repository_name": "mock_repo", "branch_name": "mock_branch"}


@pytest.fixture
def template() -> assertions.Template:
    app = cdk.App(context=TEST_CONTEXT)
    stack = PipelineStack(app, "idea-pipeline")
    template = assertions.Template.from_stack(stack)
    return template


@pytest.fixture(autouse=True)
def patch_get_ecr_repo_arn_from_registry_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_get_ecr_repo_arn_from_registry_name(_: Any, registry_name: str) -> str:

        return "mock-ecr-arn"

    monkeypatch.setattr(
        InstallStack,
        "get_ecr_repo_arn_from_registry_name",
        mock_get_ecr_repo_arn_from_registry_name,
    )


def test_pipeline_created(template: assertions.Template) -> None:
    template.resource_count_is("AWS::CodePipeline::Pipeline", 1)


def _pipeline_stack(test_suite: str = None, **extra_context: str) -> PipelineStack:  # type: ignore
    context = dict(TEST_CONTEXT)
    if test_suite is not None:
        context["test_suite"] = test_suite
    context.update(extra_context)
    app = cdk.App(context=context)
    return PipelineStack(app, "idea-pipeline")


def _invoke_commands(step: Any) -> str:
    """Join the invoke commands of a CodeBuildStep for substring assertions."""
    return "\n".join(c for c in step.commands if "invoke integ-tests" in c)


def test_default_test_suite_is_dev() -> None:
    # No test_suite context -> dev (preserves existing per-commit behavior).
    stack = _pipeline_stack()
    assert stack._test_suite == "dev"
    assert "integ-tests.dev" in _invoke_commands(stack.get_suite_test_step("dev"))


def test_dev_smoke_step_runs_only_the_subset() -> None:
    # The per-commit (dev) smoke step is filtered to the AL2023 smoke subset.
    stack = _pipeline_stack("dev")
    commands = _invoke_commands(stack.get_smoke_test_step())
    assert "invoke integ-tests.smoke" in commands
    assert "--marker-expr smoke_subset" in commands


def test_nightly_suite_step_runs_full_suite() -> None:
    # nightly selects the nightly suite; the full smoke matrix is collected by the
    # suite step (smoke tests are @nightly-tagged), not by a subset-filtered step.
    stack = _pipeline_stack("nightly")
    assert stack._test_suite == "nightly"
    commands = _invoke_commands(stack.get_suite_test_step("nightly"))
    assert "integ-tests.nightly" in commands
    assert "smoke_subset" not in commands


def _step_role_actions(step: Any) -> set[str]:
    """All IAM actions granted to a CodeBuildStep's role policy statements."""
    actions: set[str] = set()
    for statement in step.role_policy_statements:
        action = statement.to_json().get("Action", [])
        actions.update([action] if isinstance(action, str) else action)
    return actions


@pytest.mark.parametrize("suite", ["nightly", "release"])
def test_full_smoke_suites_grant_smoke_permissions(suite: str) -> None:
    # nightly/release run the full smoke matrix, so their role must include the
    # smoke-only permissions absent from the API test set. Regression guard for
    # the dynamodb:UpdateItem denial that broke the migrated DCV session test.
    stack = _pipeline_stack(suite)
    actions = _step_role_actions(stack.get_suite_test_step(suite))
    assert "dynamodb:UpdateItem" in actions
    assert "s3:GetObject" in actions
    assert "secretsmanager:GetSecretValue" in actions


def test_dev_suite_step_excludes_smoke_permissions() -> None:
    # dev runs the smoke subset via the standalone smoke step (which carries its
    # own permissions), so the dev suite step must not over-grant them.
    stack = _pipeline_stack("dev")
    actions = _step_role_actions(stack.get_suite_test_step("dev"))
    assert "dynamodb:UpdateItem" not in actions


def test_test_suite_threaded_into_synth_env() -> None:
    # The Synth step must export TEST_SUITE so the self-mutating pipeline re-synths
    # with the same suite selection.
    stack = _pipeline_stack("nightly")
    synth_step = stack.pipeline.synth
    assert isinstance(synth_step, pipelines.CodeBuildStep)
    assert synth_step.env.get("TEST_SUITE") == "nightly"


def test_trigger_context_threaded_into_synth_env() -> None:
    # source_trigger / schedule_trigger / schedule_cron must be exported into the
    # Synth env so the self-mutating pipeline re-synths with the same trigger config.
    # Without this, UpdatePipeline would revert to the per-commit trigger and drop the
    # schedule on the first run.
    stack = _pipeline_stack(
        "nightly",
        source_trigger="none",
        schedule_trigger="true",
        schedule_cron="cron(0 9 ? * MON-FRI *)",
    )
    synth_step = stack.pipeline.synth
    assert isinstance(synth_step, pipelines.CodeBuildStep)
    assert synth_step.env.get("SOURCE_TRIGGER") == "none"
    assert synth_step.env.get("SCHEDULE_TRIGGER") == "true"
    assert synth_step.env.get("SCHEDULE_CRON") == "cron(0 9 ? * MON-FRI *)"


def test_scheduled_trigger_adds_eventbridge_rule() -> None:
    # schedule_trigger=true adds an EventBridge rule with the given cron that starts
    # the pipeline (used by the scheduled nightly pipelines).
    stack = _pipeline_stack(
        "nightly",
        source_trigger="none",
        schedule_trigger="true",
        schedule_cron="cron(0 9 ? * MON-FRI *)",
    )
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties(
        "AWS::Events::Rule",
        {"ScheduleExpression": "cron(0 9 ? * MON-FRI *)"},
    )


def test_no_scheduled_trigger_by_default() -> None:
    # Without schedule_trigger, there is no schedule-expression EventBridge rule
    # (default per-commit pipelines are unchanged).
    stack = _pipeline_stack()
    template = assertions.Template.from_stack(stack)
    rules = template.find_resources(
        "AWS::Events::Rule",
        {"Properties": {"ScheduleExpression": "cron(0 9 ? * MON-FRI *)"}},
    )
    assert rules == {}, f"unexpected scheduled rule(s): {list(rules)}"


def test_registry_name_set_correctly_from_context() -> None:
    # No context should be public registry name
    app = aws_cdk.App()
    app.node.set_context("ad_sync_registry_name", "ad_sync")
    stage = DeployStage(
        aws_cdk.App(context={"vpc_id": "vpc-0fakeexample0000001"}),
        "Stage",
        False,
        RESParameters(),
    )

    assert stage.install_stack.ad_sync_registry_name == PUBLIC_REGISTRY_NAME

    # context should override
    app = aws_cdk.App(context={"vpc_id": "vpc-0fakeexample0000001"})
    app.node.set_context("ad_sync_registry_name", "ad_sync")
    stage = DeployStage(app, "DeployStage", False, RESParameters())

    assert stage.install_stack.ad_sync_registry_name == "ad_sync"
