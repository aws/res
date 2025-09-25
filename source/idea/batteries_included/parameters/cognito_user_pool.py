#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Any

from idea.infrastructure.install.constants import OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX
from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class CognitoUserPoolKey(Key):
    COGNITO_USER_POOL_ID = "CognitoUserPoolId"
    COGNITO_USER_POOL_DOMAIN_URL = "CognitoUserPoolDomainUrl"


@dataclass
class CognitoUserPoolParameters(Base):
    cognito_user_pool_id: str = Base.parameter(
        Attributes(
            id=CognitoUserPoolKey.COGNITO_USER_POOL_ID,
            type="String",
            description=(
                "Cognito user pool for user and app client authentication. "
                "RES will create one by default if no Cognito user pool is specified"
            ),
            allowed_pattern="^$|^[a-z0-9-_]+_[A-Za-z0-9]+$",
        )
    )
    cognito_user_pool_domain_url: str = Base.parameter(
        Attributes(
            id=CognitoUserPoolKey.COGNITO_USER_POOL_DOMAIN_URL,
            type="String",
            description=(
                "Cognito user pool domain for managed login. "
                "This parameter must be provided when CognitoUserPoolId is specified."
            ),
        )
    )


class CognitoUserPoolParameterLabels:
    parameter_labels_for_cognito_user_pool: dict[str, Any] = {
        CognitoUserPoolKey.COGNITO_USER_POOL_ID: {
            "default": f"{CognitoUserPoolKey.COGNITO_USER_POOL_ID}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        CognitoUserPoolKey.COGNITO_USER_POOL_DOMAIN_URL: {
            "default": f"{CognitoUserPoolKey.COGNITO_USER_POOL_DOMAIN_URL}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
    }


class CognitoUserPoolParameterGroups:
    parameter_group_for_cognito_user_pool: dict[str, Any] = {
        "Label": {
            "default": f"Cognito User Pool details{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        "Parameters": [
            CognitoUserPoolKey.COGNITO_USER_POOL_ID,
            CognitoUserPoolKey.COGNITO_USER_POOL_DOMAIN_URL,
        ],
    }
