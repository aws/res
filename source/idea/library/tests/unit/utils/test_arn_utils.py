#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

import pytest
from res.utils import arn_utils

PARTITION = "aws"
ACCOUNT_ID = "123456789012"
REGION = "us-east-1"

SETTINGS = {
    "cluster.aws.account_id": ACCOUNT_ID,
    "cluster.aws.region": REGION,
    "cluster.aws.partition": PARTITION,
}


def _mock_get_setting(key):
    return SETTINGS[key]


class TestArnUtils:
    """Test arn_utils module functions."""

    def test_build_arn_with_resource(self):
        result = arn_utils.build_arn(PARTITION, "s3", "", "", resource="my-bucket/key")
        assert result == f"arn:{PARTITION}:s3:::my-bucket/key"

    def test_build_arn_with_resource_type_and_id(self):
        result = arn_utils.build_arn(
            PARTITION,
            "iam",
            "",
            ACCOUNT_ID,
            resource_type="role",
            resource_id="my-role",
        )
        assert result == f"arn:{PARTITION}:iam::{ACCOUNT_ID}:role/my-role"

    def test_build_arn_with_resource_id_only(self):
        result = arn_utils.build_arn(
            PARTITION, "sqs", REGION, ACCOUNT_ID, resource_id="my-queue"
        )
        assert result == f"arn:{PARTITION}:sqs:{REGION}:{ACCOUNT_ID}:my-queue"

    def test_build_arn_with_custom_delimiter(self):
        result = arn_utils.build_arn(
            PARTITION,
            "iam",
            "",
            ACCOUNT_ID,
            resource_type="role",
            resource_id="my-role",
            resource_delimiter=":",
        )
        assert result == f"arn:{PARTITION}:iam::{ACCOUNT_ID}:role:my-role"

    def test_build_arn_raises_when_no_resource_or_resource_id(self):
        with pytest.raises(
            ValueError, match="Either 'resource' or 'resource_id' must be provided"
        ):
            arn_utils.build_arn(PARTITION, "s3", REGION, ACCOUNT_ID)

    @patch(
        "res.utils.arn_utils.cluster_settings.get_setting",
        side_effect=_mock_get_setting,
    )
    def test_get_arn_uses_defaults_from_cluster_settings(self, mock_get_setting):
        result = arn_utils.get_arn("s3", "my-bucket/*")
        assert result == f"arn:{PARTITION}:s3:{REGION}:{ACCOUNT_ID}:my-bucket/*"

    @patch(
        "res.utils.arn_utils.cluster_settings.get_setting",
        side_effect=_mock_get_setting,
    )
    def test_get_arn_overrides_account_and_region(self, mock_get_setting):
        override_account = "222222222222"
        result = arn_utils.get_arn(
            "iam", "role/my-role", aws_account_id=override_account, aws_region=""
        )
        assert result == f"arn:{PARTITION}:iam::{override_account}:role/my-role"
