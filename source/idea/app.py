#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import aws_cdk as cdk
from cdk_bootstrapless_synthesizer import BootstraplessStackSynthesizer

from idea.constants import (
    ARTIFACTS_BUCKET_PREFIX_NAME,
    INSTALL_STACK_NAME,
    PIPELINE_STACK_NAME,
)
from idea.infrastructure.install.stack import InstallStack
from idea.pipeline.stack import PipelineStack


def main() -> None:
    app = cdk.App()

    synthesizer = cdk.DefaultStackSynthesizer(generate_bootstrap_version_rule=False)
    publish_templates = app.node.try_get_context("publish_templates")
    is_publish_templates = (
        True if publish_templates and publish_templates.lower() == "true" else False
    )
    registry_name = app.node.try_get_context("registry_name")

    given_bucket_prefix = app.node.try_get_context("file_asset_prefix")
    bucket_prefix = (
        given_bucket_prefix
        if given_bucket_prefix
        else cdk.DefaultStackSynthesizer.DEFAULT_FILE_ASSET_PREFIX
    )

    install_synthesizer = (
        BootstraplessStackSynthesizer(
            file_asset_bucket_name=f"{ARTIFACTS_BUCKET_PREFIX_NAME}-${{AWS::Region}}",
            file_asset_prefix=bucket_prefix,
        )
        if is_publish_templates
        else synthesizer
    )

    PipelineStack(app, PIPELINE_STACK_NAME, synthesizer=synthesizer)
    InstallStack(
        app,
        INSTALL_STACK_NAME,
        registry_name=registry_name,
        synthesizer=install_synthesizer,
    )

    app.synth()
