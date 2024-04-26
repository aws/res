#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Match, Template

from idea.infrastructure.install import handlers
from idea.infrastructure.install.stack import InstallStack
from tests.unit.infrastructure.install import util


def test_installer_event_handler_lambda_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "CustomResourceEventHandler"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Description": "Lambda to handle the CFN custom resource events",
                "Runtime": "python3.11",
                "Handler": "handlers.handle_custom_resource_lifecycle_event",
                "Environment": {
                    "Variables": {
                        "SFN_ARN": {
                            "Ref": util.get_logical_id(
                                stack, ["Installer", "InstallerStateMachine"]
                            )
                        }
                    }
                },
            }
        },
    )


def test_installer_wait_condition_lambda_creation(
    stack: InstallStack,
    template: Template,
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "WaitConditionResponseSender"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Description": "Lambda to send response using the wait condition callback",
                "Runtime": "python3.11",
                "Handler": "handlers.send_wait_condition_response",
            }
        },
    )


def test_installer_state_machine_created(
    stack: InstallStack, template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "InstallerStateMachine"],
        cfn_type="AWS::StepFunctions::StateMachine",
        props={
            "Properties": {
                # TODO: add the definition string for a snapshot test when it's done
                "DefinitionString": Match.any_value()
            }
        },
    )


def test_custom_resource_creation(stack: InstallStack, template: Template) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=["Installer", "Installer"],
        cfn_type="Custom::RES",
        props={
            "Properties": {
                handlers.EnvKeys.CALLBACK_URL: {
                    "Ref": util.get_logical_id(
                        stack,
                        [
                            "Installer",
                            f"InstallerWaitConditionHandle{stack.installer.get_wait_condition_suffix()}",
                        ],
                    )
                }
            },
        },
    )

    util.assert_resource_name_has_correct_type_and_props(
        stack,
        template,
        resources=[
            "Installer",
            f"InstallerWaitCondition{stack.installer.get_wait_condition_suffix()}",
        ],
        cfn_type="AWS::CloudFormation::WaitCondition",
        props={
            "Properties": {
                "Count": 1,
                "Handle": {
                    "Ref": util.get_logical_id(
                        stack,
                        [
                            "Installer",
                            f"InstallerWaitConditionHandle{stack.installer.get_wait_condition_suffix()}",
                        ],
                    )
                },
                "Timeout": "7200",
            },
            "DependsOn": [util.get_logical_id(stack, ["Installer", "Installer"])],
        },
    )
