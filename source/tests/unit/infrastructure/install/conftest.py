#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Optional

import aws_cdk
import pytest
from aws_cdk import assertions
from aws_cdk.assertions import Template

from idea.infrastructure.install.installer import Installer
from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.stacks.ad_sync_stack import ADSyncStack
from idea.infrastructure.install.stacks.install_stack import InstallStack
from idea.infrastructure.install.stacks.res_base_stack import ResBaseStack
from idea.infrastructure.install.stacks.res_finalizer_stack import ResFinalizerStack

REGISTRY_NAME = "fake-registry-name"


@pytest.fixture(scope="session")
def cluster_name() -> str:
    return "foobar"


@pytest.fixture(scope="session")
def registry_name() -> str:
    return REGISTRY_NAME


@pytest.fixture(scope="session")
def stack(
    cluster_name: str,
    registry_name: str,
) -> InstallStack:

    monkeypatch = pytest.MonkeyPatch()

    monkeypatch.setattr(
        InstallStack,
        "get_ecr_repo_arn_from_registry_name",
        lambda _, registry_name: "mock-ecr-arn",
    )

    monkeypatch.setattr(
        InstallStack,
        "get_private_registry_name",
        lambda _, registry_name: "fake-registry-name",
    )

    monkeypatch.setattr(Installer, "get_wait_condition_suffix", lambda _: "timestamp")

    synthesizer = aws_cdk.DefaultStackSynthesizer(generate_bootstrap_version_rule=False)
    env = aws_cdk.Environment(account="111111111111", region="us-east-1")
    app = aws_cdk.App(context={"vpc_id": "vpc-0fakeexample0000001"})
    return InstallStack(
        app,
        "IDEAInstallStack",
        parameters=RESParameters(cluster_name=cluster_name),
        installer_registry_name=registry_name,
        ad_sync_registry_name=registry_name,
        env=env,
        synthesizer=synthesizer,
    )


@pytest.fixture(scope="session")
def template(stack: InstallStack) -> Template:
    return assertions.Template.from_stack(stack)


@pytest.fixture(scope="session")
def res_base_stack(stack: InstallStack) -> ResBaseStack:
    return stack.res_base_stack


@pytest.fixture(scope="session")
def res_base_template(res_base_stack: ResBaseStack) -> Template:
    return assertions.Template.from_stack(res_base_stack.nested_stack)


@pytest.fixture(scope="session")
def ad_sync_stack(stack: InstallStack) -> ADSyncStack:
    return stack.ad_sync_stack


@pytest.fixture(scope="session")
def ad_sync_template(ad_sync_stack: ADSyncStack) -> Template:
    return assertions.Template.from_stack(ad_sync_stack.nested_stack)


@pytest.fixture(scope="session")
def res_finalizer_stack(stack: InstallStack) -> ResFinalizerStack:
    return stack.res_finalizer_stack


@pytest.fixture(scope="session")
def res_finalizer_template(res_finalizer_stack: ResFinalizerStack) -> Template:
    return assertions.Template.from_stack(res_finalizer_stack.nested_stack)
