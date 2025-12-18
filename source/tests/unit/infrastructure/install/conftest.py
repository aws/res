#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Optional

import aws_cdk
import pytest
from aws_cdk import assertions
from aws_cdk.assertions import Template

from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.infrastructure.install.stacks.cluster_manager_stack import ClusterManagerStack
from idea.infrastructure.install.stacks.cluster_stack import ClusterStack
from idea.infrastructure.install.stacks.identity_stack import IdentityStack
from idea.infrastructure.install.stacks.install_stack import InstallStack
from idea.infrastructure.install.stacks.res_base_stack import ResBaseStack
from idea.infrastructure.install.stacks.res_finalizer_stack import ResFinalizerStack
from idea.infrastructure.install.stacks.shared_storage_stack import SharedStorageStack
from idea.infrastructure.install.stacks.virtual_desktop_controller_stack import (
    VirtualDesktopControllerStack,
)

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

    synthesizer = aws_cdk.DefaultStackSynthesizer(generate_bootstrap_version_rule=False)
    env = aws_cdk.Environment(account="111111111111", region="us-east-1")
    app = aws_cdk.App(context={"vpc_id": "vpc-0fakeexample0000001"})
    return InstallStack(
        app,
        "IDEAInstallStack",
        parameters=RESParameters(cluster_name=cluster_name),
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
def identity_stack(stack: InstallStack) -> IdentityStack:
    return stack.identity_stack


@pytest.fixture(scope="session")
def identity_template(identity_stack: IdentityStack) -> Template:
    return assertions.Template.from_stack(identity_stack.nested_stack)


@pytest.fixture(scope="session")
def res_finalizer_stack(stack: InstallStack) -> ResFinalizerStack:
    return stack.res_finalizer_stack


@pytest.fixture(scope="session")
def res_finalizer_template(res_finalizer_stack: ResFinalizerStack) -> Template:
    return assertions.Template.from_stack(res_finalizer_stack.nested_stack)


@pytest.fixture(scope="session")
def shared_storage_stack(stack: InstallStack) -> SharedStorageStack:
    return stack.shared_storage_stack


@pytest.fixture(scope="session")
def shared_storage_template(shared_storage_stack: SharedStorageStack) -> Template:
    return assertions.Template.from_stack(shared_storage_stack.nested_stack)


@pytest.fixture(scope="session")
def cluster_stack(stack: InstallStack) -> ClusterStack:
    return stack.cluster_stack


@pytest.fixture(scope="session")
def cluster_template(cluster_stack: ClusterStack) -> Template:
    return assertions.Template.from_stack(cluster_stack.nested_stack)


@pytest.fixture(scope="session")
def vdc_stack(stack: InstallStack) -> VirtualDesktopControllerStack:
    return stack.vdc_stack


@pytest.fixture(scope="session")
def vdc_template(vdc_stack: VirtualDesktopControllerStack) -> Template:
    return assertions.Template.from_stack(vdc_stack.nested_stack)


@pytest.fixture(scope="session")
def cluster_manager_stack(stack: InstallStack) -> ClusterManagerStack:
    return stack.cluster_manager_stack


@pytest.fixture(scope="session")
def cluster_manager_template(cluster_manager_stack: ClusterManagerStack) -> Template:
    return assertions.Template.from_stack(cluster_manager_stack.nested_stack)
