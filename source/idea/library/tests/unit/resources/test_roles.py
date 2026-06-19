#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

import pytest
import res.exceptions as exceptions
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


@patch("res.resources.roles.get_role")
def test_get_roles_batch_returns_multiple_roles(mock_get_role):
    """
    Test get_roles_batch returns dict of multiple roles
    """

    def mock_role_response(role_id):
        return {
            "role_id": role_id,
            "name": f"Role {role_id}",
            "vdis": {"create_sessions": True},
        }

    mock_get_role.side_effect = mock_role_response

    result = roles.get_roles_batch(["role1", "role2", "role3"])

    assert len(result) == 3
    assert "role1" in result
    assert "role2" in result
    assert "role3" in result
    assert result["role1"]["name"] == "Role role1"
    assert mock_get_role.call_count == 3


@patch("res.resources.roles.get_role")
def test_get_roles_batch_empty_input(mock_get_role):
    """
    Test get_roles_batch returns empty dict for empty input
    """
    result = roles.get_roles_batch([])

    assert result == {}
    mock_get_role.assert_not_called()


@patch("res.resources.roles.get_role")
def test_get_roles_batch_skips_not_found_roles(mock_get_role):
    """
    Test get_roles_batch skips roles that are not found
    """

    def mock_role_response(role_id):
        if role_id == "role2":
            raise exceptions.RoleNotFound(f"Role {role_id} not found")
        return {"role_id": role_id, "name": f"Role {role_id}"}

    mock_get_role.side_effect = mock_role_response

    result = roles.get_roles_batch(["role1", "role2", "role3"])

    assert len(result) == 2
    assert "role1" in result
    assert "role2" not in result
    assert "role3" in result
