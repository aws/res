#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.resources import cluster_settings, ad_automation
from res.utils import sssd_utils
from typing import Optional
from unittest.mock import Mock
import logging

from ideabootstrap.directory_service import active_directory as active_directory
from ideabootstrap.directory_service.linux import active_directory as active_directory_platform


def test_active_directory_no_ad_configuration_provided_skip(monkeypatch):
    monkeypatch.setattr(cluster_settings, "get_setting", lambda _: None)
    monkeypatch.setenv("RES_BASE_OS", "linux")

    mock_configure_sssd = Mock()
    monkeypatch.setattr(active_directory_platform, "configure_sssd", mock_configure_sssd)
    mock_is_in_active_directory = Mock()
    monkeypatch.setattr(active_directory_platform, "is_in_active_directory", mock_is_in_active_directory)
    mock_join_active_directory = Mock()
    monkeypatch.setattr(active_directory_platform, "join_active_directory", mock_join_active_directory)

    active_directory.configure()
    mock_configure_sssd.assert_not_called()
    mock_is_in_active_directory.assert_not_called()
    mock_join_active_directory.assert_not_called()


def test_active_directory_disable_ad_join_configure_sssd(monkeypatch):
    def _get_setting(key: str) -> Optional[str]:
        if key == sssd_utils.DOMAIN_NAME_KEY:
            return "domain"
        elif key == sssd_utils.DISABLE_AD_JOIN_KEY:
            return "true"
        else:
            return None

    monkeypatch.setattr(
        cluster_settings,
        "get_setting",
        _get_setting,
    )
    monkeypatch.setenv("RES_BASE_OS", "linux")

    mock_configure_sssd = Mock()
    monkeypatch.setattr(active_directory_platform, "configure_sssd", mock_configure_sssd)
    mock_is_in_active_directory = Mock()
    monkeypatch.setattr(active_directory_platform, "is_in_active_directory", mock_is_in_active_directory)
    mock_join_active_directory = Mock()
    monkeypatch.setattr(active_directory_platform, "join_active_directory", mock_join_active_directory)

    active_directory.configure()
    mock_configure_sssd.assert_called_once()
    mock_is_in_active_directory.assert_not_called()
    mock_join_active_directory.assert_not_called()


def test_active_directory_enable_ad_join_join_active_directory(monkeypatch):
    def _get_setting(key: str) -> Optional[str]:
        if key == sssd_utils.DOMAIN_NAME_KEY:
            return "domain"
        elif key == sssd_utils.DISABLE_AD_JOIN_KEY:
            return "false"
        else:
            return None

    monkeypatch.setattr(
        cluster_settings,
        "get_setting",
        _get_setting,
    )
    monkeypatch.setenv("RES_BASE_OS", "linux")

    mock_configure_sssd = Mock()
    monkeypatch.setattr(active_directory_platform, "configure_sssd", mock_configure_sssd)
    monkeypatch.setattr(active_directory_platform, "is_in_active_directory", lambda: False)
    mock_join_active_directory = Mock()
    monkeypatch.setattr(active_directory_platform, "join_active_directory", mock_join_active_directory)
    monkeypatch.setattr(ad_automation, "request_ad_authorization", lambda: True)
    monkeypatch.setattr(ad_automation, "get_authorization", lambda: {"status": "success"})

    active_directory.configure()
    mock_configure_sssd.assert_not_called()
    mock_join_active_directory.assert_called_once()


def _setup_windows_ad_test(monkeypatch, disable_ad_join: str, caplog=None):
    def _get_setting(key: str) -> Optional[str]:
        if key == sssd_utils.DOMAIN_NAME_KEY:
            return "domain"
        elif key == sssd_utils.DISABLE_AD_JOIN_KEY:
            return disable_ad_join
        else:
            return None

    monkeypatch.setattr(cluster_settings, "get_setting", _get_setting)
    monkeypatch.setattr(active_directory, "BASE_OS", "windows")
    
    if caplog:
        mock_logger = logging.getLogger("test_bootstrap")
        monkeypatch.setattr(active_directory, "logger", mock_logger)
        caplog.set_level(logging.DEBUG)
    
    monkeypatch.setattr(active_directory_platform, "is_in_active_directory", lambda: False)
    mock_join_active_directory = Mock()
    monkeypatch.setattr(active_directory_platform, "join_active_directory", mock_join_active_directory)
    monkeypatch.setattr(ad_automation, "request_ad_authorization", lambda: True)
    monkeypatch.setattr(ad_automation, "get_authorization", lambda: {"status": "success"})
    
    return mock_join_active_directory


def test_active_directory_windows_ad_join_disabled(monkeypatch, caplog):
    mock_join_active_directory = _setup_windows_ad_test(monkeypatch, "true", caplog)
    
    active_directory.configure()
    
    mock_join_active_directory.assert_not_called()
    assert "Active Directory auto-join is disabled" in caplog.text


def test_active_directory_windows_ad_join_enabled(monkeypatch):
    mock_join_active_directory = _setup_windows_ad_test(monkeypatch, "false")
    
    active_directory.configure()
    
    mock_join_active_directory.assert_called_once()


def test_active_directory_is_in_active_directory_skip(monkeypatch):
    def _get_setting(key: str) -> Optional[str]:
        if key == sssd_utils.DOMAIN_NAME_KEY:
            return "domain"
        elif key == sssd_utils.DISABLE_AD_JOIN_KEY:
            return "false"
        else:
            return None

    monkeypatch.setattr(
        cluster_settings,
        "get_setting",
        _get_setting,
    )
    monkeypatch.setenv("RES_BASE_OS", "linux")

    mock_configure_sssd = Mock()
    monkeypatch.setattr(active_directory_platform, "configure_sssd", mock_configure_sssd)
    mock_is_in_active_directory = Mock()
    mock_is_in_active_directory.return_value = True
    monkeypatch.setattr(active_directory_platform, "is_in_active_directory", mock_is_in_active_directory)
    mock_join_active_directory = Mock()
    monkeypatch.setattr(active_directory_platform, "join_active_directory", mock_join_active_directory)

    active_directory.configure(force_join=False)
    mock_configure_sssd.assert_not_called()
    mock_is_in_active_directory.assert_called_once()
    mock_join_active_directory.assert_not_called()
