#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Tier 0 API Proxy tests (doc area: "API Proxy").

The doc covers the budget dropdown (empty with no budget, populated after a budget
is created in the account), the EFS/FSx onboarding dropdown, and infrastructure host
status. These flow through the AWS proxy gateway (X-Amz-Target headers, e.g.
AWSBudgetServiceGateway.DescribeBudgets) — see source/tests/lambdas/aws_proxy/ for
the request shape.

The integration ResClient / ApiClient do not yet wire up the proxy gateway, so these
are skipped pending a proxy-aware client method. They are kept here (marked @dev) so
the API Proxy area is tracked in the suite rather than silently missing.
"""

import pytest


@pytest.mark.dev
class TestApiProxy:

    @pytest.mark.skip(
        reason="Proxy gateway (X-Amz-Target) not yet wired into the integration "
        "ApiClient; budget/EFS dropdown checks pending a proxy client method."
    )
    def test_budget_dropdown_empty_with_no_budget(self) -> None:
        """No budgets in account -> budget dropdown returns no options."""

    @pytest.mark.skip(
        reason="Proxy gateway (X-Amz-Target) not yet wired into the integration "
        "ApiClient; budget/EFS dropdown checks pending a proxy client method."
    )
    def test_efs_dropdown_empty_with_no_filesystem(self) -> None:
        """No additional EFS in the VPC -> onboarding dropdown returns no options."""

    @pytest.mark.skip(
        reason="Proxy gateway (X-Amz-Target) not yet wired into the integration "
        "ApiClient; infra host status check pending a proxy client method."
    )
    def test_infrastructure_host_status_loads(self) -> None:
        """Environment status page infra host table loads host statuses."""
