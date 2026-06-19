#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Optional

from res.resources import cluster_settings


def build_arn(
    partition: Optional[str],
    service: Optional[str],
    region: Optional[str],
    account_id: Optional[str],
    resource: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_delimiter="/",
) -> str:
    arn = f"arn:{partition}:{service}:{region}:{account_id}"
    if resource is not None:
        arn += f":{resource}"
    elif resource_id is not None:
        if resource_type is None:
            arn += f":{resource_id}"
        else:
            arn += f":{resource_type}{resource_delimiter}{resource_id}"
    else:
        raise ValueError("Either 'resource' or 'resource_id' must be provided")
    return arn


def get_arn(service: str, resource: str, aws_account_id=None, aws_region=None) -> str:
    if aws_account_id is None:
        aws_account_id = cluster_settings.get_setting("cluster.aws.account_id")
    if aws_region is None:
        aws_region = cluster_settings.get_setting("cluster.aws.region")
    return build_arn(
        partition=cluster_settings.get_setting("cluster.aws.partition"),
        service=service,
        region=aws_region,
        account_id=aws_account_id,
        resource=resource,
    )
