#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

import pytest
from res.resources import roles


@patch("res.resources.roles.get_role")
def test_filter_roles_with_manage_sessions_permission_with_permission(mock_get_role):
    """
    Test filter_roles_with_manage_sessions_permission returns roles with permission
    """

    def mock_role_response(role_id):
        if role_id == "role1":
            return {"vdis": {"create_terminate_others_sessions": True}}
        elif role_id == "role2":
            return {"vdis": {"create_terminate_others_sessions": False}}
        return {}

    mock_get_role.side_effect = mock_role_response

    result = roles.filter_roles_with_manage_sessions_permission({"role1", "role2"})

    assert result == {"role1"}
    assert mock_get_role.call_count == 2


@patch("res.resources.roles.get_role")
def test_filter_roles_with_manage_sessions_permission_without_permission(mock_get_role):
    """
    Test filter_roles_with_manage_sessions_permission returns empty set when no roles have permission
    """
    mock_get_role.return_value = {"vdis": {"create_terminate_others_sessions": False}}

    result = roles.filter_roles_with_manage_sessions_permission({"role1"})

    assert result == set()
    mock_get_role.assert_called_once_with("role1")


@patch("res.resources.roles.get_role")
def test_filter_roles_with_manage_sessions_permission_empty_input(mock_get_role):
    """
    Test filter_roles_with_manage_sessions_permission with empty input
    """
    result = roles.filter_roles_with_manage_sessions_permission(set())

    assert result == set()
    mock_get_role.assert_not_called()


@patch("res.resources.roles.get_role")
def test_filter_roles_with_manage_sessions_permission_no_vdis_key(mock_get_role):
    """
    Test filter_roles_with_manage_sessions_permission handles roles without vdis key
    """
    mock_get_role.return_value = {"other_permissions": {}}

    result = roles.filter_roles_with_manage_sessions_permission({"role1"})

    assert result == set()
    mock_get_role.assert_called_once_with("role1")
