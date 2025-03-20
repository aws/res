#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import Any, Dict

import res.constants as constants
from res.utils import aws_utils, sssd_utils


def transform_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    if settings.get(constants.SERVICE_ACCOUNT_USER_DN_SECRET_ARN_KEY):
        settings[constants.SERVICE_ACCOUNT_USER_DN_KEY] = aws_utils.get_secret_string(
            settings[constants.SERVICE_ACCOUNT_USER_DN_SECRET_ARN_KEY]
        )
    return settings


def update_settings(settings: Dict[str, Any]) -> None:
    _validate_settings(settings)

    if constants.SERVICE_ACCOUNT_USER_DN_KEY in settings:
        # Create a secret ARN for service account user DN to avoid storing sensitive data in DDB
        settings[f"{constants.SERVICE_ACCOUNT_USER_DN_KEY}_secret_arn"] = (
            aws_utils.create_or_update_secret(
                os.environ.get(constants.ENVIRONMENT_NAME_KEY),
                constants.MODULE_DIRECTORY_SERVICE,
                constants.SERVICE_ACCOUNT_USER_DN_INPUT_PARAMETER_NAME,
                settings[constants.SERVICE_ACCOUNT_USER_DN_KEY],
            )
        )
        settings.pop(constants.SERVICE_ACCOUNT_USER_DN_KEY)


def _validate_settings(settings: Dict[str, Any]) -> None:
    additional_sssd_configs = json.loads(
        settings.get(sssd_utils.ADDITIONAL_SSSD_CONFIGS_PARTIAL_KEY, "{}")
    )
    if additional_sssd_configs:
        sssd_utils.validate_additional_sssd_configs(additional_sssd_configs)
