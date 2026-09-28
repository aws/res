#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import base64
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest
from res import constants
from res.resources import launch_templates

TEST_CLUSTER_NAME = "res-test"
TEST_SESSION_ID = "test_session_id"
TEST_LAUNCH_TEMPLATE_ID = "lt-0123456789abcdef0"
TEST_AMI_ID = "ami-0abc"
TEST_KMS_KEY_ID = "alias/aws/ebs"
TEST_INSTANCE_PROFILE_ARN = "arn:aws:iam::123:instance-profile/vdi-host"
TEST_USER_DATA = "#!/bin/bash\necho hello"
TEST_PLACEMENT = {"Tenancy": "default"}

VIRTUAL_DESKTOP = {
    "idea_session_id": TEST_SESSION_ID,
    "base_os": "amazonlinux2",
    "hibernation_enabled": False,
    "server": {
        "instance_profile_arn": TEST_INSTANCE_PROFILE_ARN,
        "security_groups": ["sg-a"],
        "root_volume_size": {"value": 50, "unit": "gb"},
    },
}
SOFTWARE_STACK = {"ami_id": TEST_AMI_ID, "base_os": "amazonlinux2"}
AWS_TAGS = [
    {"Key": constants.RES_TAG_ENVIRONMENT_NAME, "Value": TEST_CLUSTER_NAME},
    {"Key": constants.RES_TAG_MODULE_ID, "Value": constants.MODULE_ID_VDC},
    {"Key": constants.RES_TAG_NODE_TYPE, "Value": constants.NODE_TYPE_DCV_HOST},
    {"Key": "Name", "Value": "res-test-my-desktop"},
]


class TestCreateForSession:

    @patch("res.resources.launch_templates.cluster_settings.get_setting")
    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_creates_launch_template_with_expected_shape(
        self, mock_aws_provider, mock_get_setting
    ):
        mock_get_setting.side_effect = lambda key: {
            "cluster.cluster_name": TEST_CLUSTER_NAME,
        }.get(key)
        mock_ec2 = MagicMock()
        mock_ec2.create_launch_template.return_value = {
            "LaunchTemplate": {
                "LaunchTemplateId": TEST_LAUNCH_TEMPLATE_ID,
                "LatestVersionNumber": 1,
            }
        }
        mock_aws_provider.return_value.ec2.return_value = mock_ec2

        launch_template_id, version = launch_templates.create_for_session(
            virtual_desktop=VIRTUAL_DESKTOP,
            software_stack=SOFTWARE_STACK,
            aws_tags=AWS_TAGS,
            metadata_http_tokens="required",
            kms_key_id=TEST_KMS_KEY_ID,
            placement=TEST_PLACEMENT,
            user_data=TEST_USER_DATA,
        )

        assert launch_template_id == TEST_LAUNCH_TEMPLATE_ID
        assert version == 1
        mock_ec2.create_launch_template.assert_called_once()
        call_kwargs = mock_ec2.create_launch_template.call_args[1]
        assert (
            call_kwargs["LaunchTemplateName"]
            == f"{TEST_CLUSTER_NAME}-{TEST_SESSION_ID}-lt"
        )

        launch_template_data = call_kwargs["LaunchTemplateData"]
        assert launch_template_data["ImageId"] == TEST_AMI_ID
        assert launch_template_data["UserData"] == base64.b64encode(
            TEST_USER_DATA.encode("utf-8")
        ).decode("utf-8")
        assert (
            launch_template_data["IamInstanceProfile"]["Arn"]
            == TEST_INSTANCE_PROFILE_ARN
        )
        assert launch_template_data["HibernationOptions"]["Configured"] is False
        assert launch_template_data["MetadataOptions"]["HttpTokens"] == "required"
        assert launch_template_data["Placement"] == TEST_PLACEMENT

        block_device = launch_template_data["BlockDeviceMappings"][0]
        assert block_device["Ebs"]["VolumeSize"] == 50
        assert block_device["Ebs"]["KmsKeyId"] == TEST_KMS_KEY_ID

        network_interface = launch_template_data["NetworkInterfaces"][0]
        assert network_interface["Groups"] == ["sg-a"]
        assert "SubnetId" not in network_interface

    @patch("res.resources.launch_templates.cluster_settings.get_setting")
    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_hibernation_enabled_is_baked_into_template(
        self, mock_aws_provider, mock_get_setting
    ):
        mock_get_setting.side_effect = lambda key: {
            "cluster.cluster_name": TEST_CLUSTER_NAME,
        }.get(key)
        mock_ec2 = MagicMock()
        mock_ec2.create_launch_template.return_value = {
            "LaunchTemplate": {
                "LaunchTemplateId": TEST_LAUNCH_TEMPLATE_ID,
                "LatestVersionNumber": 1,
            }
        }
        mock_aws_provider.return_value.ec2.return_value = mock_ec2

        launch_templates.create_for_session(
            virtual_desktop={**VIRTUAL_DESKTOP, "hibernation_enabled": True},
            software_stack=SOFTWARE_STACK,
            aws_tags=AWS_TAGS,
            metadata_http_tokens="required",
            kms_key_id=TEST_KMS_KEY_ID,
            placement=TEST_PLACEMENT,
            user_data="",
        )

        call_kwargs = mock_ec2.create_launch_template.call_args[1]
        assert (
            call_kwargs["LaunchTemplateData"]["HibernationOptions"]["Configured"]
            is True
        )

    @patch("res.resources.launch_templates.ec2_utils.get_systems_manager_parameter")
    @patch("res.resources.launch_templates.cluster_settings.get_setting")
    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_ssm_arn_ami_is_resolved(
        self, mock_aws_provider, mock_get_setting, mock_get_systems_manager_parameter
    ):
        mock_get_setting.side_effect = lambda key: {
            "cluster.cluster_name": TEST_CLUSTER_NAME,
        }.get(key)
        mock_get_systems_manager_parameter.return_value = {"Name": "/res/ami/amzn2"}
        mock_ec2 = MagicMock()
        mock_ec2.create_launch_template.return_value = {
            "LaunchTemplate": {
                "LaunchTemplateId": TEST_LAUNCH_TEMPLATE_ID,
                "LatestVersionNumber": 1,
            }
        }
        mock_aws_provider.return_value.ec2.return_value = mock_ec2

        launch_templates.create_for_session(
            virtual_desktop=VIRTUAL_DESKTOP,
            software_stack={
                "ami_id": "arn:aws:ssm:us-east-1:123:parameter/res/ami/amzn2"
            },
            aws_tags=AWS_TAGS,
            metadata_http_tokens="required",
            kms_key_id=TEST_KMS_KEY_ID,
            placement=TEST_PLACEMENT,
            user_data="",
        )

        call_kwargs = mock_ec2.create_launch_template.call_args[1]
        assert (
            call_kwargs["LaunchTemplateData"]["ImageId"] == "resolve:ssm:/res/ami/amzn2"
        )

    @patch("res.resources.launch_templates.cluster_settings.get_setting")
    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_template_tagged_with_environment_for_cleanup(
        self, mock_aws_provider, mock_get_setting
    ):
        mock_get_setting.side_effect = lambda key: {
            "cluster.cluster_name": TEST_CLUSTER_NAME,
        }.get(key)
        mock_ec2 = MagicMock()
        mock_ec2.create_launch_template.return_value = {
            "LaunchTemplate": {
                "LaunchTemplateId": TEST_LAUNCH_TEMPLATE_ID,
                "LatestVersionNumber": 1,
            }
        }
        mock_aws_provider.return_value.ec2.return_value = mock_ec2

        launch_templates.create_for_session(
            virtual_desktop=VIRTUAL_DESKTOP,
            software_stack=SOFTWARE_STACK,
            aws_tags=AWS_TAGS,
            metadata_http_tokens="required",
            kms_key_id=TEST_KMS_KEY_ID,
            placement=TEST_PLACEMENT,
            user_data="",
        )

        call_kwargs = mock_ec2.create_launch_template.call_args[1]
        tag_specs = call_kwargs["TagSpecifications"]
        assert len(tag_specs) == 1
        assert tag_specs[0]["ResourceType"] == "launch-template"
        tag_dict = {tag["Key"]: tag["Value"] for tag in tag_specs[0]["Tags"]}
        assert tag_dict[constants.RES_TAG_ENVIRONMENT_NAME] == TEST_CLUSTER_NAME
        assert tag_dict[constants.RES_TAG_MODULE_ID] == constants.MODULE_ID_VDC
        assert tag_dict[constants.RES_TAG_NODE_TYPE] == constants.NODE_TYPE_DCV_HOST
        assert tag_dict["idea_session_id"] == TEST_SESSION_ID

    @patch("res.resources.launch_templates.cluster_settings.get_setting")
    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_raises_on_ec2_client_error(self, mock_aws_provider, mock_get_setting):
        mock_get_setting.side_effect = lambda key: {
            "cluster.cluster_name": TEST_CLUSTER_NAME,
        }.get(key)
        mock_ec2 = MagicMock()
        mock_ec2.create_launch_template.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InvalidParameterValue", "Message": "bad ami"}},
            "CreateLaunchTemplate",
        )
        mock_aws_provider.return_value.ec2.return_value = mock_ec2

        with pytest.raises(botocore.exceptions.ClientError):
            launch_templates.create_for_session(
                virtual_desktop=VIRTUAL_DESKTOP,
                software_stack=SOFTWARE_STACK,
                aws_tags=AWS_TAGS,
                metadata_http_tokens="required",
                kms_key_id=TEST_KMS_KEY_ID,
                placement=TEST_PLACEMENT,
                user_data="",
            )


class TestDeleteForSession:

    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_deletes_launch_template(self, mock_aws_provider):
        mock_ec2 = MagicMock()
        mock_aws_provider.return_value.ec2.return_value = mock_ec2

        launch_templates.delete_for_session(TEST_LAUNCH_TEMPLATE_ID)

        mock_ec2.delete_launch_template.assert_called_once_with(
            LaunchTemplateId=TEST_LAUNCH_TEMPLATE_ID
        )

    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_no_op_when_launch_template_id_missing(self, mock_aws_provider):
        launch_templates.delete_for_session(None)
        launch_templates.delete_for_session("")

        mock_aws_provider.return_value.ec2.return_value.delete_launch_template.assert_not_called()

    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_swallows_not_found_error(self, mock_aws_provider):
        mock_ec2 = MagicMock()
        mock_ec2.delete_launch_template.side_effect = botocore.exceptions.ClientError(
            {
                "Error": {
                    "Code": "InvalidLaunchTemplateId.NotFound",
                    "Message": "not found",
                }
            },
            "DeleteLaunchTemplate",
        )
        mock_aws_provider.return_value.ec2.return_value = mock_ec2

        launch_templates.delete_for_session(TEST_LAUNCH_TEMPLATE_ID)

    @patch("res.resources.launch_templates.AwsClientProvider")
    def test_swallows_unexpected_error(self, mock_aws_provider):
        mock_ec2 = MagicMock()
        mock_ec2.delete_launch_template.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "boom"}},
            "DeleteLaunchTemplate",
        )
        mock_aws_provider.return_value.ec2.return_value = mock_ec2

        launch_templates.delete_for_session(TEST_LAUNCH_TEMPLATE_ID)
