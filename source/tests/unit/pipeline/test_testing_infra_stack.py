#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from idea.infrastructure.install.parameters.parameters import RESParameters
from idea.pipeline.testing_infra_stack import StorageTemplateUrls, TestingInfraStack

# Minimal parameters for test
TEST_PARAMS = RESParameters(
    cluster_name="test-env",
    vpc_id="vpc-12345",
    client_ip="10.0.0.0/16",
    infrastructure_host_subnets=["subnet-aaa", "subnet-bbb"],
    load_balancer_subnets=["subnet-ccc"],
    vdi_subnets=["subnet-aaa", "subnet-bbb"],
)

TEST_TEMPLATE_URLS = StorageTemplateUrls(
    efs="https://example.com/efs.yaml",
    fsx_lustre="https://example.com/lustre.yaml",
    fsx_ontap="https://example.com/ontap.yaml",
)

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "idea",
    "pipeline",
    "resources",
    "storage-config.yaml",
)


@pytest.fixture
def template() -> assertions.Template:
    app = cdk.App()
    stack = TestingInfraStack(
        app,
        "TestingInfra",
        parameters=TEST_PARAMS,
        template_urls=TEST_TEMPLATE_URLS,
        config_file=CONFIG_PATH,
    )
    return assertions.Template.from_stack(stack)


@pytest.fixture
def template_with_ad() -> assertions.Template:
    app = cdk.App()
    stack = TestingInfraStack(
        app,
        "TestingInfra",
        parameters=TEST_PARAMS,
        template_urls=TEST_TEMPLATE_URLS,
        config_file=CONFIG_PATH,
        ad_params={
            "ActiveDirectoryName": "corp.res.com",
            "DNSServerIPs": "10.0.0.1,10.0.0.2",
            "ServiceAccountCredentialsSecretArn": "arn:aws:secretsmanager:us-east-1:123456789:secret:test",
            "ComputersOU": "OU=Computers,OU=RES,DC=corp,DC=res,DC=com",
            "SudoersGroupName": "RESAdministrators",
        },
    )
    return assertions.Template.from_stack(stack)


class TestTestingInfraStack:
    """Unit tests for the TestingInfraStack CDK class."""

    def test_efs_nested_stack_created(self, template: assertions.Template) -> None:
        """Verify EFS nested stack is created with correct template URL."""
        template.has_resource(
            "AWS::CloudFormation::Stack",
            assertions.Match.object_like(
                {
                    "Properties": {
                        "TemplateURL": "https://example.com/efs.yaml",
                    }
                }
            ),
        )

    def test_fsx_lustre_nested_stack_created(
        self, template: assertions.Template
    ) -> None:
        """Verify FSx Lustre nested stack is created with correct template URL."""
        template.has_resource(
            "AWS::CloudFormation::Stack",
            assertions.Match.object_like(
                {
                    "Properties": {
                        "TemplateURL": "https://example.com/lustre.yaml",
                    }
                }
            ),
        )

    def test_fsx_ontap_nested_stack_created(
        self, template: assertions.Template
    ) -> None:
        """Verify FSx ONTAP nested stack is created with correct template URL."""
        template.has_resource(
            "AWS::CloudFormation::Stack",
            assertions.Match.object_like(
                {
                    "Properties": {
                        "TemplateURL": "https://example.com/ontap.yaml",
                    }
                }
            ),
        )

    def test_s3_buckets_created(self, template: assertions.Template) -> None:
        """Verify 5 S3 buckets are created (3 RW + 2 RO)."""
        template.resource_count_is("AWS::S3::Bucket", 5)

    def test_ssm_parameters_created(self, template: assertions.Template) -> None:
        """Verify SSM parameters are created for resource identifiers."""
        # EFS FileSystemId + Lustre FileSystemId + ONTAP FileSystemId +
        # ONTAP StorageVirtualMachineId + ONTAP SecurityGroupId +
        # 5 S3 BucketName + 5 S3 AccessMode = 15
        template.resource_count_is("AWS::SSM::Parameter", 15)

    def test_efs_ssm_parameter_name(self, template: assertions.Template) -> None:
        """Verify EFS SSM parameter has correct naming pattern."""
        template.has_resource_properties(
            "AWS::SSM::Parameter",
            assertions.Match.object_like(
                {
                    "Name": "/res/testing-infra/test-env/integ-test-efs/FileSystemId",
                }
            ),
        )

    def test_s3_bucket_naming(self, template: assertions.Template) -> None:
        """Verify S3 bucket naming includes cluster name, account, and region."""
        template.has_resource_properties(
            "AWS::S3::Bucket",
            assertions.Match.object_like(
                {
                    "BucketName": {
                        "Fn::Join": [
                            "",
                            assertions.Match.array_with(
                                [
                                    "test-env-integ-test-s3-rw-1-",
                                    {"Ref": "AWS::AccountId"},
                                    "-",
                                    {"Ref": "AWS::Region"},
                                ]
                            ),
                        ]
                    },
                }
            ),
        )

    def test_ontap_receives_ad_dns_ips(
        self, template_with_ad: assertions.Template
    ) -> None:
        """Verify ONTAP stack receives AD DNS IPs when provided."""
        template_with_ad.has_resource(
            "AWS::CloudFormation::Stack",
            assertions.Match.object_like(
                {
                    "Properties": {
                        "TemplateURL": "https://example.com/ontap.yaml",
                        "Parameters": assertions.Match.object_like(
                            {
                                "EnableActiveDirectory": "true",
                                "DNSServerIPs": "10.0.0.1,10.0.0.2",
                            }
                        ),
                    }
                }
            ),
        )

    def test_nested_stacks_count(self, template: assertions.Template) -> None:
        """Verify 3 nested stacks (EFS + Lustre + ONTAP)."""
        template.resource_count_is("AWS::CloudFormation::Stack", 3)

    def test_stack_can_be_instantiated(self) -> None:
        """Verify TestingInfraStack can be instantiated without error."""
        # This is tested at the DeployStage level, not here directly.
        # Just verify the stack can be instantiated without error.
        app = cdk.App()
        stack = TestingInfraStack(
            app,
            "TestingInfra",
            parameters=TEST_PARAMS,
            template_urls=TEST_TEMPLATE_URLS,
            config_file=CONFIG_PATH,
        )
        assert stack is not None
