#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass

from idea.infrastructure.install.parameters import (
    cognito_user_pool,
    common,
    customdomain,
    directoryservice,
    shared_storage,
)
from idea.isolated_vpc import internet_proxy


@dataclass
class IsolatedVpcParameters(
    common.CommonParameters,
    customdomain.CustomDomainParameters,
    directoryservice.DirectoryServiceParameters,
    shared_storage.SharedStorageParameters,
    internet_proxy.InternetProxyParameters,
    cognito_user_pool.CognitoUserPoolParameters,
):
    """
    RESParameters variant for isolated VPC deployments.
    Same as RESParameters but proxy params resolve from SSM at deploy time.
    """

    pass
