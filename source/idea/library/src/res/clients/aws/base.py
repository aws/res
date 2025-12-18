#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Set


class AwsServiceEndpoint:
    def __init__(
        self, service_name: Optional[str] = None, endpoint_url: Optional[str] = None
    ):
        self.service_name = service_name
        self.endpoint_url = endpoint_url

    def __str__(self) -> str:
        return f"Service: {self.service_name}, Endpoint Url: {self.endpoint_url}"


class AWSClientProviderOptions:
    def __init__(
        self,
        profile: Optional[str] = None,
        region: Optional[str] = None,
        pricing_api_region: Optional[str] = None,
        endpoints: Optional[List[AwsServiceEndpoint]] = None,
    ):
        self.profile = profile
        self.region = region
        self.pricing_api_region = pricing_api_region
        self.endpoints = endpoints or []

    @staticmethod
    def default() -> "AWSClientProviderOptions":
        return AWSClientProviderOptions()


class AwsClientProviderProtocol(ABC):
    """Simplified protocol for AWS client provider"""

    @abstractmethod
    def aws_partition(self) -> str:
        pass

    @abstractmethod
    def aws_region(self) -> str:
        pass

    @abstractmethod
    def aws_account_id(self) -> str:
        pass

    @abstractmethod
    def aws_dns_suffix(self) -> str:
        pass

    @abstractmethod
    def aws_profile(self) -> str:
        pass

    @abstractmethod
    def is_running_in_ec2(self) -> bool:
        pass

    @abstractmethod
    def are_credentials_expired(self) -> bool:
        pass

    @abstractmethod
    def supported_clients(self) -> Set[str]:
        pass

    @abstractmethod
    def get_client(self, service_name: str, **kwargs: Any) -> Any:
        pass


class InstanceMetadataUtilProtocol(ABC):
    @abstractmethod
    def is_running_in_ec2(self) -> bool:
        pass


def general_exception(message: str) -> Exception:
    return Exception(message)
