#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Tier 0 infrastructure-validation tests.

These are fast, describe-only boto3 assertions against a deployed RES environment.
They require no VDI provisioning and are part of the ``dev`` suite, so they run on
every pipeline execution to catch infrastructure regressions early.

Covers the doc areas:
- "All the resources are tagged"
- "S3 bucket should have access logging turned"
- "SSL requirement enabled on S3 bucket"
- DynamoDB tables should have point-in-time recovery enabled
"""

import logging
from typing import List, Optional, Tuple

import boto3
import pytest

logger = logging.getLogger(__name__)

# All RES-managed resources carry this tag (see res.constants.ENVIRONMENT_NAME_TAG_KEY).
ENVIRONMENT_NAME_TAG_KEY = "res:EnvironmentName"


def _logging_bucket_name(environment_name: str, region: str) -> str:
    account_id = boto3.client("sts", region_name=region).get_caller_identity()[
        "Account"
    ]
    # Matches res_base_stack.create_bucket(): "{cluster}-logging-{region}-{account}".
    return f"{environment_name}-logging-{region}-{account_id}"


@pytest.mark.dev
@pytest.mark.infra_validation
class TestInfraValidation:

    def test_all_resources_tagged(self, region: str, environment_name: str) -> None:
        """
        Every RES-managed resource must carry the res:EnvironmentName tag.

        Uses the Resource Groups Tagging API to confirm at least the core infra
        resources are returned for the environment's tag value.
        """
        client = boto3.client("resourcegroupstaggingapi", region_name=region)
        paginator = client.get_paginator("get_resources")
        resource_arns: List[str] = []
        for page in paginator.paginate(
            TagFilters=[{"Key": ENVIRONMENT_NAME_TAG_KEY, "Values": [environment_name]}]
        ):
            resource_arns.extend(
                mapping["ResourceARN"]
                for mapping in page.get("ResourceTagMappingList", [])
            )

        logger.info(
            f"found {len(resource_arns)} resources tagged "
            f"{ENVIRONMENT_NAME_TAG_KEY}={environment_name}"
        )
        assert resource_arns, (
            f"no resources tagged {ENVIRONMENT_NAME_TAG_KEY}={environment_name}; "
            "RES resources are expected to be tagged with the environment name"
        )

    def test_logging_bucket_access_logging_enabled(
        self, region: str, environment_name: str
    ) -> None:
        """The cluster logging bucket must have server access logging enabled."""
        bucket = _logging_bucket_name(environment_name, region)
        s3 = boto3.client("s3", region_name=region)

        response = s3.get_bucket_logging(Bucket=bucket)
        logging_enabled = response.get("LoggingEnabled")

        assert (
            logging_enabled is not None
        ), f"server access logging is not enabled on bucket {bucket}"
        assert logging_enabled.get(
            "TargetBucket"
        ), f"server access logging on {bucket} is missing a target bucket"

    def test_logging_bucket_ssl_only_policy(
        self, region: str, environment_name: str
    ) -> None:
        """
        The logging bucket policy must deny non-TLS requests via the
        AllowSSLRequestsOnly statement (aws:SecureTransport=false -> Deny).
        """
        import json

        bucket = _logging_bucket_name(environment_name, region)
        s3 = boto3.client("s3", region_name=region)

        policy = json.loads(s3.get_bucket_policy(Bucket=bucket)["Policy"])
        statements = policy.get("Statement", [])

        ssl_only = next(
            (s for s in statements if s.get("Sid") == "AllowSSLRequestsOnly"), None
        )
        assert (
            ssl_only is not None
        ), f"bucket {bucket} policy missing AllowSSLRequestsOnly statement"
        assert ssl_only.get("Effect") == "Deny"
        assert (
            ssl_only.get("Condition", {}).get("Bool", {}).get("aws:SecureTransport")
            == "false"
        ), "AllowSSLRequestsOnly must deny requests where aws:SecureTransport=false"

    def test_dynamodb_tables_pitr_enabled(
        self, region: str, environment_name: str
    ) -> None:
        """
        All of the environment's DynamoDB tables must have point-in-time
        recovery (PITR) enabled. Tables are named "{environment_name}.<name>".
        """
        ddb = boto3.client("dynamodb", region_name=region)
        prefix = f"{environment_name}."

        tables: List[str] = []
        paginator = ddb.get_paginator("list_tables")
        for page in paginator.paginate():
            tables.extend(
                name for name in page.get("TableNames", []) if name.startswith(prefix)
            )

        assert tables, f"no DynamoDB tables found with prefix {prefix!r}"

        tables_without_pitr: List[Tuple[str, Optional[str]]] = []
        for table_name in tables:
            backups = ddb.describe_continuous_backups(TableName=table_name)
            status = (
                backups["ContinuousBackupsDescription"]
                .get("PointInTimeRecoveryDescription", {})
                .get("PointInTimeRecoveryStatus")
            )
            if status != "ENABLED":
                tables_without_pitr.append((table_name, status))

        assert not tables_without_pitr, "PITR is not ENABLED on tables: " + ", ".join(
            f"{name} ({status})" for name, status in tables_without_pitr
        )
