#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Dict

import requests

EC2_INSTANCE_METADATA_LATEST = "http://169.254.169.254/latest"
EC2_INSTANCE_METADATA_URL_PREFIX = f"{EC2_INSTANCE_METADATA_LATEST}/meta-data"
EC2_INSTANCE_IDENTITY_DOCUMENT_URL = (
    f"{EC2_INSTANCE_METADATA_LATEST}/dynamic/instance-identity/document"
)

EC2_INSTANCE_METADATA_API_URL = f"{EC2_INSTANCE_METADATA_LATEST}/api"
EC2_IMDS_TOKEN_REQUEST_HEADERS = {"X-aws-ec2-metadata-token-ttl-seconds": "900"}


def get_imds_auth_header() -> Dict[str, str]:
    """
    Return a built auth header for EC2 instance metadata IMDSv2
    """
    return {"X-aws-ec2-metadata-token": get_imds_auth_token()}


def get_imds_auth_token() -> str:
    """
    Generate an IMDSv2 auth token from EC2 instance metadata
    """
    result = requests.put(
        EC2_INSTANCE_METADATA_API_URL + "/token",
        headers=EC2_IMDS_TOKEN_REQUEST_HEADERS,
    )
    if result.status_code != 200:
        raise Exception(
            f"Failed to retrieve EC2 instance IMDSv2 authentication token. Statuscode: ({result.status_code})"
        )
    else:
        return result.text.strip()


def get_instance_id() -> str:
    try:
        result = requests.get(
            f"{EC2_INSTANCE_METADATA_URL_PREFIX}/instance-id",
            headers=get_imds_auth_header(),
            timeout=5,
        )
        if result.status_code == 200:
            return result.text.strip()
        else:
            raise Exception(f"Failed to get instance ID: {result.text}")
    except Exception as e:
        raise Exception(f"Failed to get instance ID: {e}")


def get_private_dns_name() -> str:
    try:
        result = requests.get(
            f"{EC2_INSTANCE_METADATA_URL_PREFIX}/local-hostname",
            headers=get_imds_auth_header(),
            timeout=5,
        )
        if result.status_code == 200:
            return result.text.strip()
        else:
            raise Exception(f"Failed to get private DNS name: {result.text}")
    except Exception as e:
        raise Exception(f"Failed to get private DNS name: {e}")


def get_instance_region() -> str:
    try:
        result = requests.get(
            f"{EC2_INSTANCE_METADATA_URL_PREFIX}/placement/region",
            headers=get_imds_auth_header(),
            timeout=5,
        )
        if result.status_code == 200:
            return result.text.strip()
        else:
            raise f"Failed to get instance region: {result.text}"
    except Exception as e:
        raise Exception(f"Failed to get instance region: {e}")
