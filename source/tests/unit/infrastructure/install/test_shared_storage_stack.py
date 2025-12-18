#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk.assertions import Template

from idea.infrastructure.install import constants
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.stacks.shared_storage_stack import SharedStorageStack
from ideadatamodel import constants as idea_constants  # type: ignore
from tests.unit.infrastructure.install import util


def test_stack_description(shared_storage_template: Template) -> None:
    description = shared_storage_template.to_json()["Description"]
    assert "ModuleId: shared-storage" in description
    assert "Version:" in description


def test_shared_storage_security_group_creation(
    shared_storage_stack: SharedStorageStack, shared_storage_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        shared_storage_stack.nested_stack,
        shared_storage_template,
        resources=["shared-storage-security-group-construct"],
        cfn_type="AWS::EC2::SecurityGroup",
        props={
            "Properties": {
                "GroupDescription": "Shared Storage Security Group",
            }
        },
    )


def test_security_group_ingress_rules(
    shared_storage_stack: SharedStorageStack, shared_storage_template: Template
) -> None:
    # Test that the security group has the required ingress rules
    security_groups = shared_storage_template.find_resources("AWS::EC2::SecurityGroup")

    # Find the shared storage security group
    shared_storage_sg = None
    for logical_id, sg in security_groups.items():
        if (
            sg.get("Properties", {}).get("GroupDescription")
            == "Shared Storage Security Group"
        ):
            shared_storage_sg = sg
            break

    assert shared_storage_sg is not None

    ingress_rules = shared_storage_sg["Properties"]["SecurityGroupIngress"]

    # Check for required ports: 2049 (NFS), 988 (FSx), 1021-1023 (FSx range)
    required_ports = [2049, 988]
    found_ports = []

    for rule in ingress_rules:
        if rule["IpProtocol"] == "tcp":
            from_port = rule["FromPort"]
            to_port = rule["ToPort"]

            if from_port == to_port and from_port in required_ports:
                found_ports.append(from_port)
            elif from_port == 1021 and to_port == 1023:
                found_ports.append("1021-1023")

    assert 2049 in found_ports, "Should have NFS port 2049"
    assert 988 in found_ports, "Should have FSx port 988"
    assert "1021-1023" in found_ports, "Should have FSx port range 1021-1023"


def test_internal_efs_file_system_creation(
    shared_storage_stack: SharedStorageStack, shared_storage_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        shared_storage_stack.nested_stack,
        shared_storage_template,
        resources=["internal-storage-efs"],
        cfn_type="AWS::EFS::FileSystem",
        props={
            "Properties": {
                "Encrypted": True,
                "PerformanceMode": "generalPurpose",
                "ThroughputMode": "bursting",
            }
        },
    )


def test_vpc_lookup_lambda_role_creation(
    shared_storage_stack: SharedStorageStack, shared_storage_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        shared_storage_stack.nested_stack,
        shared_storage_template,
        resources=["shared-storage-vpc-vpc-lookup-construct", "ServiceRole"],
        cfn_type="AWS::IAM::Role",
        props={
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                        }
                    ],
                },
            }
        },
    )


def test_vpc_lookup_lambda_creation(
    shared_storage_stack: SharedStorageStack, shared_storage_template: Template
) -> None:
    util.assert_resource_name_has_correct_type_and_props(
        shared_storage_stack.nested_stack,
        shared_storage_template,
        resources=["shared-storage-vpc-vpc-lookup-construct"],
        cfn_type="AWS::Lambda::Function",
        props={
            "Properties": {
                "Handler": "vpc_lookup_handler.handler",
                "Runtime": constants.RES_COMMON_LAMBDA_RUNTIME.to_string(),
            }
        },
    )


def test_lambda_function_has_correct_timeout(
    shared_storage_stack: SharedStorageStack, shared_storage_template: Template
) -> None:
    # Test that the VPC lookup Lambda has the correct timeout
    lambda_functions = shared_storage_template.find_resources("AWS::Lambda::Function")

    # Find the VPC lookup lambda
    vpc_lookup_lambda = None
    for logical_id, lambda_func in lambda_functions.items():
        handler = lambda_func.get("Properties", {}).get("Handler", "")
        if "vpc_lookup_handler.handler" in handler:
            vpc_lookup_lambda = lambda_func
            break

    assert vpc_lookup_lambda is not None
    assert vpc_lookup_lambda["Properties"]["Timeout"] == 180
