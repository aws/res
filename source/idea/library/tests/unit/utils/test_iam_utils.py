#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock, patch

# Mock the IAM client before importing iam_utils (it creates a client at import time)
with patch(
    "res.clients.aws.aws_provider.AwsClientProvider.iam", return_value=MagicMock()
):
    from res.utils import iam_utils


CLUSTER_NAME = "res-env"
AWS_REGION = "us-east-1"
ACCOUNT_ID = "123456789012"
PARTITION = "aws"
IAM_RESOURCE_PATH = "/test-path/"
IAM_RESOURCE_PREFIX = "iam-prefix-"

SETTINGS = {
    "cluster.cluster_name": CLUSTER_NAME,
    "cluster.aws.region": AWS_REGION,
    "cluster.aws.account_id": ACCOUNT_ID,
    "cluster.aws.partition": PARTITION,
    "cluster.iam.iam_resource_path": IAM_RESOURCE_PATH,
    "cluster.iam.iam_resource_prefix": IAM_RESOURCE_PREFIX,
}


def _mock_get_setting(key, default=None):
    return SETTINGS.get(key, default)


class TestIAMUtils:
    """Test iam_utils module functions."""

    def test_get_vdi_role_path_with_prefix(self):
        result = iam_utils._get_vdi_role_path("my-cluster", "us-west-2", "/my-path/")
        assert result == "/my-path/my-cluster-us-west-2/vdi"

    def test_get_vdi_role_path_without_prefix(self):
        result = iam_utils._get_vdi_role_path("my-cluster", "us-west-2")
        assert result == "my-cluster-us-west-2/vdi"

    def test_get_vdi_role_name_with_prefix(self):
        result = iam_utils._get_vdi_role_name("my-cluster", "my-project", "pfx-")
        assert result == "pfx-my-cluster-vdi-my-project"

    def test_get_vdi_role_name_without_prefix(self):
        result = iam_utils._get_vdi_role_name("my-cluster", "my-project")
        assert result == "my-cluster-vdi-my-project"

    @patch(
        "res.utils.arn_utils.cluster_settings.get_setting",
        side_effect=_mock_get_setting,
    )
    @patch(
        "res.utils.iam_utils.cluster_settings.get_setting",
        side_effect=_mock_get_setting,
    )
    def test_build_vdi_instance_profile_arn(self, mock_iam_setting, mock_arn_setting):
        result = iam_utils.build_vdi_instance_profile_arn("test-project")

        assert result == (
            f"arn:{PARTITION}:iam::{ACCOUNT_ID}:"
            f"instance-profile{IAM_RESOURCE_PATH}{CLUSTER_NAME}-{AWS_REGION}/vdi/"
            f"{IAM_RESOURCE_PREFIX}{CLUSTER_NAME}-vdi-test-project"
        )

    @patch(
        "res.utils.arn_utils.cluster_settings.get_setting",
        side_effect=_mock_get_setting,
    )
    @patch(
        "res.utils.iam_utils.cluster_settings.get_setting",
        side_effect=_mock_get_setting,
    )
    def test_build_vdi_instance_profile_arn_different_projects(
        self, mock_iam_setting, mock_arn_setting
    ):
        result_a = iam_utils.build_vdi_instance_profile_arn("project-a")
        result_b = iam_utils.build_vdi_instance_profile_arn("project-b")

        assert "vdi/iam-prefix-res-env-vdi-project-a" in result_a
        assert "vdi/iam-prefix-res-env-vdi-project-b" in result_b
        assert result_a != result_b

    @patch("res.resources.cluster_settings.get_setting")
    def test_build_vdi_instance_profile_arn_missing_iam_path_defaults(
        self, mock_get_setting
    ):
        """Verify fallback to '/' and '' when iam_resource_path/prefix settings are missing."""
        from res.exceptions import SettingNotFound

        def _side_effect(key):
            if key in (
                "cluster.iam.iam_resource_path",
                "cluster.iam.iam_resource_prefix",
            ):
                raise SettingNotFound(f"Setting not found: {key}")
            return SETTINGS[key]

        mock_get_setting.side_effect = _side_effect

        result = iam_utils.build_vdi_instance_profile_arn("test-project")

        assert (
            f"instance-profile/{CLUSTER_NAME}-{AWS_REGION}/vdi/{CLUSTER_NAME}-vdi-test-project"
            in result
        )
