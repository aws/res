#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
import res.constants as constants
from res.resources import directory_service_settings
from res.utils import aws_utils, sssd_utils


def test_transform_settings_retrieve_service_account_dn_content(monkeypatch):
    monkeypatch.setattr(aws_utils, "get_secret_string", lambda x: "service_account_dn")

    settings = {constants.SERVICE_ACCOUNT_USER_DN_SECRET_ARN_KEY: "test_arn"}
    settings = directory_service_settings.transform_settings(settings)
    assert settings[constants.SERVICE_ACCOUNT_USER_DN_KEY] == "service_account_dn"


def test_update_settings_invalid_additional_sssd_configs_throw_exception(monkeypatch):
    error_message = "error message"

    def raise_exception(_additional_sssd_configs):
        raise Exception(error_message)

    monkeypatch.setattr(
        "res.utils.sssd_utils.validate_additional_sssd_configs", raise_exception
    )

    settings = {
        sssd_utils.ADDITIONAL_SSSD_CONFIGS_PARTIAL_KEY: '{"id_provider": "test"}'
    }
    with pytest.raises(Exception) as exc_info:
        directory_service_settings.update_settings(settings)
    assert error_message in exc_info.value.args[0]


def test_update_settings_save_service_account_dn_to_secret(monkeypatch):
    monkeypatch.setattr(
        aws_utils,
        "create_or_update_secret",
        lambda cluster_name, module_name, key, secret_string_value: "service_account_dn_secret_arn",
    )

    settings = {constants.SERVICE_ACCOUNT_USER_DN_KEY: "service_account_dn"}
    directory_service_settings.update_settings(settings)
    assert (
        settings[constants.SERVICE_ACCOUNT_USER_DN_SECRET_ARN_KEY]
        == "service_account_dn_secret_arn"
    )
