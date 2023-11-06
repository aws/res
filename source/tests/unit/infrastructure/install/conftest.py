#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from typing import Any, Optional

import aws_cdk
import pytest
from aws_cdk import assertions
from aws_cdk.assertions import Template

from idea.infrastructure.install.installer import Installer
from idea.infrastructure.install.parameters.parameters import Parameters
from idea.infrastructure.install.stack import InstallStack


@pytest.fixture
def cluster_name() -> str:
    return "foobar"


@pytest.fixture
def registry_name() -> str:
    return "fake-registry-name"


@pytest.fixture(autouse=True)
def patch_wait_condition_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_get_wait_condition_suffix(_: Any) -> str:
        return "timestamp"

    monkeypatch.setattr(
        Installer, "get_wait_condition_suffix", mock_get_wait_condition_suffix
    )


@pytest.fixture(params=[None, "fake_key_alias"])
def dynamodb_kms_key_alias(request: pytest.FixtureRequest) -> Optional[str]:
    value = getattr(request, "param")
    if value is None:
        return None
    return str(value)


@pytest.fixture
def stack(
    cluster_name: str, registry_name: str, dynamodb_kms_key_alias: Optional[str]
) -> InstallStack:
    synthesizer = aws_cdk.DefaultStackSynthesizer(generate_bootstrap_version_rule=False)
    env = aws_cdk.Environment(account="111111111111", region="us-east-1")
    app = aws_cdk.App()
    return InstallStack(
        app,
        "IDEAInstallStack",
        parameters=Parameters(cluster_name=cluster_name),
        registry_name=registry_name,
        dynamodb_kms_key_alias=dynamodb_kms_key_alias,
        env=env,
        synthesizer=synthesizer,
    )


@pytest.fixture
def template(stack: InstallStack) -> Template:
    return assertions.Template.from_stack(stack)
