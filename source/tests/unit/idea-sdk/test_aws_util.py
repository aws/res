#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from unittest.mock import MagicMock, call, patch

import pytest
from ideasdk.aws.aws_util import AWSUtil

from ideadatamodel import Policy


class TestInvokeAwsListing:
    """Tests for invoke_aws_listing pagination fix."""

    def setup_method(self):
        self.context = MagicMock()
        self.aws_util = AWSUtil(self.context)

    def test_marker_based_pagination_returns_all_pages(self):
        """Verify that marker-based pagination iterates through all pages."""
        mock_fn = MagicMock()
        mock_fn.side_effect = [
            {"Items": [{"id": "1"}], "Marker": "page2_token"},
            {"Items": [{"id": "2"}], "Marker": "page3_token"},
            {"Items": [{"id": "3"}]},
        ]

        def result_cb(response):
            return response.get("Items", [])

        results = self.aws_util.invoke_aws_listing(
            fn=mock_fn,
            result_cb=result_cb,
            marker_based_paging=True,
        )

        assert len(results) == 3
        assert results == [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        assert mock_fn.call_count == 3

    def test_next_token_based_pagination_returns_all_pages(self):
        """Verify that NextToken-based pagination iterates through all pages."""
        mock_fn = MagicMock()
        mock_fn.side_effect = [
            {"Items": [{"id": "1"}], "NextToken": "token2"},
            {"Items": [{"id": "2"}], "NextToken": "token3"},
            {"Items": [{"id": "3"}]},
        ]

        def result_cb(response):
            return response.get("Items", [])

        results = self.aws_util.invoke_aws_listing(
            fn=mock_fn,
            result_cb=result_cb,
            marker_based_paging=False,
        )

        assert len(results) == 3
        assert mock_fn.call_count == 3

    def test_single_page_result(self):
        """Verify single-page responses work correctly."""
        mock_fn = MagicMock()
        mock_fn.return_value = {"Items": [{"id": "1"}, {"id": "2"}]}

        def result_cb(response):
            return response.get("Items", [])

        results = self.aws_util.invoke_aws_listing(
            fn=mock_fn,
            result_cb=result_cb,
        )

        assert len(results) == 2
        assert mock_fn.call_count == 1

    def test_empty_result(self):
        """Verify empty responses return empty list."""
        mock_fn = MagicMock()
        mock_fn.return_value = {"Items": []}

        def result_cb(response):
            return response.get("Items", [])

        results = self.aws_util.invoke_aws_listing(
            fn=mock_fn,
            result_cb=result_cb,
        )

        assert results == []

    def test_max_results_stops_pagination(self):
        """Verify pagination stops when max_results is reached."""
        mock_fn = MagicMock()
        mock_fn.side_effect = [
            {"Items": [{"id": str(i)} for i in range(20)], "NextToken": "more"},
            {"Items": [{"id": str(i)} for i in range(20, 40)], "NextToken": "more"},
            {"Items": [{"id": str(i)} for i in range(40, 60)]},
        ]

        def result_cb(response):
            return response.get("Items", [])

        results = self.aws_util.invoke_aws_listing(
            fn=mock_fn,
            result_cb=result_cb,
            max_results=30,
        )

        assert len(results) >= 30
        # Should stop after 2 pages (40 results >= max_results 30)
        assert mock_fn.call_count == 2


class TestListAvailableHostPolicies:
    """Tests for list_available_host_policies using Resource Groups Tagging API."""

    def setup_method(self):
        self.context = MagicMock()
        self.aws_util = AWSUtil(self.context)
        self.mock_tagging_client = MagicMock()
        self.mock_aws_provider = MagicMock()
        self.mock_aws_provider.aws_partition.return_value = "aws"
        self.mock_aws_provider.get_client.return_value = self.mock_tagging_client
        self.aws_util.aws = MagicMock(return_value=self.mock_aws_provider)

    def test_returns_tagged_policies(self):
        """Verify tagged policies are returned."""
        self.mock_tagging_client.get_resources.return_value = {
            "ResourceTagMappingList": [
                {"ResourceARN": "arn:aws:iam::123456789012:policy/MyPolicy"},
                {"ResourceARN": "arn:aws:iam::123456789012:policy/OtherPolicy"},
            ],
            "PaginationToken": "",
        }

        result = self.aws_util.list_available_host_policies()

        assert len(result) == 2
        assert result[0] == Policy(
            policy_arn="arn:aws:iam::123456789012:policy/MyPolicy",
            policy_name="MyPolicy",
        )
        assert result[1] == Policy(
            policy_arn="arn:aws:iam::123456789012:policy/OtherPolicy",
            policy_name="OtherPolicy",
        )

    def test_handles_pagination(self):
        """Verify pagination works across multiple pages."""
        self.mock_tagging_client.get_resources.side_effect = [
            {
                "ResourceTagMappingList": [
                    {"ResourceARN": "arn:aws:iam::123456789012:policy/Policy1"},
                ],
                "PaginationToken": "next_page",
            },
            {
                "ResourceTagMappingList": [
                    {"ResourceARN": "arn:aws:iam::123456789012:policy/Policy2"},
                ],
                "PaginationToken": "",
            },
        ]

        result = self.aws_util.list_available_host_policies()

        assert len(result) == 2
        assert result[0].policy_name == "Policy1"
        assert result[1].policy_name == "Policy2"
        assert self.mock_tagging_client.get_resources.call_count == 2

    def test_empty_result_set(self):
        """Verify empty response returns empty list."""
        self.mock_tagging_client.get_resources.return_value = {
            "ResourceTagMappingList": [],
            "PaginationToken": "",
        }

        result = self.aws_util.list_available_host_policies()

        assert result == []

    def test_uses_global_region(self):
        """Verify tagging client is created with the partition's global region."""
        self.mock_tagging_client.get_resources.return_value = {
            "ResourceTagMappingList": [],
            "PaginationToken": "",
        }

        self.aws_util.list_available_host_policies()

        self.mock_aws_provider.get_client.assert_called_once_with(
            service_name="resourcegroupstaggingapi", region_name="us-east-1"
        )

    def test_govcloud_uses_correct_global_region(self):
        """Verify GovCloud partition uses us-gov-west-1."""
        self.mock_aws_provider.aws_partition.return_value = "aws-us-gov"
        self.mock_tagging_client.get_resources.return_value = {
            "ResourceTagMappingList": [],
            "PaginationToken": "",
        }

        self.aws_util.list_available_host_policies()

        self.mock_aws_provider.get_client.assert_called_once_with(
            service_name="resourcegroupstaggingapi", region_name="us-gov-west-1"
        )

    def test_china_uses_correct_global_region(self):
        """Verify China partition uses cn-northwest-1."""
        self.mock_aws_provider.aws_partition.return_value = "aws-cn"
        self.mock_tagging_client.get_resources.return_value = {
            "ResourceTagMappingList": [],
            "PaginationToken": "",
        }

        self.aws_util.list_available_host_policies()

        self.mock_aws_provider.get_client.assert_called_once_with(
            service_name="resourcegroupstaggingapi", region_name="cn-northwest-1"
        )

    def test_extracts_policy_name_from_path_arn(self):
        """Verify policy name is extracted correctly from ARNs with paths."""
        self.mock_tagging_client.get_resources.return_value = {
            "ResourceTagMappingList": [
                {"ResourceARN": "arn:aws:iam::123456789012:policy/my/path/DeepPolicy"},
            ],
            "PaginationToken": "",
        }

        result = self.aws_util.list_available_host_policies()

        assert result[0].policy_name == "DeepPolicy"
