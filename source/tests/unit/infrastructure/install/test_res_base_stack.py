# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Template


def test_stack_description(res_base_template: Template) -> None:
    res_base_template.template_matches({"Description": "Nested RES Base Stack"})
