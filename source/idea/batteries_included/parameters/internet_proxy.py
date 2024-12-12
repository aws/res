#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Any

from idea.infrastructure.install.constants import (
    OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX,
    PROXY_URL_REGEX,
)
from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class InternetProxyKey(Key):
    HTTP_PROXY = "HttpProxy"
    HTTPS_PROXY = "HttpsProxy"
    NO_PROXY = "NoProxy"


@dataclass
class InternetProxyParameters(Base):
    http_proxy: str = Base.parameter(
        Attributes(
            id=InternetProxyKey.HTTP_PROXY,
            type="String",
            description="For deployment in isolated environment, please configure a HTTP proxy to connect to AWS services without VPC endpoints.",
            allowed_pattern=PROXY_URL_REGEX,
            constraint_description="The http proxy must be a valid url with IP address and port number. example: http://169.254.169.254:8080",
        )
    )

    https_proxy: str = Base.parameter(
        Attributes(
            id=InternetProxyKey.HTTPS_PROXY,
            type="String",
            description="For deployment in isolated environment, please configure a HTTPS proxy to connect to AWS services without VPC endpoints.",
            allowed_pattern=PROXY_URL_REGEX,
            constraint_description="The https proxy must be a valid url with IP address and port number. example: http://169.254.169.254:8080",
        )
    )

    no_proxy: str = Base.parameter(
        Attributes(
            id=InternetProxyKey.NO_PROXY,
            type="String",
            description="For deployment in isolated environment, if you are setting up HTTP_PROXY and HTTPS_PROXY, the NO_PROXY parameters are required to prevent the instance from using proxy to query localhost, instance metadata IP addresses, and the services that support VPC endpoints. example: 169.254.170.2,localhost",
        )
    )


class InternetProxyParameterGroups:
    parameter_group_for_internet_proxy: dict[str, Any] = {
        "Label": {
            "default": "Internet proxy configuration for RES deployed in isolated environment."
        },
        "Parameters": [
            InternetProxyKey.HTTPS_PROXY,
            InternetProxyKey.HTTP_PROXY,
            InternetProxyKey.NO_PROXY,
        ],
    }


class InternetProxyParameterLabels:
    parameter_labels_for_internet_proxy: dict[str, Any] = {
        InternetProxyKey.HTTPS_PROXY: {
            "default": f"{InternetProxyKey.HTTPS_PROXY}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        InternetProxyKey.HTTP_PROXY: {
            "default": f"{InternetProxyKey.HTTP_PROXY}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        InternetProxyKey.NO_PROXY: {
            "default": f"{InternetProxyKey.NO_PROXY}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
    }
