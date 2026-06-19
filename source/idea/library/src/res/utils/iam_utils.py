#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from functools import lru_cache
from typing import List

from botocore.exceptions import ClientError
from res.clients.aws.aws_provider import AwsClientProvider
from res.constants import ENVIRONMENT_NAME_KEY
from res.resources import cluster_settings
from res.utils import arn_utils, logging_utils

logger = logging_utils.get_logger("iam")

_aws_client_provider = AwsClientProvider()
_iam_client = _aws_client_provider.iam()


@lru_cache
def get_iam_resource_prefix() -> str:
    iam_resource_prefix = cluster_settings.get_setting(
        "cluster.iam.iam_resource_prefix"
    )
    return iam_resource_prefix if iam_resource_prefix else ""


def get_vdi_role_name(project_name: str) -> str:
    return f"{get_iam_resource_prefix()}{os.environ.get(ENVIRONMENT_NAME_KEY)}-vdi-{project_name}"


def get_role_attached_policies_arns(role_name: str) -> (bool, List[str]):
    """
    List attached policies to a role
    """
    try:
        attached_policies_response = _iam_client.list_attached_role_policies(
            RoleName=role_name,
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            return False, []
        raise e
    return True, [
        policy["PolicyArn"]
        for policy in attached_policies_response.get("AttachedPolicies", [])
    ]


def detach_policy_from_role(role_name: str, policy_arn: str) -> bool:
    """
    Detach a policy from a role
    """
    try:
        _iam_client.detach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn,
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            return True
        raise e
    return True


def dissociate_role_and_instance_profile(role_name: str, instance_profile_name) -> bool:
    """
    Deassociate a role from an instance profile
    """
    try:
        _iam_client.remove_role_from_instance_profile(
            InstanceProfileName=instance_profile_name,
            RoleName=role_name,
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            return True
        raise e
    return True


def delete_iam_role(role_name: str) -> bool:
    try:
        _iam_client.delete_role(RoleName=role_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            return True
        raise e
    return True


def delete_iam_instance_profile(instance_profile_name: str) -> bool:
    try:
        _iam_client.delete_instance_profile(InstanceProfileName=instance_profile_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            return True
        raise e
    return True


def _get_vdi_role_path(cluster_name: str, region: str, path: str = "") -> str:
    return f"{path}{cluster_name}-{region}/vdi"


def _get_vdi_role_name(cluster_name: str, project_name: str, prefix: str = "") -> str:
    return f"{prefix}{cluster_name}-vdi-{project_name}"


def build_vdi_instance_profile_arn(project_name: str) -> str:
    cluster_name = cluster_settings.get_setting("cluster.cluster_name")
    region = cluster_settings.get_setting("cluster.aws.region")
    try:
        iam_path = cluster_settings.get_setting("cluster.iam.iam_resource_path") or "/"
    except Exception:
        logger.warning("cluster.iam.iam_resource_path not found, defaulting to '/'")
        iam_path = "/"
    try:
        iam_prefix = (
            cluster_settings.get_setting("cluster.iam.iam_resource_prefix") or ""
        )
    except Exception:
        logger.warning("cluster.iam.iam_resource_prefix not found, defaulting to ''")
        iam_prefix = ""
    instance_profile_path = _get_vdi_role_path(cluster_name, region, iam_path)
    instance_profile_name = _get_vdi_role_name(cluster_name, project_name, iam_prefix)
    return arn_utils.get_arn(
        service="iam",
        aws_region="",
        resource=f"instance-profile{instance_profile_path}/{instance_profile_name}",
    )
