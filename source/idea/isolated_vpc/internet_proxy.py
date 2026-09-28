#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
# Code changes made to this file must be replicated in 'source/idea/infrastructure/install/parameters/internet_proxy' too

from dataclasses import dataclass
from typing import Any

from idea.infrastructure.install.constants import OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX
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
            type="AWS::SSM::Parameter::Value<String>",
            description="Provide parameter store path containing the HTTP proxy URL for isolated VPC deployment.",
        )
    )

    https_proxy: str = Base.parameter(
        Attributes(
            id=InternetProxyKey.HTTPS_PROXY,
            type="AWS::SSM::Parameter::Value<String>",
            description="Provide parameter store path containing the HTTPS proxy URL for isolated VPC deployment.",
        )
    )

    no_proxy: str = Base.parameter(
        Attributes(
            id=InternetProxyKey.NO_PROXY,
            type="AWS::SSM::Parameter::Value<String>",
            description="Provide parameter store path containing the NO_PROXY exclusion list for isolated VPC deployment.",
        )
    )


class InternetProxyParameterGroups:
    parameter_group_for_internet_proxy: dict[str, Any] = {
        "Label": {
            "default": "Internet proxy configuration for RES deployed in isolated environment."
        },
        "Parameters": [
            InternetProxyKey.HTTPS_PROXY.value,
            InternetProxyKey.HTTP_PROXY.value,
            InternetProxyKey.NO_PROXY.value,
        ],
    }


class InternetProxyParameterLabels:
    parameter_labels_for_internet_proxy: dict[str, Any] = {
        InternetProxyKey.HTTPS_PROXY.value: {
            "default": f"{InternetProxyKey.HTTPS_PROXY.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        InternetProxyKey.HTTP_PROXY.value: {
            "default": f"{InternetProxyKey.HTTP_PROXY.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        InternetProxyKey.NO_PROXY.value: {
            "default": f"{InternetProxyKey.NO_PROXY.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
    }
